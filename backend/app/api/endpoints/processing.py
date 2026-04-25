import os
import re
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dataset import Dataset
from app.schemas.response import StandardResponse
from app.services.quick_cleaning_service import QuickCleaningService

router = APIRouter()


def _get_dataset_or_404(dataset_id: int, db: Session) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="数据集或文件不存在")
    return dataset


def _load_dataset_dataframe(dataset: Dataset, columns: List[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(dataset.file_path, columns=columns)


def _save_dataset_dataframe(dataset: Dataset, df: pd.DataFrame, db: Session) -> None:
    df.to_parquet(dataset.file_path, engine="pyarrow")
    _refresh_dataset_metadata(dataset, df)
    db.commit()


def _refresh_dataset_metadata(dataset: Dataset, df: pd.DataFrame) -> None:
    dataset.row_count = len(df)
    dataset.col_count = len(df.columns)
    dataset.schema_info = [{"name": str(col), "type": str(dtype)} for col, dtype in df.dtypes.items()]


def _ensure_column_exists(df: pd.DataFrame, column: str) -> None:
    if column not in df.columns:
        raise ValueError(f"列不存在: {column}")


def _build_encoding_preview(df: pd.DataFrame, column: str, separator: str = ",") -> Dict[str, Any]:
    _ensure_column_exists(df, column)

    series = df[column]
    non_null = series.dropna()
    normalized = non_null.astype(str).str.strip()
    normalized = normalized[normalized != ""]

    top_values_raw = normalized.value_counts().head(12)
    sample_values = normalized.head(10).tolist()
    contains_separator = bool(separator) and normalized.str.contains(re.escape(separator)).any()

    if contains_separator:
        token_counter: Dict[str, int] = {}
        for raw_value in normalized.tolist():
            tokens = [item.strip() for item in raw_value.split(separator) if item.strip()]
            for token in tokens:
                token_counter[token] = token_counter.get(token, 0) + 1

        sorted_tokens = sorted(token_counter.items(), key=lambda item: (-item[1], item[0]))
        recommended_columns = [f"{column}_{token}" for token, _count in sorted_tokens[:12]]
        return {
            "column": column,
            "value_mode": "multi_value",
            "separator": separator,
            "sample_values": sample_values,
            "unique_count": int(normalized.nunique(dropna=True)),
            "top_values": [{"value": str(key), "count": int(value)} for key, value in top_values_raw.items()],
            "recommended_encoding": "multi_hot_encode",
            "recommended_mapping": None,
            "recommended_columns": recommended_columns,
            "encoding_options": [
                {"key": "multi_hot_encode", "label": "多热编码", "description": "生成 0/1 矩阵列"},
                {"key": "one_hot_encode", "label": "独热编码", "description": "将整串值当作单一类别处理"},
            ],
        }

    unique_values = list(dict.fromkeys(normalized.tolist()))[:100]
    recommended_mapping = {str(value): index + 1 for index, value in enumerate(unique_values)}
    return {
        "column": column,
        "value_mode": "single_value",
        "separator": separator,
        "sample_values": sample_values,
        "unique_count": int(normalized.nunique(dropna=True)),
        "top_values": [{"value": str(key), "count": int(value)} for key, value in top_values_raw.items()],
        "recommended_encoding": "ordinal_encode",
        "recommended_mapping": recommended_mapping,
        "recommended_columns": [f"{column}_编码"],
        "encoding_options": [
            {"key": "ordinal_encode", "label": "顺序整数映射", "description": "按映射表转为 1/2/3/4 等整数"},
            {"key": "one_hot_encode", "label": "独热编码", "description": "为每个类别生成单独的 0/1 列"},
        ],
    }


def _fill_missing_values(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    columns = params.get("columns", [])
    method = params.get("method")
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
                df[col] = df[col].fillna(mode_val.iloc[0])
        elif method == "custom":
            df[col] = df[col].fillna(value)

    return df


def _convert_column_type(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    column = params.get("column")
    target_type = params.get("target_type")
    if column not in df.columns:
        return df

    if target_type == "numeric":
        df[column] = pd.to_numeric(df[column], errors="coerce")
    elif target_type == "string":
        df[column] = df[column].astype(str)
    elif target_type == "datetime":
        df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def _normalize_columns(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    columns = params.get("columns", [])
    method = params.get("method", "minmax")

    for col in columns:
        if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
            continue
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

    return df


def _drop_duplicated_output_columns(df: pd.DataFrame, output_columns: List[str]) -> pd.DataFrame:
    duplicated_columns = [name for name in output_columns if name in df.columns]
    if duplicated_columns:
        return df.drop(columns=duplicated_columns)
    return df


def _apply_one_hot_encode(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    columns = params.get("columns", [])
    keep_original = bool(params.get("keep_original", False))
    if not columns:
        return df

    encoded = pd.get_dummies(
        df[columns],
        columns=columns,
        prefix=columns,
        dtype="int8",
    )
    encoded.columns = encoded.columns.astype(str)
    df = _drop_duplicated_output_columns(df, encoded.columns.tolist())
    df = pd.concat([df, encoded], axis=1)
    if not keep_original:
        df = df.drop(columns=columns)
    return df


def _apply_multi_hot_encode(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    column = params.get("column")
    separator = params.get("separator", ",")
    keep_original = bool(params.get("keep_original", False))
    if column not in df.columns:
        return df

    split_series = df[column].fillna("").astype(str).str.split(separator)
    dummies = split_series.str.join("|").str.get_dummies(sep="|")
    dummies = dummies.rename(columns=lambda item: f"{column}_{str(item).strip()}")
    dummies = dummies.loc[:, [name for name in dummies.columns if name != f"{column}_"]]
    dummies = dummies.astype("int8", copy=False)
    df = _drop_duplicated_output_columns(df, dummies.columns.tolist())
    df = pd.concat([df, dummies], axis=1)
    if not keep_original:
        df = df.drop(columns=[column])
    return df


def _build_ordinal_mapping(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, int]:
    mapping = params.get("mapping") or {}
    if mapping:
        return {str(key): int(value) for key, value in mapping.items()}

    column = params.get("column")
    separator = str(params.get("separator", ","))
    preview = _build_encoding_preview(df[[column]], column=column, separator=separator)
    return {str(key): int(value) for key, value in (preview.get("recommended_mapping") or {}).items()}


def _apply_ordinal_encode(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    column = params.get("column")
    keep_original = bool(params.get("keep_original", True))
    encoded_column = str(params.get("encoded_column") or f"{column}_编码").strip()
    _ensure_column_exists(df, column)

    mapping = _build_ordinal_mapping(df, params)
    source_series = df[column]
    mapped_series = source_series.where(source_series.isna(), source_series.astype(str).str.strip()).map(mapping)
    df[encoded_column] = pd.to_numeric(mapped_series, errors="coerce")
    if not keep_original:
        df = df.drop(columns=[column])
    return df


def _apply_processing_operation(df: pd.DataFrame, operation: Dict[str, Any]) -> pd.DataFrame:
    op_type = operation.get("type")
    params = operation.get("params", {})

    if op_type == "dropna":
        subset = params.get("columns")
        return df.dropna(subset=subset) if subset else df.dropna()

    if op_type == "fillna":
        return _fill_missing_values(df, params)

    if op_type == "drop_duplicates":
        subset = params.get("columns")
        return df.drop_duplicates(subset=subset) if subset else df.drop_duplicates()

    if op_type == "rename_columns":
        mapping = params.get("mapping", {})
        return df.rename(columns=mapping) if mapping else df

    if op_type == "type_convert":
        return _convert_column_type(df, params)

    if op_type == "replace_value":
        column = params.get("column")
        if column in df.columns:
            df[column] = df[column].replace(params.get("old_value"), params.get("new_value"))
        return df

    if op_type == "compute_column":
        new_column = params.get("new_column")
        expression = params.get("expression")
        if new_column and expression:
            try:
                df[new_column] = df.eval(expression)
            except Exception as exc:
                raise ValueError(f"列计算失败 '{expression}': {str(exc)}") from exc
        return df

    if op_type == "normalize":
        return _normalize_columns(df, params)

    if op_type == "one_hot_encode":
        return _apply_one_hot_encode(df, params)

    if op_type == "multi_hot_encode":
        return _apply_multi_hot_encode(df, params)

    if op_type == "ordinal_encode":
        return _apply_ordinal_encode(df, params)

    raise ValueError(f"不支持的操作类型: {op_type}")


@router.post("/{dataset_id}/outliers", response_model=StandardResponse[Dict[str, Any]])
def handle_outliers(
    dataset_id: int,
    column: str = Body(..., embed=True),
    method: str = Body("iqr", embed=True),
    strategy: str = Body("clip", embed=True),
    z_threshold: float = Body(3.0, embed=True),
    db: Session = Depends(get_db),
):
    """快速异常值处理，作为现有 processing 主流程的补充入口。"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        df = _load_dataset_dataframe(dataset)
        _ensure_column_exists(df, column)
        result = QuickCleaningService.handle_outliers(
            df,
            column=column,
            method=method,
            strategy=strategy,
            z_threshold=z_threshold,
        )
        _save_dataset_dataframe(dataset, df, db)
        return StandardResponse(success=True, data=result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"异常值处理失败: {str(exc)}") from exc


@router.post("/{dataset_id}/encoding-preview", response_model=StandardResponse[Dict[str, Any]])
def preview_encoding(
    dataset_id: int,
    column: str = Body(..., embed=True),
    separator: str = Body(",", embed=True),
    db: Session = Depends(get_db),
):
    """在真正编码前返回列值样本、建议编码方式和默认映射。"""
    dataset = _get_dataset_or_404(dataset_id, db)
    try:
        df = _load_dataset_dataframe(dataset, columns=[column])
        preview = _build_encoding_preview(df, column=column, separator=separator)
        return StandardResponse(success=True, data=preview)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成编码预览失败: {str(exc)}") from exc


@router.post("/{dataset_id}/process", response_model=StandardResponse[bool])
def process_dataset(
    dataset_id: int,
    operations: List[Dict[str, Any]] = Body(...),
    db: Session = Depends(get_db),
):
    """处理数据集（清洗、变换、编码等），直接修改工作副本。"""
    dataset = _get_dataset_or_404(dataset_id, db)

    try:
        df = _load_dataset_dataframe(dataset)
        for operation in operations:
            df = _apply_processing_operation(df, operation)

        _save_dataset_dataframe(dataset, df, db)
        return StandardResponse(success=True, data=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据处理失败: {str(exc)}") from exc
