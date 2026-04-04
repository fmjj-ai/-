from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Project(Base):
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
