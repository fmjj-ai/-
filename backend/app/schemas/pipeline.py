from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    project_id: int

class PipelineCreate(PipelineBase):
    pass

class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None

class PipelineInDBBase(PipelineBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Pipeline(PipelineInDBBase):
    pass
