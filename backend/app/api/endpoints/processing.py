import os
import re
from typing import Any, Dict, List

import numpy as np
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


def _refresh_dataset_metadata(dataset: Dataset, df: pd.DataFrame) -> None:
    dataset.row_count = len(df)
    dataset.col_count = len(df.columns)
    dataset.schema_info = [{"name": str(col), "type": str(dtype)} for col, dtype in df.dtypes.items()]


def _build_encoding_preview(df: pd.DataFrame, column: str, separator: str = ",") -> Dict[str, Any]:
    if column not in df.columns:
        raise ValueError(f"列不存在: {column}")

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
        df = pd.read_parquet(dataset.file_path)
        if column not in df.columns:
            raise ValueError(f"列不存在: {column}")
        result = QuickCleaningService.handle_outliers(
            df,
            column=column,
            method=method,
            strategy=strategy,
            z_threshold=z_threshold,
        )
        df.to_parquet(dataset.file_path, engine="pyarrow")
        _refresh_dataset_metadata(dataset, df)
        db.commit()
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
        df = pd.read_parquet(dataset.file_path, columns=[column])
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
        df = pd.read_parquet(dataset.file_path)

        for op in operations:
            op_type = op.get("type")
            params = op.get("params", {})

            if op_type == "dropna":
                subset = params.get("columns")
                df = df.dropna(subset=subset) if subset else df.dropna()

            elif op_type == "fillna":
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

            elif op_type == "drop_duplicates":
                subset = params.get("columns")
                df = df.drop_duplicates(subset=subset) if subset else df.drop_duplicates()

            elif op_type == "rename_columns":
                mapping = params.get("mapping", {})
                if mapping:
                    df = df.rename(columns=mapping)

            elif op_type == "type_convert":
                col = params.get("column")
                target_type = params.get("target_type")
                if col in df.columns:
                    if target_type == "numeric":
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    elif target_type == "string":
                        df[col] = df[col].astype(str)
                    elif target_type == "datetime":
                        df[col] = pd.to_datetime(df[col], errors="coerce")

            elif op_type == "replace_value":
                col = params.get("column")
                old_val = params.get("old_value")
                new_val = params.get("new_value")
                if col in df.columns:
                    df[col] = df[col].replace(old_val, new_val)

            elif op_type == "compute_column":
                new_col = params.get("new_column")
                expression = params.get("expression")
                if new_col and expression:
                    try:
                        df[new_col] = df.eval(expression)
                    except Exception as exc:
                        raise ValueError(f"列计算失败 '{expression}': {str(exc)}") from exc

            elif op_type == "normalize":
                columns = params.get("columns", [])
                method = params.get("method", "minmax")
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

            elif op_type == "one_hot_encode":
                columns = params.get("columns", [])
                keep_original = bool(params.get("keep_original", False))
                if columns:
                    encoded = pd.get_dummies(
                        df[columns],
                        columns=columns,
                        prefix=columns,
                        dtype="int8",
                    )
                    encoded.columns = encoded.columns.astype(str)
                    duplicated_columns = [name for name in encoded.columns if name in df.columns]
                    if duplicated_columns:
                        df = df.drop(columns=duplicated_columns)
                    df = pd.concat([df, encoded], axis=1)
                    if not keep_original:
                        df = df.drop(columns=columns)

            elif op_type == "multi_hot_encode":
                col = params.get("column")
                sep = params.get("separator", ",")
                keep_original = bool(params.get("keep_original", False))
                if col in df.columns:
                    split_series = df[col].fillna("").astype(str).str.split(sep)
                    dummies = split_series.str.join("|").str.get_dummies(sep="|")
                    dummies = dummies.rename(columns=lambda item: f"{col}_{str(item).strip()}")
                    dummies = dummies.loc[:, [name for name in dummies.columns if name != f"{col}_"]]
                    dummies = dummies.astype("int8", copy=False)
                    duplicated_columns = [name for name in dummies.columns if name in df.columns]
                    if duplicated_columns:
                        df = df.drop(columns=duplicated_columns)
                    df = pd.concat([df, dummies], axis=1)
                    if not keep_original:
                        df = df.drop(columns=[col])

            elif op_type == "ordinal_encode":
                col = params.get("column")
                keep_original = bool(params.get("keep_original", True))
                encoded_column = str(params.get("encoded_column") or f"{col}_编码").strip()
                mapping = params.get("mapping") or {}
                if col not in df.columns:
                    raise ValueError(f"列不存在: {col}")

                if not mapping:
                    preview = _build_encoding_preview(df[[col]], column=col, separator=str(params.get("separator", ",")))
                    mapping = preview.get("recommended_mapping") or {}

                normalized_mapping = {str(key): int(value) for key, value in mapping.items()}
                source_series = df[col]
                mapped_series = source_series.where(source_series.isna(), source_series.astype(str).str.strip()).map(normalized_mapping)
                df[encoded_column] = pd.to_numeric(mapped_series, errors="coerce")
                if not keep_original:
                    df = df.drop(columns=[col])

            else:
                raise ValueError(f"不支持的操作类型: {op_type}")

        df.to_parquet(dataset.file_path, engine="pyarrow")
        _refresh_dataset_metadata(dataset, df)
        db.commit()
        return StandardResponse(success=True, data=True)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据处理失败: {str(exc)}") from exc
