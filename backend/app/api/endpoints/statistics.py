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

@router.get("/{dataset_id}/overview", response_model=StandardResponse[Dict[str, Any]])
def get_dataset_overview(dataset_id: int, db: Session = Depends(get_db)):
    """ST-03 自动数据概览"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        df = pd.read_parquet(dataset.file_path)
        
        # Calculate overview
        overview = {
            "row_count": len(df),
            "col_count": len(df.columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            "columns": []
        }
        
        for col in df.columns:
            col_data = df[col]
            missing_count = col_data.isnull().sum()
            col_info = {
                "name": str(col),
                "type": str(col_data.dtype),
                "missing_count": int(missing_count),
                "missing_rate": float(missing_count / len(df)),
                "unique_count": int(col_data.nunique())
            }
            overview["columns"].append(col_info)
            
        return StandardResponse(success=True, data=overview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成概览失败: {str(e)}")

@router.post("/{dataset_id}/descriptive", response_model=StandardResponse[Dict[str, Any]])
def get_descriptive_stats(
    dataset_id: int,
    columns: Optional[List[str]] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """ST-04 描述性统计"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        df = pd.read_parquet(dataset.file_path)
        if columns:
            missing_cols = [c for c in columns if c not in df.columns]
            if missing_cols:
                raise ValueError(f"列不存在: {', '.join(missing_cols)}")
            df = df[columns]
            
        numeric_df = df.select_dtypes(include=[np.number])
        categorical_df = df.select_dtypes(exclude=[np.number])
        
        stats = {
            "numeric": {},
            "categorical": {}
        }
        
        if not numeric_df.empty:
            desc = numeric_df.describe().to_dict()
            for col, metrics in desc.items():
                stats["numeric"][col] = {k: float(v) if pd.notnull(v) else None for k, v in metrics.items()}
                
        if not categorical_df.empty:
            for col in categorical_df.columns:
                val_counts = categorical_df[col].value_counts().head(10).to_dict()
                stats["categorical"][col] = {
                    "unique_count": int(categorical_df[col].nunique()),
                    "top_values": {str(k): int(v) for k, v in val_counts.items()}
                }
                
        return StandardResponse(success=True, data=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算描述性统计失败: {str(e)}")

@router.post("/{dataset_id}/correlation", response_model=StandardResponse[Dict[str, Any]])
def get_correlation_matrix(
    dataset_id: int,
    columns: Optional[List[str]] = Body(None, embed=True),
    method: str = Body("pearson", embed=True),
    db: Session = Depends(get_db)
):
    """ST-05 相关性矩阵"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        df = pd.read_parquet(dataset.file_path)
        
        # Handle large datasets by sampling
        if len(df) > 10000:
            df = df.sample(n=10000, random_state=42)
            
        if columns:
            missing_cols = [c for c in columns if c not in df.columns]
            if missing_cols:
                raise ValueError(f"列不存在: {', '.join(missing_cols)}")
            df = df[columns]
            
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty:
            raise ValueError("没有数值列可计算相关性")
            
        corr_matrix = numeric_df.corr(method=method)
        # Convert to format suitable for ECharts heatmap
        cols = corr_matrix.columns.tolist()
        data = []
        for i in range(len(cols)):
            for j in range(len(cols)):
                val = corr_matrix.iloc[i, j]
                val = float(val) if pd.notnull(val) else None
                data.append([i, j, val])
                
        result = {
            "columns": cols,
            "data": data,
            "method": method
        }
        return StandardResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算相关性矩阵失败: {str(e)}")

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

@router.post("/{dataset_id}/regression", response_model=StandardResponse[Dict[str, Any]])
def get_regression_analysis(
    dataset_id: int,
    y_col: str = Body(..., embed=True),
    x_cols: List[str] = Body(..., embed=True),
    reg_type: str = Body("linear", embed=True), # linear, polynomial
    poly_degree: int = Body(2, embed=True),
    test_size: float = Body(0.2, embed=True),
    random_state: int = Body(42, embed=True),
    db: Session = Depends(get_db)
):
    """ST-06 回归分析"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        df = pd.read_parquet(dataset.file_path)
        
        missing_cols = [c for c in [y_col] + x_cols if c not in df.columns]
        if missing_cols:
            raise ValueError(f"列不存在: {', '.join(missing_cols)}")
            
        # Check if categorical
        for col in x_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError(f"自变量包含非数值列 ({col})，请先在数据处理中进行编码")
                
        # Drop missing values
        analysis_df = df[[y_col] + x_cols].dropna()
        if len(analysis_df) < len(df):
            # Record dropping of missing values
            pass # Or we can prompt user, but here we drop automatically for simplicity
            
        X = analysis_df[x_cols].values
        y = analysis_df[y_col].values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)
        
        if reg_type == "linear":
            model = LinearRegression()
        elif reg_type == "polynomial":
            model = make_pipeline(PolynomialFeatures(poly_degree), LinearRegression())
        else:
            raise ValueError(f"不支持的回归类型: {reg_type}")
            
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        
        # Prepare fit line data (for 1D X only)
        fit_line = None
        if len(x_cols) == 1:
            x_min, x_max = X[:, 0].min(), X[:, 0].min() + (X[:, 0].max() - X[:, 0].min())
            x_range = np.linspace(X[:, 0].min(), X[:, 0].max(), 100).reshape(-1, 1)
            y_range_pred = model.predict(x_range)
            fit_line = [[float(x_range[i][0]), float(y_range_pred[i])] for i in range(100)]
            
        result = {
            "metrics": {
                "r2": float(r2),
                "mae": float(mae),
                "mse": float(mse)
            },
            "fit_line": fit_line,
            "coefficients": model.coef_.tolist() if reg_type == "linear" else None,
            "intercept": float(model.intercept_) if reg_type == "linear" else None
        }
        return StandardResponse(success=True, data=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回归分析失败: {str(e)}")

@router.post("/{dataset_id}/aggregation", response_model=StandardResponse[Dict[str, Any]])
def get_chart_aggregation(
    dataset_id: int,
    x_col: str = Body(..., embed=True),
    y_col: Optional[str] = Body(None, embed=True),
    agg_method: str = Body("count", embed=True), # count, sum, mean, min, max
    max_bins: int = Body(50, embed=True),
    db: Session = Depends(get_db)
):
    """用于图表渲染的后端聚合逻辑，防止卡顿"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
        
    try:
        df = pd.read_parquet(dataset.file_path)
        
        if x_col not in df.columns:
            raise ValueError(f"列不存在: {x_col}")
        if y_col and y_col not in df.columns:
            raise ValueError(f"列不存在: {y_col}")
            
        result = {"x_axis": [], "y_axis": []}
        
        # If x is numeric and we just want to bin it (like a histogram)
        if pd.api.types.is_numeric_dtype(df[x_col]) and not y_col:
            counts, bins = np.histogram(df[x_col].dropna(), bins=min(max_bins, df[x_col].nunique()))
            result["x_axis"] = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)]
            result["y_axis"] = counts.tolist()
            
        # Group by categorical x
        else:
            if not y_col:
                # Value counts
                agg_df = df[x_col].value_counts().head(max_bins).reset_index()
                result["x_axis"] = agg_df[x_col].astype(str).tolist()
                result["y_axis"] = agg_df["count"].tolist()
            else:
                # Group by x and aggregate y
                if not pd.api.types.is_numeric_dtype(df[y_col]):
                    raise ValueError("聚合目标列必须是数值型")
                    
                grouped = df.groupby(x_col)[y_col]
                if agg_method == "sum":
                    agg_res = grouped.sum()
                elif agg_method == "mean":
                    agg_res = grouped.mean()
                elif agg_method == "max":
                    agg_res = grouped.max()
                elif agg_method == "min":
                    agg_res = grouped.min()
                else: # count
                    agg_res = grouped.count()
                    
                # Sort and take top N
                agg_res = agg_res.sort_values(ascending=False).head(max_bins)
                result["x_axis"] = agg_res.index.astype(str).tolist()
                result["y_axis"] = agg_res.values.tolist()
                
        return StandardResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聚合计算失败: {str(e)}")
