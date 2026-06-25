from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    language_stats: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    overview: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dependency_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    architecture_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    complexity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    learning_difficulty: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    owner_user = relationship("User", back_populates="repositories")
    ingestion_jobs = relationship("IngestionJob", back_populates="repository", cascade="all, delete-orphan")
    files = relationship("FileRecord", back_populates="repository", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="repository", cascade="all, delete-orphan")
