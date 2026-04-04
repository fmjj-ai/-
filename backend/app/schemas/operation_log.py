from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class OperationLogBase(BaseModel):
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    project_id: Optional[int] = None

class OperationLogCreate(OperationLogBase):
    pass

class OperationLogUpdate(BaseModel):
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    project_id: Optional[int] = None

class OperationLogInDBBase(OperationLogBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class OperationLog(OperationLogInDBBase):
    pass
