from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class SettingBase(BaseModel):
    key: str
    value: Dict[str, Any]
    is_global: bool = False
    project_id: Optional[int] = None

class SettingCreate(SettingBase):
    pass

class SettingUpdate(BaseModel):
    key: Optional[str] = None
    value: Optional[Dict[str, Any]] = None
    is_global: Optional[bool] = None
    project_id: Optional[int] = None

class SettingInDBBase(SettingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Setting(SettingInDBBase):
    pass
