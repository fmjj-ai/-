from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class RunBase(BaseModel):
    status: str = "pending"
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    project_id: int
    pipeline_id: Optional[int] = None
    snapshot_id: Optional[int] = None

class RunCreate(RunBase):
    pass

class RunUpdate(BaseModel):
    status: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    error_info: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class RunInDBBase(RunBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Run(RunInDBBase):
    pass
