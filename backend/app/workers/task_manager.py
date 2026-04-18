import asyncio
import functools
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from multiprocessing import Manager
from typing import Any, Callable, Dict, Optional

from app.db.session import SessionLocal
from app.models.artifact import Artifact
from app.models.task import Task

logger = logging.getLogger(__name__)


def _merge_task_result(existing: Any, result: Any, metadata: Optional[Dict[str, Any]]) -> Any:
    if isinstance(existing, dict):
        merged = dict(existing)
    else:
        merged = {}
    if isinstance(metadata, dict):
        merged.update(metadata)
    if isinstance(result, dict):
        merged.update(result)
        return merged
    if merged:
        merged["value"] = result
        return merged
    return result


def _task_wrapper(task_id: str, q, func: Callable, *args, **kwargs):
    def update_progress(progress: float, status: str = "running"):
        q.put({
            "task_id": task_id,
            "progress": progress,
            "status": status,
        })

    kwargs["update_progress"] = update_progress

    try:
        res = func(*args, **kwargs)
        q.put({
            "task_id": task_id,
            "progress": 100.0,
            "status": "completed",
            "result": res,
        })
        return res
    except Exception as exc:
        q.put({
            "task_id": task_id,
            "status": "failed",
            "error": str(exc),
        })
        raise


class TaskManager:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.pool = None
        self.tasks: Dict[str, asyncio.Task] = {}
        self.listeners: Dict[str, asyncio.Queue] = {}
        self._manager = None
        self._progress_queue = None

    def _init_pool(self):
        if self.pool is None:
            self._manager = Manager()
            self._progress_queue = self._manager.Queue()
            self.pool = ProcessPoolExecutor(max_workers=self.max_workers)

    async def start_progress_listener(self):
        self._init_pool()
        loop = asyncio.get_running_loop()
        while True:
            msg = await loop.run_in_executor(None, self._progress_queue.get)
            if msg is None:
                continue

            task_id = msg.get("task_id")
            progress = msg.get("progress")
            status = msg.get("status")
            result = msg.get("result")
            error = msg.get("error")

            try:
                final_result = result
                with SessionLocal() as db:
                    task_db = db.query(Task).filter(Task.id == task_id).first()
                    if task_db:
                        if progress is not None:
                            task_db.progress = progress
                        if status:
                            task_db.status = status
                        if result is not None:
                            task_db.result = _merge_task_result(task_db.result, result, None)
                        if error is not None:
                            task_db.error = error
                        if status in ("completed", "failed", "cancelled"):
                            task_db.finished_at = datetime.utcnow()
                        db.commit()

                        final_result = task_db.result if isinstance(task_db.result, dict) else result
                        if status == "completed" and isinstance(final_result, dict):
                            artifacts = final_result.get("artifacts") or []
                            for artifact_data in artifacts:
                                file_path = artifact_data.get("file_path")
                                if not file_path:
                                    continue
                                exists = db.query(Artifact).filter(
                                    Artifact.project_id == task_db.project_id,
                                    Artifact.task_id == task_id,
                                    Artifact.file_path == file_path,
                                ).first()
                                if exists:
                                    continue
                                db.add(Artifact(
                                    project_id=task_db.project_id,
                                    task_id=task_id,
                                    name=str(artifact_data.get("name") or "未命名产物"),
                                    type=str(artifact_data.get("type") or "file"),
                                    file_path=str(file_path),
                                    size=int(artifact_data.get("size") or 0),
                                ))
                            db.commit()
            except Exception as exc:
                logger.error("Failed to update task %s status in DB: %s", task_id, exc)

            await self._broadcast_sse({
                "task_id": task_id,
                "progress": progress,
                "status": status,
                "result": final_result,
                "error": error,
            })

    async def _broadcast_sse(self, data: dict):
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

    async def submit_task(self, task_project_id: int, name: str, func: Callable, *args, metadata: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        task_id = str(uuid.uuid4())
        with SessionLocal() as db:
            task_db = Task(
                id=task_id,
                name=name,
                project_id=task_project_id,
                status="running",
                progress=0.0,
                result=metadata or None,
                started_at=datetime.utcnow(),
            )
            db.add(task_db)
            db.commit()

        loop = asyncio.get_running_loop()
        self._init_pool()
        bound_func = functools.partial(_task_wrapper, task_id, self._progress_queue, func, *args, **kwargs)
        future = loop.run_in_executor(self.pool, bound_func)
        self.tasks[task_id] = future
        return task_id


task_manager = TaskManager()
