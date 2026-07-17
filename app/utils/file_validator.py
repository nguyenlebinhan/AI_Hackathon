import hashlib
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePath
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from fastapi import UploadFile

from app.config.settings import Settings
from app.exceptions import AppError, PayloadTooLargeError, UnsupportedMediaTypeError

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_TYPES = {
    ".pdf": PDF_MIME,
    ".docx": DOCX_MIME,
}
DANGEROUS_SUFFIXES = {
    ".bat",
    ".cmd",
    ".com",
    ".exe",
    ".jar",
    ".js",
    ".msi",
    ".php",
    ".ps1",
    ".scr",
    ".sh",
    ".vbs",
}
FORBIDDEN_FILENAME_CHARACTERS = set('<>:"/\\|?*')
READ_CHUNK_SIZE = 1024 * 1024


@dataclass
class ValidatedUpload:
    file_object: BinaryIO
    original_filename: str
    mime_type: str
    extension: str
    file_size: int
    checksum: str

    def close(self) -> None:
        self.file_object.close()


class FileValidator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, upload: UploadFile) -> ValidatedUpload:
        filename = self._validate_filename(upload.filename)
        extension = PurePath(filename).suffix.lower()
        expected_mime = ALLOWED_TYPES.get(extension)
        if expected_mime is None:
            raise UnsupportedMediaTypeError(
                "UNSUPPORTED_FILE_EXTENSION",
                "Chỉ chấp nhận tệp có phần mở rộng .pdf hoặc .docx.",
                {"extension": extension or None},
            )

        supplied_mime = (upload.content_type or "").split(";", maxsplit=1)[0].strip().lower()
        if supplied_mime != expected_mime:
            raise UnsupportedMediaTypeError(
                "MIME_TYPE_MISMATCH",
                "MIME type không khớp với phần mở rộng của tệp.",
                {"expected": expected_mime, "received": supplied_mime or None},
            )

        temporary_file = SpooledTemporaryFile(
            max_size=self.settings.upload_spool_memory_bytes,
            mode="w+b",
        )
        digest = hashlib.sha256()
        size = 0
        try:
            upload.file.seek(0)
            while chunk := upload.file.read(READ_CHUNK_SIZE):
                size += len(chunk)
                if size > self.settings.max_upload_size_bytes:
                    raise PayloadTooLargeError(self.settings.max_upload_size_bytes)
                digest.update(chunk)
                temporary_file.write(chunk)

            if size == 0:
                raise AppError(
                    status_code=422,
                    code="EMPTY_FILE",
                    message="Không thể tải lên tệp rỗng.",
                )

            temporary_file.seek(0)
            self._validate_signature(temporary_file, extension)
            temporary_file.seek(0)
            return ValidatedUpload(
                file_object=temporary_file,
                original_filename=filename,
                mime_type=expected_mime,
                extension=extension,
                file_size=size,
                checksum=digest.hexdigest(),
            )
        except Exception:
            temporary_file.close()
            raise

    @staticmethod
    def _validate_filename(raw_filename: str | None) -> str:
        if raw_filename is None:
            raise AppError(
                status_code=422,
                code="MISSING_FILENAME",
                message="Tệp tải lên phải có tên.",
            )
        filename = unicodedata.normalize("NFKC", raw_filename).strip()
        if (
            not filename
            or filename in {".", ".."}
            or len(filename) > 255
            or filename.endswith((".", " "))
            or any(ord(character) < 32 for character in filename)
            or any(character in FORBIDDEN_FILENAME_CHARACTERS for character in filename)
        ):
            raise AppError(
                status_code=422,
                code="UNSAFE_FILENAME",
                message="Tên tệp không an toàn hoặc không hợp lệ.",
            )

        suffixes = [suffix.lower() for suffix in PurePath(filename).suffixes]
        if any(suffix in DANGEROUS_SUFFIXES for suffix in suffixes[:-1]):
            raise AppError(
                status_code=422,
                code="UNSAFE_FILENAME",
                message="Tên tệp chứa phần mở rộng có nguy cơ thực thi.",
            )
        return filename

    @staticmethod
    def _validate_signature(file_object: BinaryIO, extension: str) -> None:
        header = file_object.read(8)
        file_object.seek(0)
        if extension == ".pdf":
            if not header.startswith(b"%PDF-"):
                raise UnsupportedMediaTypeError(
                    "INVALID_FILE_SIGNATURE",
                    "Nội dung tệp không có chữ ký PDF hợp lệ.",
                )
            return

        if not header.startswith(b"PK\x03\x04") or not zipfile.is_zipfile(file_object):
            raise UnsupportedMediaTypeError(
                "INVALID_FILE_SIGNATURE",
                "Nội dung tệp không có chữ ký DOCX hợp lệ.",
            )
        try:
            with zipfile.ZipFile(file_object) as archive:
                members = set(archive.namelist())
                required_members = {"[Content_Types].xml", "word/document.xml"}
                if not required_members.issubset(members):
                    raise UnsupportedMediaTypeError(
                        "INVALID_DOCX_STRUCTURE",
                        "Tệp ZIP không có cấu trúc tài liệu Word hợp lệ.",
                    )
        except (zipfile.BadZipFile, RuntimeError) as exc:
            raise UnsupportedMediaTypeError(
                "INVALID_DOCX_STRUCTURE",
                "Không thể đọc cấu trúc tài liệu Word.",
            ) from exc
