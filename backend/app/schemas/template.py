from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str
    content: Dict[str, Any]
    project_id: Optional[int] = None

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    project_id: Optional[int] = None

class TemplateInDBBase(TemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Template(TemplateInDBBase):
    pass
