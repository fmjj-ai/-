from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class TaskBase(BaseModel):
    name: str
    project_id: int

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    finished_at: Optional[datetime] = None

class TaskResponse(TaskBase):
    id: str
    status: str
    progress: float
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ArtifactBase(BaseModel):
    name: str
    type: str
    project_id: int
    task_id: Optional[str] = None
    file_path: str
    size: Optional[int] = 0

class ArtifactCreate(ArtifactBase):
    pass

class ArtifactResponse(ArtifactBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True
