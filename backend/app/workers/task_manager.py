import asyncio
import uuid
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from app.db.session import SessionLocal
from app.models.task import Task
from app.models.artifact import Artifact

logger = logging.getLogger(__name__)

def _task_wrapper(task_id: str, q, func: Callable, *args, **kwargs):
    def update_progress(progress: float, status: str = "running"):
        q.put({
            "task_id": task_id,
            "progress": progress,
            "status": status
        })

    kwargs['update_progress'] = update_progress

    try:
        res = func(*args, **kwargs)
        q.put({
            "task_id": task_id,
            "progress": 100.0,
            "status": "completed",
            "result": res
        })
        return res
    except Exception as e:
        q.put({
            "task_id": task_id,
            "status": "failed",
            "error": str(e)
        })
        raise

class TaskManager:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.pool = None
        self.tasks: Dict[str, asyncio.Task] = {}
        self.listeners: Dict[str, asyncio.Queue] = {} # 用于 SSE 的订阅队列
        self._manager = None
        self._progress_queue = None

    def _init_pool(self):
        if self.pool is None:
            self._manager = Manager()
            self._progress_queue = self._manager.Queue()
            self.pool = ProcessPoolExecutor(max_workers=self.max_workers)

    async def start_progress_listener(self):
        """主进程监听子进程进度并更新 DB / 推送 SSE"""
        self._init_pool()
        loop = asyncio.get_running_loop()
        while True:
            # 这是一个阻塞调用，我们用 run_in_executor 让它不阻塞主循环
            msg = await loop.run_in_executor(None, self._progress_queue.get)
            if msg is None:
                continue
                
            task_id = msg.get("task_id")
            progress = msg.get("progress")
            status = msg.get("status")
            result = msg.get("result")
            error = msg.get("error")
            
            # 更新数据库
            try:
                with SessionLocal() as db:
                    task_db = db.query(Task).filter(Task.id == task_id).first()
                    if task_db:
                        if progress is not None:
                            task_db.progress = progress
                        if status:
                            task_db.status = status
                        if result is not None:
                            task_db.result = result
                        if error is not None:
                            task_db.error = error
                        if status in ("completed", "failed", "cancelled"):
                            task_db.finished_at = datetime.utcnow()
                        db.commit()
            except Exception as e:
                logger.error(f"Failed to update task {task_id} status in DB: {e}")

            # 推送到 SSE
            await self._broadcast_sse({
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "result": result,
                "error": error
            })

    async def _broadcast_sse(self, data: dict):
        # 推送给所有订阅者
        for q in self.listeners.values():
            await q.put(data)

    def subscribe(self) -> tuple[str, asyncio.Queue]:
        client_id = str(uuid.uuid4())
        q = asyncio.Queue()
        self.listeners[client_id] = q
        return client_id, q

    def unsubscribe(self, client_id: str):
        if client_id in self.listeners:
            del self.listeners[client_id]

    async def submit_task(self, task_project_id: int, name: str, func: Callable, *args, **kwargs) -> str:
        task_id = str(uuid.uuid4())

        # 写入数据库
        with SessionLocal() as db:
            task_db = Task(
                id=task_id,
                name=name,
                project_id=task_project_id,
                status="running",
                started_at=datetime.utcnow()
            )
            db.add(task_db)
            db.commit()
            
        loop = asyncio.get_running_loop()
        self._init_pool()
        import functools
        bound_func = functools.partial(_task_wrapper, task_id, self._progress_queue, func, *args, **kwargs)
        future = loop.run_in_executor(self.pool, bound_func)
        self.tasks[task_id] = future
        return task_id

task_manager = TaskManager()
