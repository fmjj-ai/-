from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class QuickCleaningService:
    """快速清洗服务，作为 processing 主流程的补充入口。"""

    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return {
            "service": "quick_cleaning",
            "description": "提供缺失值统计与异常值检测/处理等高频清洗能力。",
            "operations": [
                {"key": "missing_stats", "label": "缺失值统计"},
                {"key": "outlier_preview", "label": "异常值预览"},
                {"key": "outlier_handle", "label": "异常值处理"},
            ],
        }

    @staticmethod
    def get_validation_rules() -> List[Dict[str, Any]]:
        return [
            {"field": "dataset_id", "required": True, "type": "integer"},
            {"field": "column", "required": False, "type": "string"},
            {"field": "method", "required": False, "type": "string", "enum": ["iqr", "zscore"]},
            {"field": "strategy", "required": False, "type": "string", "enum": ["clip", "remove", "replace_mean"]},
        ]

    @staticmethod
    def get_missing_stats(df: pd.DataFrame) -> Dict[str, Any]:
        rows = len(df)
        columns = []
        for col in df.columns:
            missing_count = int(df[col].isna().sum())
            columns.append({
                "name": str(col),
                "missing_count": missing_count,
                "total_count": rows,
                "missing_rate": float(missing_count / rows) if rows else 0.0,
            })
        columns.sort(key=lambda item: item["missing_count"], reverse=True)
        return {
            "row_count": rows,
            "column_count": len(df.columns),
            "columns": columns,
        }

    @staticmethod
    def preview_outliers(df: pd.DataFrame, column: str, method: str = "iqr", z_threshold: float = 3.0) -> Dict[str, Any]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            raise ValueError("目标列没有可用于异常值检测的数值数据")
        mask, summary = QuickCleaningService._build_outlier_mask(series, method=method, z_threshold=z_threshold)
        outliers = series[mask]
        return {
            "column": column,
            "method": method,
            "outlier_count": int(outliers.shape[0]),
            "summary": summary,
            "sample_values": outliers.head(20).astype(float).tolist(),
        }

    @staticmethod
    def handle_outliers(
        df: pd.DataFrame,
        column: str,
        method: str = "iqr",
        strategy: str = "clip",
        z_threshold: float = 3.0,
    ) -> Dict[str, Any]:
        series = pd.to_numeric(df[column], errors="coerce")
        valid_series = series.dropna()
        if valid_series.empty:
            raise ValueError("目标列没有可用于异常值处理的数值数据")
        mask, summary = QuickCleaningService._build_outlier_mask(valid_series, method=method, z_threshold=z_threshold)
        outlier_index = valid_series[mask].index
        affected = len(outlier_index)
        if affected == 0:
            return {"affected_rows": 0, "strategy": strategy, "column": column, "summary": summary}

        if strategy == "remove":
            df.drop(index=outlier_index, inplace=True)
        elif strategy == "replace_mean":
            replacement = float(valid_series[~mask].mean()) if (~mask).any() else float(valid_series.mean())
            df.loc[outlier_index, column] = replacement
        else:
            lower = summary.get("lower_bound")
            upper = summary.get("upper_bound")
            if lower is None or upper is None:
                raise ValueError("当前检测方法不支持 clip 策略")
            df[column] = series.clip(lower=lower, upper=upper)

        return {"affected_rows": affected, "strategy": strategy, "column": column, "summary": summary}

    @staticmethod
    def _build_outlier_mask(series: pd.Series, method: str = "iqr", z_threshold: float = 3.0):
        if method == "zscore":
            mean = float(series.mean())
            std = float(series.std())
            if std == 0:
                return pd.Series(False, index=series.index), {
                    "mean": mean,
                    "std": std,
                    "z_threshold": float(z_threshold),
                    "lower_bound": None,
                    "upper_bound": None,
                }
            z_scores = ((series - mean) / std).abs()
            mask = z_scores > float(z_threshold)
            return mask, {
                "mean": mean,
                "std": std,
                "z_threshold": float(z_threshold),
                "lower_bound": None,
                "upper_bound": None,
            }

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        return mask, {
            "q1": q1,
            "q3": q3,
            "iqr": float(iqr),
            "lower_bound": float(lower),
            "upper_bound": float(upper),
        }
