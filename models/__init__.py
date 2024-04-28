from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.orm import InstrumentedAttribute, Relationship, declarative_base
from sqlalchemy.sql import func

from .favorite import Favorite
from .user import User
from .video import Video

AlchemyBase = declarative_base()


class MetadataMixin:
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

    def delete(self):
        if self.deleted_at is None:
            # only update deleted date if not already deleted
            self.deleted_at = datetime.now()

    def undelete(self):
        self.deleted_at = None


def deleted_at_set_listener(target, value, old_value, initiator):
    if isinstance(target, MetadataMixin):
        target._deleted_at_updated = value != old_value
        for name, attr in vars(type(target)).items():
            if (
                isinstance(attr, InstrumentedAttribute)
                and isinstance(attr.property, Relationship)
                and attr.property.uselist
            ):
                for item in getattr(target, name):
                    if isinstance(item, MetadataMixin):
                        if value:
                            item.delete()
                        else:
                            item.undelete()
