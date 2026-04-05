from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
import os
import pandas as pd

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.services.quick_cleaning_service import QuickCleaningService

router = APIRouter()


@router.get("/capabilities", response_model=StandardResponse[dict])
def get_quick_cleaning_capabilities():
    return StandardResponse(success=True, data={
        "capabilities": QuickCleaningService.get_capabilities(),
        "validation": QuickCleaningService.get_validation_rules(),
    })


@router.get("/{dataset_id}/missing-stats", response_model=StandardResponse[dict])
def get_missing_stats(dataset_id: int, db: Session = Depends(get_db)):
    dataset = _get_dataset(dataset_id, db)
    df = pd.read_parquet(dataset.file_path)
    return StandardResponse(success=True, data=QuickCleaningService.get_missing_stats(df))


@router.post("/{dataset_id}/outlier-preview", response_model=StandardResponse[dict])
def preview_outliers(
    dataset_id: int,
    column: str = Body(..., embed=True),
    method: str = Body("iqr", embed=True),
    z_threshold: float = Body(3.0, embed=True),
    db: Session = Depends(get_db),
):
    dataset = _get_dataset(dataset_id, db)
    df = pd.read_parquet(dataset.file_path)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列不存在: {column}")
    try:
        result = QuickCleaningService.preview_outliers(
            df,
            column=column,
            method=method,
            z_threshold=z_threshold,
        )
        return StandardResponse(success=True, data=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/outlier-handle", response_model=StandardResponse[dict])
def handle_outliers(
    dataset_id: int,
    column: str = Body(..., embed=True),
    method: str = Body("iqr", embed=True),
    strategy: str = Body("clip", embed=True),
    z_threshold: float = Body(3.0, embed=True),
    db: Session = Depends(get_db),
):
    dataset = _get_dataset(dataset_id, db)
    df = pd.read_parquet(dataset.file_path)
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"列不存在: {column}")
    try:
        result = QuickCleaningService.handle_outliers(
            df,
            column=column,
            method=method,
            strategy=strategy,
            z_threshold=z_threshold,
        )
        df.to_parquet(dataset.file_path, engine="pyarrow")
        dataset.row_count = len(df)
        dataset.col_count = len(df.columns)
        dataset.schema_info = [{"name": str(col), "type": str(dtype)} for col, dtype in df.dtypes.items()]
        db.commit()
        return StandardResponse(success=True, data=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"异常值处理失败: {str(exc)}") from exc



def _get_dataset(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
    return dataset
