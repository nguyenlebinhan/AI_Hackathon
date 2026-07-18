from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid
from app.model.processing import ProcessingStatus

if TYPE_CHECKING:
    from app.model.chunking import DocumentChunk
    from app.model.extraction import DocumentPage, DocumentTable
    from app.model.processing import ProcessingJob
    from app.model.storage import DocumentFile
    from app.model.structure import DocumentSection
    from app.model.users import User
    from app.model.workspaces import Workspace


class DocumentType(str, Enum):
    TEXT_BASED = "TEXT_BASED"
    SCANNED = "SCANNED"
    HYBRID = "HYBRID"
    DOCX = "DOCX"


class DocumentApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "uq_documents_workspace_checksum_active",
            "workspace_id",
            "checksum",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        UniqueConstraint("id", "commune_id", name="uq_documents_id_commune"),
        CheckConstraint(
            "(is_deleted = false AND deleted_at IS NULL) OR "
            "(is_deleted = true AND deleted_at IS NOT NULL)",
            name="documents_soft_delete_consistent",
        ),
        Index("ix_documents_commune_deleted", "commune_id", "is_deleted"),
        Index("ix_documents_commune_owner", "commune_id", "owner_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("doc"))
    # Nullable only during the staged legacy-data migration. Every /api/v1
    # repository requires an exact non-null tenant match.
    commune_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("communes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    owner_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_status: Mapped[DocumentApprovalStatus] = mapped_column(
        SAEnum(
            DocumentApprovalStatus,
            name="document_approval_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=DocumentApprovalStatus.DRAFT,
        index=True,
    )
    meeting_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(
            ProcessingStatus,
            name="document_processing_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ProcessingStatus.UPLOADED,
        index=True,
    )
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_type: Mapped[DocumentType | None] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=True,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    deleted_by: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="documents")
    uploader: Mapped["User | None"] = relationship(
        "User",
        back_populates="documents",
        foreign_keys=[uploaded_by],
    )
    owner: Mapped["User | None"] = relationship("User", foreign_keys=[owner_id])
    deleter: Mapped["User | None"] = relationship("User", foreign_keys=[deleted_by])
    files: Mapped[list["DocumentFile"]] = relationship("DocumentFile", back_populates="document")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProcessingJob.attempt",
    )
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    sections: Mapped[list["DocumentSection"]] = relationship(
        "DocumentSection", back_populates="document", cascade="all, delete-orphan"
    )
    tables: Mapped[list["DocumentTable"]] = relationship(
        "DocumentTable", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
