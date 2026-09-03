from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RomMetadata(Base):
    __tablename__ = "rom_metadata"

    rom_id: Mapped[str] = mapped_column(ForeignKey("rom_entries.id", ondelete="CASCADE"), primary_key=True)
    matched_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    developer: Mapped[str | None] = mapped_column(String(180), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(180), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(40), nullable=True)
    genres: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    background_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
