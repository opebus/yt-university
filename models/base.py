from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


class MetadataMixin:
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {field.name: getattr(self, field.name) for field in self.__table__.c}


AlchemyBase = declarative_base(cls=MetadataMixin)
