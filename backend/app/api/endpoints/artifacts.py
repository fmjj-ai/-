import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.db.session import get_db
from app.models.artifact import Artifact
from app.models.project import Project
from app.schemas.artifact import ArtifactResponse
from app.schemas.response import StandardResponse

router = APIRouter()


def _build_download_filename(artifact: Artifact) -> str:
    name = str(artifact.name or "artifact").strip() or "artifact"
    if Path(name).suffix:
        return name

    file_ext = Path(str(artifact.file_path or "")).suffix
    if file_ext:
        return f"{name}{file_ext}"

    type_ext_map = {
        "html": ".html",
        "markdown": ".md",
        "md": ".md",
        "csv": ".csv",
        "json": ".json",
        "txt": ".txt",
        "pdf": ".pdf",
        "png": ".png",
        "svg": ".svg",
        "jpg": ".jpg",
        "jpeg": ".jpeg",
    }
    inferred_ext = type_ext_map.get(str(artifact.type or "").strip().lower(), "")
    return f"{name}{inferred_ext}"


def _build_media_type(artifact: Artifact, download_filename: str) -> str:
    media_type, _ = mimetypes.guess_type(download_filename)
    if not media_type:
        media_type, _ = mimetypes.guess_type(str(artifact.file_path or ""))
    return media_type or "application/octet-stream"


def _infer_type_from_path(file_name: str, content_type: Optional[str] = None) -> str:
    suffix = Path(file_name).suffix.lstrip(".").lower()
    if suffix:
        return suffix
    if content_type and "/" in content_type:
        return content_type.split("/", 1)[1].lower()
    return "file"


def _get_artifact_or_404(artifact_id: int, db: Session) -> Artifact:
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if not os.path.exists(artifact.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    return artifact


@router.get("/", response_model=StandardResponse[List[ArtifactResponse]])
def list_artifacts(
    project_id: int,
    type: Optional[str] = Query(None),
    name_prefix: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """列出项目下产物，支持按类型、名称前缀、任务过滤。"""
    query = (
        db.query(Artifact)
        .options(joinedload(Artifact.task))
        .filter(Artifact.project_id == project_id)
    )

    if type:
        query = query.filter(Artifact.type == type)
    if name_prefix:
        query = query.filter(Artifact.name.like(f"{name_prefix}%"))
    if task_id:
        query = query.filter(Artifact.task_id == task_id)

    query = query.order_by(Artifact.created_at.desc())
    if limit:
        query = query.limit(limit)

    artifacts = query.all()
    return StandardResponse(success=True, data=artifacts)


@router.post("/upload", response_model=StandardResponse[ArtifactResponse])
async def upload_artifact(
    project_id: int = Form(...),
    name: Optional[str] = Form(None),
    task_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传并登记产物，供图表导出与词云轮廓图等场景复用。"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    if not file.filename:
        raise HTTPException(status_code=400, detail="上传文件缺少文件名")

    artifact_name = str(name or Path(file.filename).stem or f"artifact_{uuid.uuid4().hex[:8]}").strip()
    suffix = Path(file.filename).suffix or ""
    folder_name = "masks" if "轮廓图" in artifact_name else "manual"
    target_dir = Path(f"storage/projects/{project_id}/artifacts/{folder_name}")
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_file_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = target_dir / stored_file_name
    try:
        with target_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存上传文件失败: {exc}") from exc
    finally:
        await file.close()

    artifact = Artifact(
        project_id=project_id,
        task_id=task_id,
        name=artifact_name,
        type=_infer_type_from_path(file.filename, file.content_type),
        file_path=str(target_path),
        size=int(target_path.stat().st_size),
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return StandardResponse(success=True, data=artifact)


@router.get("/{artifact_id}/preview")
def preview_artifact(artifact_id: int, db: Session = Depends(get_db)):
    """预览产物（inline 展示，不触发下载）。"""
    artifact = _get_artifact_or_404(artifact_id, db)
    download_filename = _build_download_filename(artifact)
    media_type = _build_media_type(artifact, download_filename)
    return FileResponse(
        path=artifact.file_path,
        filename=download_filename,
        media_type=media_type,
        content_disposition_type="inline",
    )


@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: int, db: Session = Depends(get_db)):
    """下载导出产物。"""
    artifact = _get_artifact_or_404(artifact_id, db)
    download_filename = _build_download_filename(artifact)
    media_type = _build_media_type(artifact, download_filename)
    return FileResponse(
        path=artifact.file_path,
        filename=download_filename,
        media_type=media_type,
        content_disposition_type="attachment",
    )


@router.delete("/{artifact_id}", response_model=StandardResponse[str])
def delete_artifact(artifact_id: int, db: Session = Depends(get_db)):
    """删除产物记录及对应文件。"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if os.path.exists(artifact.file_path):
        try:
            os.remove(artifact.file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    db.delete(artifact)
    db.commit()
    return StandardResponse(success=True, data="Artifact deleted successfully")

