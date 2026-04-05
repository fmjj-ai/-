from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import os
import pandas as pd

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.services.chart_calculation_service import ChartCalculationService

router = APIRouter()


@router.get("/capabilities", response_model=StandardResponse[dict])
def get_chart_calculation_capabilities():
    return StandardResponse(success=True, data={
        "capabilities": ChartCalculationService.get_capabilities(),
        "response_contract": ChartCalculationService.get_response_contract(),
    })


@router.post("/{dataset_id}/histogram", response_model=StandardResponse[Dict[str, Any]])
def histogram(
    dataset_id: int,
    column: str = Body(..., embed=True),
    bins: int = Body(20, embed=True),
    db: Session = Depends(get_db)
):
    df = _load_dataset_df(dataset_id, db)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列不存在: {column}")
    return StandardResponse(success=True, data=ChartCalculationService.compute_histogram(df, column, bins))


@router.post("/{dataset_id}/boxplot", response_model=StandardResponse[Dict[str, Any]])
def boxplot(
    dataset_id: int,
    column: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    df = _load_dataset_df(dataset_id, db)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列不存在: {column}")
    return StandardResponse(success=True, data=ChartCalculationService.compute_boxplot(df, column))


@router.post("/{dataset_id}/wordcloud", response_model=StandardResponse[Dict[str, Any]])
def wordcloud(
    dataset_id: int,
    text_column: str = Body(..., embed=True),
    top_n: int = Body(80, embed=True),
    stopwords: Optional[list[str]] = Body(None, embed=True),
    min_length: int = Body(2, embed=True),
    db: Session = Depends(get_db)
):
    df = _load_dataset_df(dataset_id, db)
    if text_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列不存在: {text_column}")
    return StandardResponse(success=True, data=ChartCalculationService.compute_wordcloud(df, text_column, top_n, stopwords, min_length))


@router.post("/{dataset_id}/aggregate", response_model=StandardResponse[Dict[str, Any]])
def aggregate(
    dataset_id: int,
    group_by: str = Body(..., embed=True),
    metric: Optional[str] = Body(None, embed=True),
    agg_method: str = Body("count", embed=True),
    top_n: int = Body(50, embed=True),
    db: Session = Depends(get_db)
):
    df = _load_dataset_df(dataset_id, db)
    return StandardResponse(success=True, data=ChartCalculationService.compute_aggregation(df, group_by, metric, agg_method, top_n))


def _load_dataset_df(dataset_id: int, db: Session) -> pd.DataFrame:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
    return pd.read_parquet(dataset.file_path)
