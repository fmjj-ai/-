import mimetypes
import os
from pathlib import Path

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from fastapi.responses import FileResponse

from sqlalchemy.orm import Session



from app.db.session import get_db

from app.models.artifact import Artifact

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

    query = db.query(Artifact).filter(Artifact.project_id == project_id)



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



@router.get("/{artifact_id}/download")

def download_artifact(artifact_id: int, db: Session = Depends(get_db)):

    """下载导出产物"""

    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:

        raise HTTPException(status_code=404, detail="Artifact not found")

        

    if not os.path.exists(artifact.file_path):

        raise HTTPException(status_code=404, detail="File not found on server")

        

    download_filename = _build_download_filename(artifact)
    media_type = _build_media_type(artifact, download_filename)

    return FileResponse(

        path=artifact.file_path,

        filename=download_filename,

        media_type=media_type,

        content_disposition_type="attachment"

    )



@router.delete("/{artifact_id}", response_model=StandardResponse[str])

def delete_artifact(artifact_id: int, db: Session = Depends(get_db)):

    """删除产物记录及对应文件"""

    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()

    if not artifact:

        raise HTTPException(status_code=404, detail="Artifact not found")

        

    # 删除物理文件

    if os.path.exists(artifact.file_path):

        try:

            os.remove(artifact.file_path)

        except Exception as e:

            raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

            

    db.delete(artifact)

    db.commit()

    

    return StandardResponse(success=True, data="Artifact deleted successfully")

