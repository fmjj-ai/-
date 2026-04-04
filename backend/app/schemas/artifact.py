from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

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
        from_attributes = True
