from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
import os

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.workers.task_manager import task_manager
from app.workers.modeling_worker import run_clustering_task, run_predictive_modeling_task

router = APIRouter()

@router.post("/{dataset_id}/clustering", response_model=StandardResponse[str])
async def start_clustering(
    dataset_id: int,
    config: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    启动聚类长任务
    config = {
        "features": ["col1", "col2"],
        "algorithm": "kmeans", # kmeans, dbscan, hdbscan, meanshift
        "n_clusters": 0, # 0 means auto for kmeans
        "eps": 0.5,
        "min_samples": 5,
        "min_cluster_size": 5
    }
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")

    task_id = await task_manager.submit_task(
        dataset.project_id,
        f"聚类分析 - {dataset.name}",
        run_clustering_task,
        dataset_id=dataset.id,
        file_path=dataset.file_path,
        config=config,
        project_id=dataset.project_id,
        metadata={
            "kind": "clustering",
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
        },
    )

    return StandardResponse(success=True, data=task_id)

@router.post("/{dataset_id}/predictive", response_model=StandardResponse[str])
async def start_predictive_modeling(
    dataset_id: int,
    config: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    启动分类/回归建模长任务
    config = {
        "target": "y",
        "features": ["x1", "x2"],
        "task_type": "classification", # classification or regression
        "algorithm": "rf", # rf, xgb, lgbm, mlp
    }
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")

    task_id = await task_manager.submit_task(
        dataset.project_id,
        f"预测建模 - {dataset.name}",
        run_predictive_modeling_task,
        dataset_id=dataset.id,
        file_path=dataset.file_path,
        config=config,
        project_id=dataset.project_id,
        metadata={
            "kind": "predictive_modeling",
            "dataset_id": dataset.id,
            "dataset_name": dataset.name,
            "task_type": str(config.get("task_type", "") or ""),
        },
    )

    return StandardResponse(success=True, data=task_id)
