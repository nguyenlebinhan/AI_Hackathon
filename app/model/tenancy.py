from __future__ import annotations

from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin


class Province(TimestampMixin, Base):
    __tablename__ = "provinces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    communes: Mapped[list[Commune]] = relationship(
        "Commune",
        back_populates="province",
        passive_deletes=True,
    )


class Commune(TimestampMixin, Base):
    __tablename__ = "communes"
    __table_args__ = (
        UniqueConstraint("province_id", "name", name="uq_communes_province_name"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    province_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("provinces.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    province: Mapped[Province] = relationship("Province", back_populates="communes")
    users = relationship("User", back_populates="commune", passive_deletes=True)

