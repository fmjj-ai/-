from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base

class Task(Base):
    id = Column(String, primary_key=True, index=True) # UUID
    name = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    status = Column(String, nullable=False, default="pending") # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)
    result = Column(JSON, nullable=True)
    error = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    project = relationship("Project", backref="tasks")
    artifacts = relationship("Artifact", back_populates="task")
