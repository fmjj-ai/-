import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.api import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
    app_exception_handler,
    global_exception_handler,
)
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.schemas.response import StandardResponse
from app.workers.task_manager import task_manager

# 1. 配置日志
setup_logging()

# 2. 自动创建数据库表（如果不存在的话）
# 实际生产中通常使用 Alembic 进行数据库迁移，但为了快速启动和测试这里可以直接创建
Base.metadata.create_all(bind=engine)


async def _shutdown_task_manager(listener_task: asyncio.Task) -> None:
    if task_manager._progress_queue is not None:
        try:
            task_manager._progress_queue.put(None)
        except Exception:
            pass

    listener_task.cancel()
    with suppress(asyncio.CancelledError, TimeoutError):
        await asyncio.wait_for(listener_task, timeout=2)

    if task_manager.pool is not None:
        task_manager.pool.shutdown(wait=False, cancel_futures=True)
        task_manager.pool = None
    if task_manager._manager is not None:
        task_manager._manager.shutdown()
        task_manager._manager = None
        task_manager._progress_queue = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动任务进度监听
    listener_task = asyncio.create_task(task_manager.start_progress_listener())
    yield
    # 关闭时取消任务
    await _shutdown_task_manager(listener_task)


# 3. 初始化 FastAPI 应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# 4. 配置 CORS 中间件
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 5. 注册全局异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理 Pydantic 参数校验异常，并转换为标准的业务异常格式
    """
    errors = exc.errors()
    # 将校验错误信息放入 debug_info 中
    validation_exc = ValidationException(debug_info={"detail": errors})
    return await app_exception_handler(request, validation_exc)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    处理 404 等标准 HTTP 异常
    """
    if exc.status_code == 404:
        return await app_exception_handler(request, NotFoundException())

    error_content = {
        "success": False,
        "error": {
            "error_code": f"HTTP_ERROR_{exc.status_code}",
            "message": str(exc.detail),
            "debug_info": None,
            "suggestion": "请检查请求参数或稍后重试",
        },
    }
    return JSONResponse(status_code=exc.status_code, content=error_content)


# 6. 注册路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", response_model=StandardResponse[str])
def root():
    return StandardResponse(success=True, data=f"Welcome to {settings.PROJECT_NAME} API")
