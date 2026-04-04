from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base

class Setting(Base):
    key = Column(String(100), nullable=False, index=True)
    value = Column(JSON, nullable=False)
    is_global = Column(Boolean, default=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)

    project = relationship("Project", backref="settings")
