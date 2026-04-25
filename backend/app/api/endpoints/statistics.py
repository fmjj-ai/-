import os
import uuid
from typing import Any, Dict, List, Optional

import markdown
import numpy as np
import pandas as pd
import pdfkit
import pyarrow.compute as pc
import pyarrow.parquet as pq
from fastapi import APIRouter, Body, Depends, HTTPException
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.artifact import Artifact
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse

router = APIRouter()

DESCRIPTIVE_FULL_MODE = "full"
DESCRIPTIVE_SUMMARY_MODE = "summary"
DESCRIPTIVE_SUMMARY_MAX_COLUMNS = 10
DESCRIPTIVE_SUMMARY_TOP_VALUES = 5
DESCRIPTIVE_FULL_TOP_VALUES = 10
OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD = 50000
OVERVIEW_UNIQUE_COUNT_DISTINCT_SCAN_TYPES = {
    "string",
    "large_string",
    "binary",
    "large_binary",
}
OVERVIEW_UNIQUE_COUNT_SKIPPED = "skipped_high_cardinality_scan"
DESCRIPTIVE_CATEGORICAL_HIGH_CARDINALITY_ROW_THRESHOLD = OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD


def _get_dataset_or_404(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
    return dataset


def _get_dataset_record_or_404(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return dataset


def _load_parquet_dataframe(file_path: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
    parquet_file = pq.ParquetFile(file_path)
    available_columns = [field.name for field in parquet_file.schema_arrow]
    if columns:
        missing_cols = [column for column in columns if column not in available_columns]
        if missing_cols:
            raise ValueError(f"列不存在: {', '.join(missing_cols)}")
    return pd.read_parquet(file_path, columns=columns)


def _get_parquet_file(file_path: str) -> pq.ParquetFile:
    return pq.ParquetFile(file_path)


def _unwrap_body_default(value: Any) -> Any:
    """兼容直接调用路由函数的测试场景，Body(...) 默认值需要显式展开。"""
    return getattr(value, "default", value)


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

    selected_columns = numeric_columns[:max_columns]
    if len(selected_columns) < max_columns:
        selected_columns.extend(other_columns[: max_columns - len(selected_columns)])
    return selected_columns


def _should_skip_unique_count(field: Any, row_count: int) -> bool:
    return row_count > OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD and str(field.type) in OVERVIEW_UNIQUE_COUNT_DISTINCT_SCAN_TYPES


def _maybe_compute_unique_count(column_data: Any, field: Any, row_count: int) -> Optional[int]:
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
    return any(marker in dtype_name for marker in ("object", "string", "category"))


def _build_categorical_stats(series: pd.Series, mode: str, top_values_limit: int) -> Dict[str, Any]:
    if _should_skip_descriptive_categorical_scan(series, mode):
        return {
            "unique_count": None,
            "unique_count_status": OVERVIEW_UNIQUE_COUNT_SKIPPED,
            "top_values": {},
            "top_values_status": OVERVIEW_UNIQUE_COUNT_SKIPPED,
        }

    value_counts = series.value_counts(dropna=True).head(top_values_limit).to_dict()
    return {
        "unique_count": int(series.nunique(dropna=True)),
        "top_values": {str(key): int(value) for key, value in value_counts.items()},
    }


def _build_numeric_stats(numeric_df: pd.DataFrame) -> Dict[str, Dict[str, Optional[float]]]:
    if numeric_df.empty:
        return {}

    numeric_stats: Dict[str, Dict[str, Optional[float]]] = {}
    for column, metrics in numeric_df.describe().to_dict().items():
        numeric_stats[column] = {key: float(value) if pd.notnull(value) else None for key, value in metrics.items()}
    return numeric_stats


def _build_descriptive_stats_payload(df: pd.DataFrame, mode: str) -> Dict[str, Any]:
    numeric_df = df.select_dtypes(include=[np.number])
    categorical_df = df.select_dtypes(exclude=[np.number])
    top_values_limit = DESCRIPTIVE_SUMMARY_TOP_VALUES if mode == DESCRIPTIVE_SUMMARY_MODE else DESCRIPTIVE_FULL_TOP_VALUES

    payload = {
        "numeric": _build_numeric_stats(numeric_df),
        "categorical": {},
        "meta": {
            "mode": mode,
            "selected_columns": df.columns.tolist(),
            "column_count": int(len(df.columns)),
        },
    }

    for column in categorical_df.columns:
        payload["categorical"][column] = _build_categorical_stats(
            categorical_df[column],
            mode=mode,
            top_values_limit=top_values_limit,
        )

    return payload


def _build_overview(file_path: str) -> Dict[str, Any]:
    parquet_file = _get_parquet_file(file_path)
    metadata = parquet_file.metadata
    schema = parquet_file.schema_arrow
    row_count = metadata.num_rows if metadata else 0

    overview = {
        "row_count": int(row_count),
        "col_count": len(schema),
        "memory_usage_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
        "columns": [],
    }

    for field in schema:
        column_name = field.name
        column_data = parquet_file.read(columns=[column_name]).column(0)
        missing_count = int(column_data.null_count)
        unique_count = _maybe_compute_unique_count(column_data, field, row_count)

        column_overview = {
            "name": str(column_name),
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


def _build_correlation_result(df: pd.DataFrame, method: str) -> Dict[str, Any]:
    sampled_df = df.sample(n=10000, random_state=42) if len(df) > 10000 else df
    numeric_df = _filter_correlation_columns(sampled_df)
    corr_matrix = numeric_df.corr(method=method)
    columns = corr_matrix.columns.tolist()
    data: List[List[Any]] = []

    for row_index, _row_name in enumerate(columns):
        for column_index, _column_name in enumerate(columns):
            value = corr_matrix.iloc[row_index, column_index]
            data.append([row_index, column_index, float(value) if pd.notnull(value) else None])

    return {
        "columns": columns,
        "data": data,
        "method": method,
    }


def _build_regression_model(reg_type: str, poly_degree: int) -> Any:
    if reg_type == "linear":
        return LinearRegression()
    if reg_type == "polynomial":
        return make_pipeline(PolynomialFeatures(poly_degree), LinearRegression())
    raise ValueError(f"不支持的回归类型: {reg_type}")


def _build_fit_line(model: Any, features: np.ndarray) -> List[List[float]] | None:
    if features.shape[1] != 1:
        return None

    x_range = np.linspace(features[:, 0].min(), features[:, 0].max(), 100).reshape(-1, 1)
    y_range_pred = model.predict(x_range)
    return [[float(x_range[index][0]), float(y_range_pred[index])] for index in range(100)]


def _build_regression_result(
    df: pd.DataFrame,
    y_col: str,
    x_cols: List[str],
    reg_type: str,
    poly_degree: int,
    test_size: float,
    random_state: int,
) -> Dict[str, Any]:
    for column in x_cols:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"自变量包含非数值列 ({column})，请先在数据处理中进行编码")

    analysis_df = df[[y_col] + x_cols].dropna()
    features = analysis_df[x_cols].values
    target = analysis_df[y_col].values

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
    )

    model = _build_regression_model(reg_type, poly_degree)
    model.fit(x_train, y_train)
    y_pred = model.predict(x_test)

    return {
        "metrics": {
            "r2": float(r2_score(y_test, y_pred)),
            "mae": float(mean_absolute_error(y_test, y_pred)),
            "mse": float(mean_squared_error(y_test, y_pred)),
        },
        "fit_line": _build_fit_line(model, features),
        "coefficients": model.coef_.tolist() if reg_type == "linear" else None,
        "intercept": float(model.intercept_) if reg_type == "linear" else None,
    }


def _build_histogram_aggregation(series: pd.Series, max_bins: int) -> Dict[str, Any]:
    counts, bins = np.histogram(series.dropna(), bins=min(max_bins, max(series.nunique(), 1)))
    return {
        "x_axis": [f"{bins[index]:.2f}-{bins[index + 1]:.2f}" for index in range(len(bins) - 1)],
        "y_axis": counts.tolist(),
    }


def _build_value_count_aggregation(series: pd.Series, max_bins: int) -> Dict[str, Any]:
    aggregation_df = series.value_counts().head(max_bins).reset_index()
    value_column = "count" if "count" in aggregation_df.columns else aggregation_df.columns[1]
    label_column = aggregation_df.columns[0]
    return {
        "x_axis": aggregation_df[label_column].astype(str).tolist(),
        "y_axis": aggregation_df[value_column].tolist(),
    }


def _build_grouped_aggregation(df: pd.DataFrame, x_col: str, y_col: str, agg_method: str, max_bins: int) -> Dict[str, Any]:
    if not pd.api.types.is_numeric_dtype(df[y_col]):
        raise ValueError("聚合目标列必须是数值型")

    grouped = df.groupby(x_col)[y_col]
    if agg_method == "sum":
        aggregated = grouped.sum()
    elif agg_method == "mean":
        aggregated = grouped.mean()
    elif agg_method == "max":
        aggregated = grouped.max()
    elif agg_method == "min":
        aggregated = grouped.min()
    else:
        aggregated = grouped.count()

    aggregated = aggregated.sort_values(ascending=False).head(max_bins)
    return {
        "x_axis": aggregated.index.astype(str).tolist(),
        "y_axis": aggregated.values.tolist(),
    }


def _build_chart_aggregation_result(
    df: pd.DataFrame,
    x_col: str,
    y_col: Optional[str],
    agg_method: str,
    max_bins: int,
) -> Dict[str, Any]:
    if pd.api.types.is_numeric_dtype(df[x_col]) and not y_col:
        return _build_histogram_aggregation(df[x_col], max_bins)
    if not y_col:
        return _build_value_count_aggregation(df[x_col], max_bins)
    return _build_grouped_aggregation(df, x_col, y_col, agg_method, max_bins)


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


def _build_markdown_report(title: str, content_blocks: List[Dict[str, Any]]) -> str:
    lines = [f"# {title}", ""]
    for block in content_blocks:
        block_type = block.get("type")
        if block_type == "text":
            lines.extend([str(block.get("content", "")), ""])
            continue
        if block_type == "table":
            lines.extend([f"## {block.get('title', '表格')}", ""])
            data = block.get("data", {})
            if isinstance(data, dict):
                lines.extend(["| 属性 | 值 |", "| --- | --- |"])
                for key, value in data.items():
                    lines.append(f"| {key} | {value} |")
            lines.append("")
            continue
        if block_type == "chart":
            lines.extend(
                [
                    f"## {block.get('title', '图表')}",
                    "",
                    f"![{block.get('title', '')}]({block.get('image_url', '')})",
                    "",
                ]
            )
    return "\n".join(lines)


def _build_report_html(md_content: str) -> str:
    html_content = markdown.markdown(md_content, extensions=["tables"])
    return f"""
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
            """


def _serialize_artifact_response(artifact: Artifact, file_path: str, artifact_type: str) -> Dict[str, Any]:
    return {
        "artifact_id": artifact.id,
        "name": artifact.name,
        "file_path": file_path,
        "type": artifact_type,
    }


@router.get("/{dataset_id}/overview", response_model=StandardResponse[Dict[str, Any]])
def get_dataset_overview(dataset_id: int, db: Session = Depends(get_db)):
    """ST-03 自动数据概览"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        return StandardResponse(success=True, data=_build_overview(dataset.file_path))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成概览失败: {str(exc)}") from exc


@router.post("/{dataset_id}/descriptive", response_model=StandardResponse[Dict[str, Any]])
def get_descriptive_stats(
    dataset_id: int,
    columns: Optional[List[str]] = Body(None, embed=True),
    mode: str = Body(DESCRIPTIVE_FULL_MODE, embed=True),
    limit_columns: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db),
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
        return StandardResponse(success=True, data=_build_descriptive_stats_payload(df, mode))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"计算描述性统计失败: {str(exc)}") from exc


@router.post("/{dataset_id}/correlation", response_model=StandardResponse[Dict[str, Any]])
def get_correlation_matrix(
    dataset_id: int,
    columns: Optional[List[str]] = Body(None, embed=True),
    method: str = Body("pearson", embed=True),
    db: Session = Depends(get_db),
):
    """ST-05 相关性矩阵"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        columns = _unwrap_body_default(columns)
        method = _unwrap_body_default(method)
        df = _load_parquet_dataframe(dataset.file_path, columns=columns)
        return StandardResponse(success=True, data=_build_correlation_result(df, method))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"计算相关性矩阵失败: {str(exc)}") from exc


@router.post("/{dataset_id}/regression", response_model=StandardResponse[Dict[str, Any]])
def get_regression_analysis(
    dataset_id: int,
    y_col: str = Body(..., embed=True),
    x_cols: List[str] = Body(..., embed=True),
    reg_type: str = Body("linear", embed=True),
    poly_degree: int = Body(2, embed=True),
    test_size: float = Body(0.2, embed=True),
    random_state: int = Body(42, embed=True),
    db: Session = Depends(get_db),
):
    """ST-06 回归分析"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        required_columns = [y_col] + x_cols
        df = _load_parquet_dataframe(dataset.file_path, columns=required_columns)
        result = _build_regression_result(df, y_col, x_cols, reg_type, poly_degree, test_size, random_state)
        return StandardResponse(success=True, data=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"回归分析失败: {str(exc)}") from exc


@router.post("/{dataset_id}/aggregation", response_model=StandardResponse[Dict[str, Any]])
def get_chart_aggregation(
    dataset_id: int,
    x_col: str = Body(..., embed=True),
    y_col: Optional[str] = Body(None, embed=True),
    agg_method: str = Body("count", embed=True),
    max_bins: int = Body(50, embed=True),
    db: Session = Depends(get_db),
):
    """用于图表渲染的后端聚合逻辑，防止卡顿"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        columns = [x_col] + ([y_col] if y_col else [])
        df = _load_parquet_dataframe(dataset.file_path, columns=columns)
        return StandardResponse(success=True, data=_build_chart_aggregation_result(df, x_col, y_col, agg_method, max_bins))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"聚合计算失败: {str(exc)}") from exc


