from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.setting import Setting
from app.schemas.setting import Setting as SettingSchema, SettingCreate, SettingUpdate
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[SettingSchema])
def create_setting(setting_in: SettingCreate, db: Session = Depends(get_db)):
    setting = Setting(**setting_in.model_dump())
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return StandardResponse(success=True, data=setting)

@router.get("/", response_model=StandardResponse[List[SettingSchema]])
def get_settings(
    project_id: int = Query(None),
    is_global: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Setting)
    if project_id is not None:
        query = query.filter(Setting.project_id == project_id)
    if is_global is not None:
        query = query.filter(Setting.is_global == is_global)
    settings = query.order_by(Setting.created_at.desc()).offset(skip).limit(limit).all()
    return StandardResponse(success=True, data=settings)

@router.get("/{setting_id}", response_model=StandardResponse[SettingSchema])
def get_setting(setting_id: int, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return StandardResponse(success=True, data=setting)

@router.put("/{setting_id}", response_model=StandardResponse[SettingSchema])
def update_setting(setting_id: int, setting_in: SettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    update_data = setting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)
        
    db.commit()
    db.refresh(setting)
    return StandardResponse(success=True, data=setting)

@router.delete("/{setting_id}", response_model=StandardResponse[bool])
def delete_setting(setting_id: int, db: Session = Depends(get_db)):
    setting = db.query(Setting).filter(Setting.id == setting_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(setting)
    db.commit()
    return StandardResponse(success=True, data=True)
