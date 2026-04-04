from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class DatasetBase(BaseModel):
    name: str
    project_id: int

class DatasetCreate(DatasetBase):
    pass

class DatasetUpdate(BaseModel):
    name: Optional[str] = None

class DatasetSnapshotResponse(BaseModel):
    id: int
    dataset_id: int
    version: int
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    schema_info: Optional[List[Dict[str, Any]]] = None
    file_path: str
    file_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DatasetResponse(DatasetBase):
    id: int
    source_file_name: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    schema_info: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    snapshots: List[DatasetSnapshotResponse] = []

    model_config = ConfigDict(from_attributes=True)
