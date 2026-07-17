
from sqlalchemy.orm import Session

from app.exceptions import AppError, InvalidStateTransitionError, NotFoundError
from app.model.base import utcnow
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.model.repositories.processing import ProcessingJobRepository
from app.model.schemas.processing import ProcessingStatusResponse
from app.service.base import Service

STEP_MESSAGES: dict[ProcessingStep, str] = {
    ProcessingStep.WAITING_FOR_PROCESSING: "Tài liệu đang chờ xử lý",
    ProcessingStep.EXTRACTING_TEXT: "Đang trích xuất nội dung văn bản",
    ProcessingStep.DETECTING_PAGE_BOUNDARIES: "Đang xác định ranh giới trang",
    ProcessingStep.DETECTING_STRUCTURE: "Đang nhận diện điều, khoản và mục",
    ProcessingStep.CREATING_CHUNKS: "Đang chia tài liệu thành các đoạn có ngữ nghĩa",
    ProcessingStep.GENERATING_SUMMARY: "Đang tạo bản tóm tắt",
    ProcessingStep.BUILDING_KNOWLEDGE_GRAPH: "Đang xây dựng đồ thị tri thức",
    ProcessingStep.INDEXING_VECTOR_DATA: "Đang lập chỉ mục dữ liệu vector",
    ProcessingStep.COMPLETED: "Đã xử lý tài liệu thành công",
}

ALLOWED_TRANSITIONS: dict[ProcessingStatus, set[ProcessingStatus]] = {
    ProcessingStatus.UPLOADED: {
        ProcessingStatus.QUEUED,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
    },
    ProcessingStatus.QUEUED: {
        ProcessingStatus.PROCESSING,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
    },
    ProcessingStatus.PROCESSING: {
        ProcessingStatus.COMPLETED,
        ProcessingStatus.FAILED,
        ProcessingStatus.CANCELLED,
    },
    ProcessingStatus.COMPLETED: set(),
    ProcessingStatus.FAILED: set(),
    ProcessingStatus.CANCELLED: set(),
}
TERMINAL_STATUSES = {
    ProcessingStatus.COMPLETED,
    ProcessingStatus.FAILED,
    ProcessingStatus.CANCELLED,
}


class ProcessingStateService(Service):
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.repository = ProcessingJobRepository(session)

    def get_latest(self, document_id: str) -> ProcessingJob:
        job = self.repository.get_latest_for_document(document_id)
        if job is None:
            raise NotFoundError("PROCESSING_JOB", document_id)
        return job

    def transition(
        self,
        job_id: str,
        *,
        status: ProcessingStatus,
        progress: int,
        current_step: ProcessingStep,
        error_code: str | None = None,
        error_message: str | None = None,
        commit: bool = True,
    ) -> ProcessingJob:
        job = self.repository.get_for_update(job_id)
        if job is None:
            raise NotFoundError("PROCESSING_JOB", job_id)

        if job.status in TERMINAL_STATUSES:
            if (
                status == job.status
                and progress == job.progress
                and current_step == job.current_step
            ):
                if commit:
                    self.session.commit()
                return job
            raise InvalidStateTransitionError(job.status.value, status.value)
        if status != job.status and status not in ALLOWED_TRANSITIONS[job.status]:
            raise InvalidStateTransitionError(job.status.value, status.value)
        if not 0 <= progress <= 100:
            raise AppError(
                status_code=422,
                code="INVALID_PROCESSING_PROGRESS",
                message="Tiến độ xử lý phải nằm trong khoảng từ 0 đến 100.",
            )
        if progress < job.progress:
            raise AppError(
                status_code=409,
                code="PROCESSING_PROGRESS_REGRESSION",
                message="Tiến độ xử lý không được giảm.",
                details={"currentProgress": job.progress, "targetProgress": progress},
            )
        if status == ProcessingStatus.COMPLETED:
            progress = 100
            current_step = ProcessingStep.COMPLETED
        if status == ProcessingStatus.FAILED and not error_message:
            raise AppError(
                status_code=422,
                code="PROCESSING_ERROR_MESSAGE_REQUIRED",
                message="Trạng thái FAILED phải có thông báo lỗi.",
            )

        now = utcnow()
        job.status = status
        job.progress = progress
        job.current_step = current_step
        job.error_code = error_code
        job.error_message = error_message
        job.updated_at = now
        if status == ProcessingStatus.PROCESSING and job.started_at is None:
            job.started_at = now
        if status in TERMINAL_STATUSES:
            job.completed_at = now

        from app.model.documents import Document

        document = self.session.get(Document, job.document_id)
        if document is not None:
            document.status = status
            document.updated_at = now

        if commit:
            self.session.commit()
            self.session.refresh(job)
        else:
            self.session.flush()
        return job

    @staticmethod
    def to_response(job: ProcessingJob) -> ProcessingStatusResponse:
        message = job.error_message or STEP_MESSAGES[job.current_step]
        return ProcessingStatusResponse(
            document_id=job.document_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            message=message,
            started_at=job.started_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            error_code=job.error_code,
        )
