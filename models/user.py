from uuid import uuid4

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AlchemyBase, MetadataMixin


class User(AlchemyBase, MetadataMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)

    favorites = relationship("Favorite", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
