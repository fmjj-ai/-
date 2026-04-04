from sqlalchemy import Column, String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base

class Pipeline(Base):
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False, default=[])
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False, index=True)

    project = relationship("Project", backref="pipelines")
    runs = relationship("Run", back_populates="pipeline", cascade="all, delete-orphan")
