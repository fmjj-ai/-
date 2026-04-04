import asyncio
import json
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.task import Task
from app.schemas.task import TaskResponse
from app.schemas.response import StandardResponse
from app.workers.task_manager import task_manager

router = APIRouter()

@router.get("/", response_model=StandardResponse[List[TaskResponse]])
def get_tasks(project_id: int, db: Session = Depends(get_db)):
    """获取项目下的所有任务"""
    tasks = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).all()
    return StandardResponse(success=True, data=tasks)

@router.get("/{task_id}", response_model=StandardResponse[TaskResponse])
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return StandardResponse(success=True, data=task)

@router.delete("/{task_id}", response_model=StandardResponse[str])
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务记录"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return StandardResponse(success=True, data="Task deleted")

@router.get("/stream/events")
async def sse_events(request: Request):
    """SSE端点，用于实时推送任务进度"""
    client_id, q = task_manager.subscribe()
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    data = await asyncio.wait_for(q.get(), timeout=1.0)
                    # SSE 格式: "data: {...}\n\n"
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # 心跳包以保持连接
                    yield ": ping\n\n"
        finally:
            task_manager.unsubscribe(client_id)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
