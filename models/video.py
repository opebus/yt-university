from uuid import uuid4

from sqlalchemy.dialects.postgresql import (
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

# Importing for more specific types
from . import AlchemyBase, MetadataMixin


class Video(AlchemyBase, MetadataMixin):
    __tablename__ = "video"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(index=True, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(nullable=True)
    channel: Mapped[str] = mapped_column(nullable=True)
    channel_id: Mapped[str] = mapped_column(nullable=True)
    uploaded_at: Mapped[str] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[int] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(nullable=True)
    transcription: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)
    summary: Mapped[str] = mapped_column(nullable=True)
