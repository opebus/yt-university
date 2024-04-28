from uuid import uuid4

from sqlalchemy.orm import Mapped, mapped_column, relationship

# Importing for more specific types
from . import AlchemyBase, MetadataMixin


class User(AlchemyBase, MetadataMixin):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(default=uuid4, primary_key=True, index=True)

    videos = relationship("Favorite", back_populates="user")

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}
