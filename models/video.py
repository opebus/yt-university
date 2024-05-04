from uuid import uuid4

from sqlalchemy.dialects.postgresql import (
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Importing for more specific types
from .base import AlchemyBase, MetadataMixin


class Video(AlchemyBase, MetadataMixin):
    __tablename__ = "video"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(index=True, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(nullable=True)
    channel: Mapped[str] = mapped_column(nullable=True)
    channel_id: Mapped[str] = mapped_column(nullable=True)
    uploaded_at: Mapped[str] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    thumbnail: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[int] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(nullable=True)
    transcription: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)
    summary: Mapped[str] = mapped_column(nullable=True)
    category: Mapped[str] = mapped_column(nullable=True)
    favorite_count: Mapped[int] = mapped_column(server_default="0", nullable=False)

    favorited_users = relationship("Favorite", back_populates="video")
    playlists = relationship("PlaylistVideo", back_populates="video")

    def increment_favorite(self):
        self.favorite_count += 1

    def decrement_favorite(self):
        if self.favorite_count > 0:
            self.favorite_count -= 1
