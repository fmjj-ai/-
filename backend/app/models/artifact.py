from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Artifact(Base):
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    task_id = Column(String, ForeignKey("task.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # csv, pdf, png, svg, html, etc.
    file_path = Column(String, nullable=False)
    size = Column(Integer, default=0)
    
    project = relationship("Project", backref="artifacts")
    task = relationship("Task", back_populates="artifacts")
