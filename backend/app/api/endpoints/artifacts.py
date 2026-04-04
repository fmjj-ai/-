import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.artifact import Artifact
from app.schemas.artifact import ArtifactResponse
from app.schemas.response import StandardResponse

router = APIRouter()

@router.get("/", response_model=StandardResponse[List[ArtifactResponse]])
def list_artifacts(project_id: int, db: Session = Depends(get_db)):
    """列出项目下所有的产物（导出中心）"""
    artifacts = db.query(Artifact).filter(Artifact.project_id == project_id).order_by(Artifact.created_at.desc()).all()
    return StandardResponse(success=True, data=artifacts)

@router.get("/{artifact_id}/download")
def download_artifact(artifact_id: int, db: Session = Depends(get_db)):
    """下载导出产物"""
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
        
    if not os.path.exists(artifact.file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    # 根据 type 设置 MIME 或者仅仅使用 FileResponse 默认
    return FileResponse(
        path=artifact.file_path, 
        filename=artifact.name,
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
