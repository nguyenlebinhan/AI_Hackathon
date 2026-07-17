import logging

from app.config.celery_app import celery_app
from app.config.database import SessionLocal
from app.exceptions import (
    InvalidStateTransitionError,
    NotFoundError,
    StorageUnavailableError,
)
from app.model.base import utcnow
from app.model.documents import Document
from app.model.processing import ProcessingStatus, ProcessingStep
from app.model.repositories.processing import ProcessingJobRepository
from app.model.repositories.storage import DocumentFileRepository
from app.service.processing import ProcessingStateService
from app.utils.storage_dependencies import get_object_storage

logger = logging.getLogger(__name__)


@celery_app.task(name="vads.processing.mark_queued")
def mark_queued(job_id: str) -> None:
    """Durably hand an uploaded job to the future extraction pipeline.

    Module 1 stops at QUEUED. Extraction workers will use
    ``ProcessingStateService.transition`` to report subsequent steps.
    """

    with SessionLocal() as session:
        repository = ProcessingJobRepository(session)
        job = repository.get(job_id)
        if job is None or job.status != ProcessingStatus.UPLOADED:
            return
        try:
            ProcessingStateService(session).transition(
                job_id,
                status=ProcessingStatus.QUEUED,
                progress=0,
                current_step=ProcessingStep.WAITING_FOR_PROCESSING,
            )
        except (InvalidStateTransitionError, NotFoundError):
            # A concurrent soft delete can cancel the job before this task claims it.
            session.rollback()


@celery_app.task(name="vads.processing.redispatch_uploaded_jobs")
def redispatch_uploaded_jobs() -> int:
    """Recover jobs committed while Redis/Celery was unavailable."""

    with SessionLocal() as session:
        jobs = ProcessingJobRepository(session).list_uploaded(limit=100)
        for job in jobs:
            mark_queued.apply_async(args=[job.id])
        return len(jobs)


@celery_app.task(
    name="vads.processing.purge_document_objects",
    autoretry_for=(StorageUnavailableError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=8,
)
def purge_document_objects(document_id: str) -> int:
    """Delete original objects only after the document has been soft-deleted."""

    storage = get_object_storage()
    with SessionLocal() as session:
        document = session.get(Document, document_id)
        if document is None or document.deleted_at is None:
            return 0

        files = DocumentFileRepository(session).list_for_document(document_id)
        deleted_count = 0
        for document_file in files:
            storage.delete(object_key=document_file.object_key)
            document_file.deleted_at = utcnow()
            deleted_count += 1
        session.commit()
        logger.info(
            "Purged document objects",
            extra={"document_id": document_id, "deleted_count": deleted_count},
        )
        return deleted_count
