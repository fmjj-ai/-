from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import shutil
import uuid
import pandas as pd
import hashlib

from app.db.session import get_db
from app.models.project import Project
from app.models.dataset import Dataset, DatasetSnapshot
from app.schemas.dataset import DatasetResponse, DatasetSnapshotResponse
from app.schemas.response import StandardResponse
from app.core.config import settings

router = APIRouter()

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)

def _get_file_hash(file_path: str) -> str:
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def _parse_and_save_dataset(dataset_id: int, file_path: str, ext: str):
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return
        
        try:
            if ext in ['.csv']:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='gbk')
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            elif ext in ['.json']:
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"Unsupported file extension: {ext}")
            
            # Convert to parquet
            parquet_filename = f"{uuid.uuid4().hex}.parquet"
            parquet_path = os.path.join(settings.DATA_DIR, parquet_filename)
            df.to_parquet(parquet_path, engine='pyarrow')
            
            # Build schema
            schema_info = []
            for col, dtype in df.dtypes.items():
                schema_info.append({"name": str(col), "type": str(dtype)})
                
            row_count = len(df)
            col_count = len(df.columns)
            
            # Update dataset
            dataset.status = "ready"
            dataset.file_path = parquet_path
            dataset.row_count = row_count
            dataset.col_count = col_count
            dataset.schema_info = schema_info
            
            # Create initial snapshot (v1)
            file_hash = _get_file_hash(parquet_path)
            snapshot = DatasetSnapshot(
                dataset_id=dataset.id,
                version=1,
                row_count=row_count,
                col_count=col_count,
                schema_info=schema_info,
                file_path=parquet_path,
                file_hash=file_hash
            )
            db.add(snapshot)
            db.commit()
            
        except Exception as e:
            dataset.status = "failed"
            dataset.error_message = str(e)
            db.commit()
    finally:
        db.close()
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload", response_model=StandardResponse[DatasetResponse])
def upload_dataset(
    background_tasks: BackgroundTasks,
    project_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Create dataset record
    dataset = Dataset(
        project_id=project_id,
        name=os.path.splitext(file.filename)[0],
        source_file_name=file.filename,
        status="importing"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    # Save uploaded file temporarily
    ext = os.path.splitext(file.filename)[1].lower()
    temp_filename = f"{uuid.uuid4().hex}{ext}"
    temp_filepath = os.path.join(settings.DATA_DIR, temp_filename)
    
    with open(temp_filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Schedule parsing in background
    background_tasks.add_task(_parse_and_save_dataset, dataset.id, temp_filepath, ext)
    
    return StandardResponse(success=True, data=dataset)

@router.get("/project/{project_id}", response_model=StandardResponse[List[DatasetResponse]])
def get_datasets_by_project(project_id: int, db: Session = Depends(get_db)):
    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).order_by(Dataset.created_at.desc()).all()
    return StandardResponse(success=True, data=datasets)

@router.get("/{dataset_id}", response_model=StandardResponse[DatasetResponse])
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return StandardResponse(success=True, data=dataset)

@router.delete("/{dataset_id}", response_model=StandardResponse[bool])
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # The actual files might need to be cleaned up, here we just cascade delete in DB
    db.delete(dataset)
    db.commit()
    return StandardResponse(success=True, data=True)

@router.post("/{dataset_id}/snapshot", response_model=StandardResponse[DatasetSnapshotResponse])
def create_snapshot(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if dataset.status != "ready":
        raise HTTPException(status_code=400, detail="Dataset is not ready")
        
    # Get max version
    last_snapshot = db.query(DatasetSnapshot).filter(DatasetSnapshot.dataset_id == dataset_id).order_by(DatasetSnapshot.version.desc()).first()
    next_version = (last_snapshot.version + 1) if last_snapshot else 1
    
    # We should copy the parquet file for the new snapshot to make it immutable
    new_filename = f"{uuid.uuid4().hex}.parquet"
    new_filepath = os.path.join(settings.DATA_DIR, new_filename)
    if dataset.file_path and os.path.exists(dataset.file_path):
        shutil.copy2(dataset.file_path, new_filepath)
        file_hash = _get_file_hash(new_filepath)
    else:
        raise HTTPException(status_code=500, detail="Dataset file missing")

    snapshot = DatasetSnapshot(
        dataset_id=dataset.id,
        version=next_version,
        row_count=dataset.row_count,
        col_count=dataset.col_count,
        schema_info=dataset.schema_info,
        file_path=new_filepath,
        file_hash=file_hash
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return StandardResponse(success=True, data=snapshot)

@router.get("/{dataset_id}/snapshots", response_model=StandardResponse[List[DatasetSnapshotResponse]])
def get_dataset_snapshots(dataset_id: int, db: Session = Depends(get_db)):
    snapshots = db.query(DatasetSnapshot).filter(DatasetSnapshot.dataset_id == dataset_id).order_by(DatasetSnapshot.version.desc()).all()
    return StandardResponse(success=True, data=snapshots)

@router.get("/{dataset_id}/data")
def get_dataset_data(
    dataset_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset or data file not found")
        
    df = pd.read_parquet(dataset.file_path)
    # Handle NaN for JSON serialization
    df = df.fillna("")
    total = len(df)
    start = (page - 1) * size
    end = start + size
    
    # We include a _row_index column so the frontend knows the index of each row
    df_slice = df.iloc[start:end].copy()
    df_slice['_row_index'] = df_slice.index
    data = df_slice.to_dict('records')
    
    return StandardResponse(success=True, data={"total": total, "items": data})

@router.put("/{dataset_id}/data")
def update_dataset_data(
    dataset_id: int,
    row_index: int = Body(...),
    updates: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset or data file not found")
        
    df = pd.read_parquet(dataset.file_path)
    if 0 <= row_index < len(df):
        for col, val in updates.items():
            if col in df.columns:
                df.at[row_index, col] = val
        df.to_parquet(dataset.file_path, engine='pyarrow')
        return StandardResponse(success=True, data=True)
    else:
        raise HTTPException(status_code=400, detail="Invalid row index")
