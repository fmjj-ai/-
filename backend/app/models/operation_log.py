from sqlalchemy import Column, String, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base

class OperationLog(Base):
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(Integer, nullable=True, index=True)
    details = Column(JSON, nullable=True)
    
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)

    project = relationship("Project", backref="operation_logs")
