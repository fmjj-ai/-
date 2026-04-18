from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import pyarrow.compute as pc

from app.db.session import get_db
from app.models.artifact import Artifact
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.core.config import settings

router = APIRouter()

DESCRIPTIVE_FULL_MODE = "full"
DESCRIPTIVE_SUMMARY_MODE = "summary"
DESCRIPTIVE_SUMMARY_MAX_COLUMNS = 10
DESCRIPTIVE_SUMMARY_TOP_VALUES = 5
DESCRIPTIVE_FULL_TOP_VALUES = 10
OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD = 50000
OVERVIEW_UNIQUE_COUNT_DISTINCT_SCAN_TYPES = {
    'string',
    'large_string',
    'binary',
    'large_binary',
}
OVERVIEW_UNIQUE_COUNT_SKIPPED = "skipped_high_cardinality_scan"
DESCRIPTIVE_CATEGORICAL_HIGH_CARDINALITY_ROW_THRESHOLD = OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD


def _get_dataset_or_404(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
    return dataset


def _load_parquet_dataframe(file_path: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    parquet_file = pq.ParquetFile(file_path)
    available_columns = [field.name for field in parquet_file.schema_arrow]
    if columns:
        missing_cols = [c for c in columns if c not in available_columns]
        if missing_cols:
            raise ValueError(f"列不存在: {', '.join(missing_cols)}")
    return pd.read_parquet(file_path, columns=columns)


def _get_parquet_file(file_path: str) -> pq.ParquetFile:
    return pq.ParquetFile(file_path)


def _select_descriptive_columns(
    file_path: str,
    requested_columns: Optional[List[str]],
    mode: str,
    limit_columns: Optional[int],
) -> Optional[List[str]]:
    if requested_columns:
        return requested_columns

    if mode != DESCRIPTIVE_SUMMARY_MODE:
        return None

    parquet_file = _get_parquet_file(file_path)
    schema = parquet_file.schema_arrow
    max_columns = limit_columns or DESCRIPTIVE_SUMMARY_MAX_COLUMNS

    numeric_columns: List[str] = []
    other_columns: List[str] = []
    for field in schema:
        if pd.api.types.is_numeric_dtype(field.type.to_pandas_dtype()):
            numeric_columns.append(field.name)
        else:
            other_columns.append(field.name)

    selected = numeric_columns[:max_columns]
    if len(selected) < max_columns:
        selected.extend(other_columns[: max_columns - len(selected)])
    return selected


def _should_skip_unique_count(field, row_count: int) -> bool:
    return row_count > OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD and str(field.type) in OVERVIEW_UNIQUE_COUNT_DISTINCT_SCAN_TYPES


def _unwrap_body_default(value: Any):
    """兼容直接调用路由函数的测试场景，Body(...) 默认值需要显式展开。"""
    return getattr(value, "default", value)


def _maybe_compute_unique_count(column_data, field, row_count: int):
    if not _should_skip_unique_count(field, row_count):
        return int(pc.count_distinct(column_data).as_py())

    sample_size = min(row_count, 2048)
    sample_unique_count = int(pc.count_distinct(column_data.slice(0, sample_size)).as_py())
    if sample_unique_count <= 32:
        return int(pc.count_distinct(column_data).as_py())
    return None


def _should_skip_descriptive_categorical_scan(series: pd.Series, mode: str) -> bool:
    if mode != DESCRIPTIVE_SUMMARY_MODE:
        return False
    if len(series) <= DESCRIPTIVE_CATEGORICAL_HIGH_CARDINALITY_ROW_THRESHOLD:
        return False

    dtype_name = str(series.dtype).lower()
    return any(marker in dtype_name for marker in ('object', 'string', 'category'))


def _build_categorical_stats(series: pd.Series, mode: str, top_values_limit: int) -> Dict[str, Any]:
    if _should_skip_descriptive_categorical_scan(series, mode):
        return {
            "unique_count": None,
            "unique_count_status": OVERVIEW_UNIQUE_COUNT_SKIPPED,
            "top_values": {},
            "top_values_status": OVERVIEW_UNIQUE_COUNT_SKIPPED,
        }

    val_counts = series.value_counts(dropna=True).head(top_values_limit).to_dict()
    return {
        "unique_count": int(series.nunique(dropna=True)),
        "top_values": {str(k): int(v) for k, v in val_counts.items()}
    }


def _build_overview(file_path: str) -> Dict[str, Any]:
    parquet_file = _get_parquet_file(file_path)
    metadata = parquet_file.metadata
    schema = parquet_file.schema_arrow
    row_count = metadata.num_rows if metadata else 0

    overview = {
        "row_count": int(row_count),
        "col_count": len(schema),
        "memory_usage_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
        "columns": []
    }

    for field in schema:
        col_name = field.name
        column_data = parquet_file.read(columns=[col_name]).column(0)
        missing_count = int(column_data.null_count)
        unique_count = _maybe_compute_unique_count(column_data, field, row_count)

        column_overview = {
            "name": str(col_name),
            "type": str(field.type),
            "missing_count": missing_count,
            "missing_rate": float(missing_count / row_count) if row_count else 0.0,
            "unique_count": unique_count,
        }
        if unique_count is None:
            column_overview["unique_count_status"] = OVERVIEW_UNIQUE_COUNT_SKIPPED

        overview["columns"].append(column_overview)

    return overview


def _filter_correlation_columns(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = df.select_dtypes(include=[np.number]).copy()
    if numeric_df.empty:
        raise ValueError("没有数值列可计算相关性")

    valid_columns: List[str] = []
    for column in numeric_df.columns:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        if series.nunique(dropna=True) <= 1:
            continue
        valid_columns.append(column)

    if len(valid_columns) < 2:
        raise ValueError("有效数值列不足 2 个，无法计算相关性热力图")

    return numeric_df[valid_columns]


def _register_generated_artifact(
    db: Session,
    project_id: int,
    name: str,
    artifact_type: str,
    file_path: str,
) -> Artifact:
    artifact = Artifact(
        project_id=project_id,
        task_id=None,
        name=name,
        type=artifact_type,
        file_path=file_path,
        size=int(os.path.getsize(file_path)) if os.path.exists(file_path) else 0,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


@router.get("/{dataset_id}/overview", response_model=StandardResponse[Dict[str, Any]])
def get_dataset_overview(dataset_id: int, db: Session = Depends(get_db)):
    """ST-03 自动数据概览"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        overview = _build_overview(dataset.file_path)
        return StandardResponse(success=True, data=overview)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成概览失败: {str(e)}")


@router.post("/{dataset_id}/descriptive", response_model=StandardResponse[Dict[str, Any]])
def get_descriptive_stats(
    dataset_id: int,
    columns: Optional[List[str]] = Body(None, embed=True),
    mode: str = Body(DESCRIPTIVE_FULL_MODE, embed=True),
    limit_columns: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """ST-04 描述性统计；支持 summary 轻量模式与列限制。"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        columns = _unwrap_body_default(columns)
        mode = _unwrap_body_default(mode)
        limit_columns = _unwrap_body_default(limit_columns)
        if mode not in {DESCRIPTIVE_FULL_MODE, DESCRIPTIVE_SUMMARY_MODE}:
            raise ValueError(f"不支持的描述性统计模式: {mode}")

        selected_columns = _select_descriptive_columns(dataset.file_path, columns, mode, limit_columns)
        df = _load_parquet_dataframe(dataset.file_path, columns=selected_columns)

        numeric_df = df.select_dtypes(include=[np.number])
        categorical_df = df.select_dtypes(exclude=[np.number])
        top_values_limit = DESCRIPTIVE_SUMMARY_TOP_VALUES if mode == DESCRIPTIVE_SUMMARY_MODE else DESCRIPTIVE_FULL_TOP_VALUES

        stats = {
            "numeric": {},
            "categorical": {},
            "meta": {
                "mode": mode,
                "selected_columns": df.columns.tolist(),
                "column_count": int(len(df.columns))
            }
        }

        if not numeric_df.empty:
            desc = numeric_df.describe().to_dict()
            for col, metrics in desc.items():
                stats["numeric"][col] = {k: float(v) if pd.notnull(v) else None for k, v in metrics.items()}

        if not categorical_df.empty:
            for col in categorical_df.columns:
                stats["categorical"][col] = _build_categorical_stats(
                    categorical_df[col],
                    mode=mode,
                    top_values_limit=top_values_limit,
                )

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
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        columns = _unwrap_body_default(columns)
        method = _unwrap_body_default(method)
        df = _load_parquet_dataframe(dataset.file_path, columns=columns)
        if len(df) > 10000:
            df = df.sample(n=10000, random_state=42)

        numeric_df = _filter_correlation_columns(df)

        corr_matrix = numeric_df.corr(method=method)
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"计算相关性矩阵失败: {str(exc)}") from exc

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
    reg_type: str = Body("linear", embed=True),
    poly_degree: int = Body(2, embed=True),
    test_size: float = Body(0.2, embed=True),
    random_state: int = Body(42, embed=True),
    db: Session = Depends(get_db)
):
    """ST-06 回归分析"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        required_columns = [y_col] + x_cols
        df = _load_parquet_dataframe(dataset.file_path, columns=required_columns)

        for col in x_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise ValueError(f"自变量包含非数值列 ({col})，请先在数据处理中进行编码")

        analysis_df = df[required_columns].dropna()
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

        fit_line = None
        if len(x_cols) == 1:
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
    agg_method: str = Body("count", embed=True),
    max_bins: int = Body(50, embed=True),
    db: Session = Depends(get_db)
):
    """用于图表渲染的后端聚合逻辑，防止卡顿"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        columns = [x_col] + ([y_col] if y_col else [])
        df = _load_parquet_dataframe(dataset.file_path, columns=columns)

        result = {"x_axis": [], "y_axis": []}

        if pd.api.types.is_numeric_dtype(df[x_col]) and not y_col:
            counts, bins = np.histogram(df[x_col].dropna(), bins=min(max_bins, max(df[x_col].nunique(), 1)))
            result["x_axis"] = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)]
            result["y_axis"] = counts.tolist()
        else:
            if not y_col:
                agg_df = df[x_col].value_counts().head(max_bins).reset_index()
                value_col = 'count' if 'count' in agg_df.columns else agg_df.columns[1]
                label_col = agg_df.columns[0]
                result["x_axis"] = agg_df[label_col].astype(str).tolist()
                result["y_axis"] = agg_df[value_col].tolist()
            else:
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
                else:
                    agg_res = grouped.count()

                agg_res = agg_res.sort_values(ascending=False).head(max_bins)
                result["x_axis"] = agg_res.index.astype(str).tolist()
                result["y_axis"] = agg_res.values.tolist()

        return StandardResponse(success=True, data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聚合计算失败: {str(e)}")

import markdown
import pdfkit
import uuid

@router.post("/{dataset_id}/report", response_model=StandardResponse[Dict[str, Any]])
def generate_report(
    dataset_id: int,
    report_type: str = Body("markdown", embed=True),
    title: str = Body("数据分析报告", embed=True),
    content_blocks: List[Dict[str, Any]] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")

    try:
        md_content = f"# {title}\n\n"

        for block in content_blocks:
            b_type = block.get("type")
            if b_type == "text":
                md_content += f"{block.get('content', '')}\n\n"
            elif b_type == "table":
                md_content += f"## {block.get('title', '表格')}\n\n"
                data = block.get("data", {})
                if isinstance(data, dict):
                    md_content += "| 属性 | 值 |\n| --- | --- |\n"
                    for k, v in data.items():
                        md_content += f"| {k} | {v} |\n"
                md_content += "\n"
            elif b_type == "chart":
                md_content += f"## {block.get('title', '图表')}\n\n"
                img_url = block.get("image_url", "")
                md_content += f"![{block.get('title', '')}]({img_url})\n\n"

        artifacts_dir = f"storage/projects/{dataset.project_id}/artifacts/reports"
        os.makedirs(artifacts_dir, exist_ok=True)

        report_id = str(uuid.uuid4())

        if report_type == "markdown":
            file_path = os.path.join(artifacts_dir, f"report_{report_id}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            artifact = _register_generated_artifact(
                db=db,
                project_id=dataset.project_id,
                name=f"{dataset.name}统计分析报告.md",
                artifact_type="markdown",
                file_path=file_path,
            )
            return StandardResponse(
                success=True,
                data={
                    "artifact_id": artifact.id,
                    "name": artifact.name,
                    "file_path": file_path,
                    "type": "markdown",
                },
            )

        if report_type == "pdf":
            html_content = markdown.markdown(md_content, extensions=['tables'])
            html_doc = f'''
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: "Microsoft YaHei", "SimHei", sans-serif; padding: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    img {{ max-width: 100%; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            '''

            pdf_path = os.path.join(artifacts_dir, f"report_{report_id}.pdf")
            try:
                options = {
                    'enable-local-file-access': None,
                    'encoding': "UTF-8",
                }
                pdfkit.from_string(html_doc, pdf_path, options=options)
                artifact = _register_generated_artifact(
                    db=db,
                    project_id=dataset.project_id,
                    name=f"{dataset.name}统计分析报告.pdf",
                    artifact_type="pdf",
                    file_path=pdf_path,
                )
                return StandardResponse(
                    success=True,
                    data={
                        "artifact_id": artifact.id,
                        "name": artifact.name,
                        "file_path": pdf_path,
                        "type": "pdf",
                    },
                )

            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}")

        raise HTTPException(status_code=400, detail="不支持的报告类型")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")