@router.post("/{dataset_id}/report", response_model=StandardResponse[Dict[str, Any]])
def generate_report(
    dataset_id: int,
    report_type: str = Body("markdown", embed=True),
    title: str = Body("数据分析报告", embed=True),
    content_blocks: List[Dict[str, Any]] = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    dataset = _get_dataset_record_or_404(dataset_id, db)

    try:
        md_content = _build_markdown_report(title, content_blocks)
        artifacts_dir = f"storage/projects/{dataset.project_id}/artifacts/reports"
        os.makedirs(artifacts_dir, exist_ok=True)
        report_id = str(uuid.uuid4())

        if report_type == "markdown":
            file_path = os.path.join(artifacts_dir, f"report_{report_id}.md")
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(md_content)
            artifact = _register_generated_artifact(
                db=db,
                project_id=dataset.project_id,
                name=f"{dataset.name}统计分析报告.md",
                artifact_type="markdown",
                file_path=file_path,
            )
            return StandardResponse(success=True, data=_serialize_artifact_response(artifact, file_path, "markdown"))

        if report_type == "pdf":
            html_doc = _build_report_html(md_content)
            pdf_path = os.path.join(artifacts_dir, f"report_{report_id}.pdf")
            try:
                pdfkit.from_string(
                    html_doc,
                    pdf_path,
                    options={
                        "enable-local-file-access": None,
                        "encoding": "UTF-8",
                    },
                )
                artifact = _register_generated_artifact(
                    db=db,
                    project_id=dataset.project_id,
                    name=f"{dataset.name}统计分析报告.pdf",
                    artifact_type="pdf",
                    file_path=pdf_path,
                )
                return StandardResponse(success=True, data=_serialize_artifact_response(artifact, pdf_path, "pdf"))
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}") from exc

        raise HTTPException(status_code=400, detail="不支持的报告类型")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(exc)}") from exc
