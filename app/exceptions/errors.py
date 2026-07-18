from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}


class AuthenticationError(AppError):
    def __init__(
        self,
        code: str = "INVALID_AUTHENTICATION",
        message: str = "Xác thực không hợp lệ.",
    ) -> None:
        super().__init__(
            status_code=401,
            code=code,
            message=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(AppError):
    def __init__(
        self,
        code: str = "FORBIDDEN",
        message: str = "Bạn không có quyền thực hiện thao tác này.",
    ) -> None:
        super().__init__(status_code=403, code=code, message=message)


class BadRequestError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=400, code=code, message=message, details=details)


class RateLimitError(AppError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            status_code=429,
            code="LOGIN_RATE_LIMITED",
            message="Có quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau.",
            details={"retryAfterSeconds": retry_after_seconds},
            headers={"Retry-After": str(max(1, retry_after_seconds))},
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        names = {
            "WORKSPACE": "workspace",
            "DOCUMENT": "tài liệu",
            "DOCUMENT_PAGE": "trang tài liệu",
            "PROCESSING_JOB": "processing job",
            "CHUNK": "chunk",
            "USER": "người dùng",
            "AUDIT_LOG": "nhật ký hoạt động",
        }
        super().__init__(
            status_code=404,
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"Không tìm thấy {names.get(resource.upper(), resource.lower())}.",
            details={"id": resource_id},
        )


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=409, code=code, message=message, details=details)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=415, code=code, message=message, details=details)


class PayloadTooLargeError(AppError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            status_code=413,
            code="FILE_TOO_LARGE",
            message="Tệp vượt quá dung lượng tối đa cho phép.",
            details={"maxSizeBytes": max_size_bytes},
        )


class StorageUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="OBJECT_STORAGE_UNAVAILABLE",
            message="Kho lưu trữ tệp tạm thời không khả dụng.",
        )


class InvalidStateTransitionError(AppError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            status_code=409,
            code="INVALID_PROCESSING_STATE_TRANSITION",
            message="Không thể chuyển trạng thái xử lý theo yêu cầu.",
            details={"currentStatus": current, "targetStatus": target},
        )
