from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class Dataset(Base):
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    source_file_name = Column(String(255), nullable=True)
    status = Column(String(50), default="importing") # importing, ready, failed
    error_message = Column(Text, nullable=True)
    
    # Working copy info
    file_path = Column(String(500), nullable=True) # Parquet or CSV path
    row_count = Column(Integer, nullable=True)
    col_count = Column(Integer, nullable=True)
    schema_info = Column(JSON, nullable=True) # [{"name": "col1", "type": "string"}, ...]
    
    project = relationship("Project", back_populates="datasets")
    snapshots = relationship("DatasetSnapshot", back_populates="dataset", cascade="all, delete-orphan")

class DatasetSnapshot(Base):
    dataset_id = Column(Integer, ForeignKey("dataset.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    row_count = Column(Integer, nullable=True)
    col_count = Column(Integer, nullable=True)
    schema_info = Column(JSON, nullable=True)
    
    file_path = Column(String(500), nullable=False)
    file_hash = Column(String(100), nullable=True)
    
    dataset = relationship("Dataset", back_populates="snapshots")
