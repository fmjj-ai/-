from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.template import Template
from app.schemas.template import Template as TemplateSchema, TemplateCreate, TemplateUpdate
from app.schemas.response import StandardResponse

router = APIRouter()

@router.post("/", response_model=StandardResponse[TemplateSchema])
def create_template(template_in: TemplateCreate, db: Session = Depends(get_db)):
    template = Template(**template_in.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return StandardResponse(success=True, data=template)

@router.get("/", response_model=StandardResponse[List[TemplateSchema]])
def get_templates(
    project_id: int = Query(None),
    type: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Template)
    if project_id is not None:
        query = query.filter(Template.project_id == project_id)
    if type is not None:
        query = query.filter(Template.type == type)
    templates = query.order_by(Template.created_at.desc()).offset(skip).limit(limit).all()
    return StandardResponse(success=True, data=templates)

@router.get("/{template_id}", response_model=StandardResponse[TemplateSchema])
def get_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return StandardResponse(success=True, data=template)

@router.put("/{template_id}", response_model=StandardResponse[TemplateSchema])
def update_template(template_id: int, template_in: TemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
        
    db.commit()
    db.refresh(template)
    return StandardResponse(success=True, data=template)

@router.delete("/{template_id}", response_model=StandardResponse[bool])
def delete_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    return StandardResponse(success=True, data=True)
