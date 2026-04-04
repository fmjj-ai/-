from sqlalchemy import Column, String, ForeignKey, JSON, Integer, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class Run(Base):
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, running, success, failed
    params = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    error_info = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipeline.id"), nullable=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("dataset_snapshot.id"), nullable=True, index=True)

    project = relationship("Project", backref="runs")
    pipeline = relationship("Pipeline", back_populates="runs")
    snapshot = relationship("DatasetSnapshot", backref="runs")
