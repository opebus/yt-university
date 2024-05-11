from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import AlchemyBase

favorite = Table(
    "favorite",
    AlchemyBase.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("video_id", ForeignKey("video.id"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now()),
)


class User(AlchemyBase):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    primary_email_address_id: Mapped[str] = mapped_column(nullable=True)
    email_addresses: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)

    videos = relationship("Video", back_populates="uploaded_by")
    favorites = relationship("Video", secondary=favorite, back_populates="favorited_by")
    playlists = relationship("Playlist", back_populates="user")
