from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.services.quick_report_service import QuickReportService

router = APIRouter()


@router.get("/capabilities", response_model=StandardResponse[dict])
def get_quick_report_capabilities():
    return StandardResponse(success=True, data={
        "capabilities": QuickReportService.get_capabilities(),
        "generation_steps": QuickReportService.get_generation_steps(),
    })


@router.post("/{dataset_id}/html", response_class=HTMLResponse)
def generate_quick_html_report(
    dataset_id: int,
    title: str = Body("快速分析报告", embed=True),
    blocks: List[Dict[str, Any]] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    html = QuickReportService.render_html_report(title=title, dataset_name=dataset.name, blocks=blocks)
    return HTMLResponse(content=html)
