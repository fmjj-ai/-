from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.workers.task_manager import task_manager
from app.workers.sentiment_worker import run_sentiment_task

router = APIRouter()

@router.post("/{dataset_id}/analyze", response_model=StandardResponse[str])
async def start_sentiment_analysis(
    dataset_id: int,
    config: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    启动情感分析长任务
    config = {
        "text_column": "content",
        "use_jieba": True,
        "stopwords": ["的", "了", ...],
        "method": "snownlp", # snownlp or deepseek
        "extract_tfidf": True,
        "top_k": 20,
        "generate_wordcloud": True
    }
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")

    task_id = await task_manager.submit_task(
        dataset.project_id,
        f"情感分析 - {dataset.name}",
        run_sentiment_task,
        dataset_id=dataset.id,
        file_path=dataset.file_path,
        config=config,
        project_id=dataset.project_id
    )

    return StandardResponse(success=True, data=task_id)
