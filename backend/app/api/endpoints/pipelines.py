from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.pipeline import Pipeline
from app.schemas.pipeline import Pipeline as PipelineSchema, PipelineCreate, PipelineUpdate
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[PipelineSchema])
def create_pipeline(pipeline_in: PipelineCreate, db: Session = Depends(get_db)):
    pipeline = Pipeline(**pipeline_in.model_dump())
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return StandardResponse(success=True, data=pipeline)

@router.get("/", response_model=StandardResponse[List[PipelineSchema]])
def get_pipelines(
    project_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Pipeline)
    if project_id is not None:
        query = query.filter(Pipeline.project_id == project_id)
    pipelines = query.order_by(Pipeline.created_at.desc()).offset(skip).limit(limit).all()
    return StandardResponse(success=True, data=pipelines)

@router.get("/{pipeline_id}", response_model=StandardResponse[PipelineSchema])
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return StandardResponse(success=True, data=pipeline)

@router.put("/{pipeline_id}", response_model=StandardResponse[PipelineSchema])
def update_pipeline(pipeline_id: int, pipeline_in: PipelineUpdate, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    update_data = pipeline_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pipeline, field, value)
        
    db.commit()
    db.refresh(pipeline)
    return StandardResponse(success=True, data=pipeline)

@router.delete("/{pipeline_id}", response_model=StandardResponse[bool])
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    db.delete(pipeline)
    db.commit()
    return StandardResponse(success=True, data=True)
