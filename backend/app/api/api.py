from fastapi import APIRouter

from app.api.endpoints import (
    artifacts,
    chart_calculations,
    datasets,
    modeling,
    operation_logs,
    pipelines,
    processing,
    projects,
    quick_cleaning,
    quick_reports,
    runs,
    sentiment,
    settings,
    statistics,
    tasks,
    templates,
    theme_palettes,
)
from app.schemas.response import StandardResponse

api_router = APIRouter()

api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])
api_router.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"])
api_router.include_router(modeling.router, prefix="/modeling", tags=["modeling"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(operation_logs.router, prefix="/operation-logs", tags=["operation_logs"])
api_router.include_router(quick_cleaning.router, prefix="/quick-cleaning", tags=["quick_cleaning"])
api_router.include_router(chart_calculations.router, prefix="/chart-calculations", tags=["chart_calculations"])
api_router.include_router(theme_palettes.router, prefix="/theme-palettes", tags=["theme_palettes"])
api_router.include_router(quick_reports.router, prefix="/quick-reports", tags=["quick_reports"])


@api_router.get("/health", response_model=StandardResponse[str])
def health_check():
    """
    健康检查接口
    """
    return StandardResponse(success=True, data="ok")
