from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.run import Run
from app.schemas.run import Run as RunSchema, RunCreate, RunUpdate
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[RunSchema])
def create_run(run_in: RunCreate, db: Session = Depends(get_db)):
    run = Run(**run_in.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return StandardResponse(success=True, data=run)

@router.get("/", response_model=StandardResponse[List[RunSchema]])
def get_runs(
    project_id: int = Query(None),
    pipeline_id: int = Query(None),
    status: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Run)
    if project_id is not None:
        query = query.filter(Run.project_id == project_id)
    if pipeline_id is not None:
        query = query.filter(Run.pipeline_id == pipeline_id)
    if status is not None:
        query = query.filter(Run.status == status)
    runs = query.order_by(Run.created_at.desc()).offset(skip).limit(limit).all()
    return StandardResponse(success=True, data=runs)

@router.get("/{run_id}", response_model=StandardResponse[RunSchema])
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return StandardResponse(success=True, data=run)

@router.put("/{run_id}", response_model=StandardResponse[RunSchema])
def update_run(run_id: int, run_in: RunUpdate, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    update_data = run_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)
        
    db.commit()
    db.refresh(run)
    return StandardResponse(success=True, data=run)

@router.delete("/{run_id}", response_model=StandardResponse[bool])
def delete_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    db.delete(run)
    db.commit()
    return StandardResponse(success=True, data=True)
