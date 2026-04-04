from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.operation_log import OperationLog
from app.schemas.operation_log import OperationLog as OperationLogSchema, OperationLogCreate, OperationLogUpdate
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[OperationLogSchema])
def create_operation_log(log_in: OperationLogCreate, db: Session = Depends(get_db)):
    log = OperationLog(**log_in.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return StandardResponse(success=True, data=log)

@router.get("/", response_model=StandardResponse[List[OperationLogSchema]])
def get_operation_logs(
    project_id: int = Query(None),
    action: str = Query(None),
    resource_type: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(OperationLog)
    if project_id is not None:
        query = query.filter(OperationLog.project_id == project_id)
    if action is not None:
        query = query.filter(OperationLog.action == action)
    if resource_type is not None:
        query = query.filter(OperationLog.resource_type == resource_type)
    logs = query.order_by(OperationLog.created_at.desc()).offset(skip).limit(limit).all()
    return StandardResponse(success=True, data=logs)

@router.get("/{log_id}", response_model=StandardResponse[OperationLogSchema])
def get_operation_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="OperationLog not found")
    return StandardResponse(success=True, data=log)

@router.put("/{log_id}", response_model=StandardResponse[OperationLogSchema])
def update_operation_log(log_id: int, log_in: OperationLogUpdate, db: Session = Depends(get_db)):
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="OperationLog not found")
    
    update_data = log_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)
        
    db.commit()
    db.refresh(log)
    return StandardResponse(success=True, data=log)

@router.delete("/{log_id}", response_model=StandardResponse[bool])
def delete_operation_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(OperationLog).filter(OperationLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="OperationLog not found")
    
    db.delete(log)
    db.commit()
    return StandardResponse(success=True, data=True)
