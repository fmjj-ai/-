from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Any, Dict
import hashlib
import os

from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.task import Task
from app.schemas.response import StandardResponse
from app.workers.task_manager import task_manager
from app.workers.sentiment_worker import build_sentiment_signature, run_sentiment_task

router = APIRouter()


def _get_file_hash(file_path: str) -> str:
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


@router.post("/{dataset_id}/analyze", response_model=StandardResponse[str])
async def start_sentiment_analysis(
    dataset_id: int,
    config: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """启动情感分析长任务，并避免相同数据+相同配置的重复提交。"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")

    dataset_fingerprint = _get_file_hash(dataset.file_path)
    signature = build_sentiment_signature(dataset_fingerprint, config)

    duplicate_task = (
        db.query(Task)
        .filter(Task.project_id == dataset.project_id, Task.name == f"情感分析 - {dataset.name}")
        .order_by(Task.started_at.desc())
        .all()
    )
    for task in duplicate_task:
        result = task.result or {}
        if isinstance(result, dict) and result.get("signature") == signature and task.status in {"running", "completed"}:
            return StandardResponse(success=True, data=task.id)

    task_id = await task_manager.submit_task(
        dataset.project_id,
        f"情感分析 - {dataset.name}",
        run_sentiment_task,
        dataset_id=dataset.id,
        file_path=dataset.file_path,
        config=config,
        project_id=dataset.project_id,
        metadata={
            "kind": "sentiment_analysis",
            "dataset_id": dataset.id,
            "signature": signature,
            "dataset_fingerprint": dataset_fingerprint,
        },
    )

    return StandardResponse(success=True, data=task_id)
