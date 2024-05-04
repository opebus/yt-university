from uuid import uuid4

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import AlchemyBase, MetadataMixin


class User(AlchemyBase, MetadataMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    primary_email_address_id: Mapped[str] = mapped_column(nullable=True)
    email_addresses: Mapped[JSON] = mapped_column(type_=JSON, nullable=True)

    favorites = relationship("Favorite", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
