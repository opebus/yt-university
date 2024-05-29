from uuid import uuid4

from sqlalchemy import ARRAY, Float, ForeignKey
from sqlalchemy.dialects.postgresql import (
    JSON,
)
from sqlalchemy.orm import Mapped, deferred, mapped_column, relationship

from .base import AlchemyBase
from .playlist import playlist_video
from .user import favorite


class Video(AlchemyBase):
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
    transcription: Mapped[JSON] = deferred(mapped_column(type_=JSON, nullable=True))
    summary: Mapped[str] = deferred(mapped_column(nullable=True))
    category: Mapped[str] = mapped_column(nullable=True)
    favorite_count: Mapped[int] = mapped_column(server_default="0", nullable=False)
    embedding: Mapped[ARRAY(Float)] = mapped_column(
        type_=ARRAY(Float, dimensions=1), nullable=True
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=True)
    uploaded_by = relationship("User", back_populates="videos", uselist=False)

    favorited_by = relationship("User", secondary=favorite, back_populates="favorites")
    playlists = relationship(
        "Playlist", secondary=playlist_video, back_populates="videos"
    )
