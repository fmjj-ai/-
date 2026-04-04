from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.project import Project
from app.models.dataset import Dataset
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[ProjectResponse])
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=project_in.name,
        description=project_in.description,
        is_archived=project_in.is_archived
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return StandardResponse(success=True, data=project)

@router.get("/", response_model=StandardResponse[List[ProjectResponse]])
def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Project)
    if not include_archived:
        query = query.filter(Project.is_archived == False)
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    
    # Optional: populate dataset_count
    # Alternatively we can use a subquery for count. For simplicity, do simple query per project or hybrid property
    for p in projects:
        p.dataset_count = db.query(Dataset).filter(Dataset.project_id == p.id).count()

    return StandardResponse(success=True, data=projects)

@router.get("/{project_id}", response_model=StandardResponse[ProjectResponse])
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project.dataset_count = db.query(Dataset).filter(Dataset.project_id == project.id).count()
    return StandardResponse(success=True, data=project)

@router.put("/{project_id}", response_model=StandardResponse[ProjectResponse])
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
        
    db.commit()
    db.refresh(project)
    project.dataset_count = db.query(Dataset).filter(Dataset.project_id == project.id).count()
    return StandardResponse(success=True, data=project)

@router.delete("/{project_id}", response_model=StandardResponse[bool])
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return StandardResponse(success=True, data=True)
