from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os
import pandas as pd
import numpy as np

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.core.config import settings

router = APIRouter()

@router.post("/{dataset_id}/process", response_model=StandardResponse[bool])
def process_dataset(
    dataset_id: int,
    operations: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db)
):
    """
    处理数据集（清洗、变换、编码等），直接修改工作副本
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        # Load dataset
        df = pd.read_parquet(dataset.file_path)
        
        # Apply operations sequentially
        for op in operations:
            op_type = op.get("type")
            params = op.get("params", {})
            
            # ST-01 数据清洗
            if op_type == "dropna":
                subset = params.get("columns")
                if subset:
                    df = df.dropna(subset=subset)
                else:
                    df = df.dropna()
            
            elif op_type == "fillna":
                columns = params.get("columns", [])
                method = params.get("method") # mean, median, mode, custom
                value = params.get("value")
                
                for col in columns:
                    if col not in df.columns:
                        continue
                    if method == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].mean())
                    elif method == "median" and pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].fillna(df[col].median())
                    elif method == "mode":
                        mode_val = df[col].mode()
                        if not mode_val.empty:
                            df[col] = df[col].fillna(mode_val[0])
                    elif method == "custom":
                        df[col] = df[col].fillna(value)
            
            elif op_type == "drop_duplicates":
                subset = params.get("columns")
                if subset:
                    df = df.drop_duplicates(subset=subset)
                else:
                    df = df.drop_duplicates()
                    
            elif op_type == "rename_columns":
                mapping = params.get("mapping", {})
                if mapping:
                    df = df.rename(columns=mapping)
                    
            elif op_type == "type_convert":
                col = params.get("column")
                target_type = params.get("target_type")
                if col in df.columns:
                    if target_type == "numeric":
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    elif target_type == "string":
                        df[col] = df[col].astype(str)
                    elif target_type == "datetime":
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        
            elif op_type == "replace_value":
                col = params.get("column")
                old_val = params.get("old_value")
                new_val = params.get("new_value")
                if col in df.columns:
                    df[col] = df[col].replace(old_val, new_val)
                    
            # ST-02 数据变换
            elif op_type == "compute_column":
                new_col = params.get("new_column")
                expression = params.get("expression")
                if new_col and expression:
                    try:
                        df[new_col] = df.eval(expression)
                    except Exception as e:
                        raise ValueError(f"列计算失败 '{expression}': {str(e)}")
                        
            elif op_type == "normalize":
                columns = params.get("columns", [])
                method = params.get("method", "minmax") # minmax, zscore
                for col in columns:
                    if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                        if method == "minmax":
                            min_val = df[col].min()
                            max_val = df[col].max()
                            if max_val != min_val:
                                df[col] = (df[col] - min_val) / (max_val - min_val)
                        elif method == "zscore":
                            mean_val = df[col].mean()
                            std_val = df[col].std()
                            if std_val != 0:
                                df[col] = (df[col] - mean_val) / std_val
                                
            # PR-02 独热编码
            elif op_type == "one_hot_encode":
                columns = params.get("columns", [])
                keep_original = params.get("keep_original", False)
                if columns:
                    encoded = pd.get_dummies(df[columns], columns=columns, prefix=columns)
                    # For json serialization safety, ensure column names are strings
                    encoded.columns = encoded.columns.astype(str)
                    df = pd.concat([df, encoded], axis=1)
                    if not keep_original:
                        df = df.drop(columns=columns)
                        
            # PR-03 多热编码 (Multi-hot)
            elif op_type == "multi_hot_encode":
                col = params.get("column")
                sep = params.get("separator", ",")
                keep_original = params.get("keep_original", False)
                if col in df.columns:
                    # Drop NA and convert to string
                    s = df[col].fillna("").astype(str)
                    # Split by separator
                    s = s.str.split(sep)
                    # Use explode and get_dummies
                    # Wait, an easier way is Series.str.get_dummies
                    dummies = s.str.join('|').str.get_dummies(sep='|')
                    dummies = dummies.add_prefix(f"{col}_")
                    df = pd.concat([df, dummies], axis=1)
                    if not keep_original:
                        df = df.drop(columns=[col])
                        
            else:
                raise ValueError(f"不支持的操作类型: {op_type}")
                
        # Save updated dataframe
        df.to_parquet(dataset.file_path, engine='pyarrow')
        
        # Update metadata
        schema_info = []
        for col, dtype in df.dtypes.items():
            schema_info.append({"name": str(col), "type": str(dtype)})
            
        dataset.row_count = len(df)
        dataset.col_count = len(df.columns)
        dataset.schema_info = schema_info
        
        db.commit()
        return StandardResponse(success=True, data=True)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据处理失败: {str(e)}")
