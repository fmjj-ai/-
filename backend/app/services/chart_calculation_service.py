from __future__ import annotations

from typing import Any, Dict, List, Optional

import jieba
import numpy as np
import pandas as pd


class ChartCalculationService:
    """图表专用计算服务，作为 statistics 的补充能力存在。"""

    DEFAULT_STOPWORDS = {
        "的", "了", "和", "是", "就", "都", "而", "及", "与", "着", "或", "一个", "没有", "我们", "你们", "他们",
        "她们", "是否", "进行", "可以", "这个", "那个", "以及", "因为", "所以", "如果", "但是", "并且", "然后",
    }

    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return {
            "service": "chart_calculations",
            "description": "提供直方图、箱线图、词云与聚合图表的专用计算接口。",
            "charts": [
                {"key": "histogram", "label": "直方图", "required_fields": ["column"]},
                {"key": "boxplot", "label": "箱线图", "required_fields": ["column"]},
                {"key": "aggregation", "label": "聚合图表", "required_fields": ["group_by"]},
                {"key": "wordcloud", "label": "词云词频", "required_fields": ["text_column"]},
            ],
        }

    @staticmethod
    def get_response_contract() -> List[Dict[str, Any]]:
        return [
            {"field": "chart_type", "type": "string"},
            {"field": "dataset_id", "type": "integer"},
            {"field": "payload", "type": "object"},
        ]

    @staticmethod
    def compute_histogram(df: pd.DataFrame, column: str, bins: int = 20) -> Dict[str, Any]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            raise ValueError("目标列没有可用于直方图的数值数据")
        bins = max(1, min(int(bins), max(1, series.nunique())))
        counts, edges = np.histogram(series, bins=bins)
        labels = [f"{edges[i]:.4g}-{edges[i + 1]:.4g}" for i in range(len(edges) - 1)]
        return {
            "labels": labels,
            "counts": counts.astype(int).tolist(),
            "summary": {
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
            },
        }

    @staticmethod
    def compute_boxplot(df: pd.DataFrame, column: str) -> Dict[str, Any]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            raise ValueError("目标列没有可用于箱线图的数值数据")
        q1 = float(series.quantile(0.25))
        median = float(series.quantile(0.5))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        whisker_low = float(series[series >= lower].min()) if not series[series >= lower].empty else float(series.min())
        whisker_high = float(series[series <= upper].max()) if not series[series <= upper].empty else float(series.max())
        outliers = series[(series < lower) | (series > upper)]
        return {
            "box": [whisker_low, q1, median, q3, whisker_high],
            "outliers": outliers.astype(float).tolist(),
            "summary": {
                "count": int(series.shape[0]),
                "iqr": float(iqr),
                "outlier_count": int(outliers.shape[0]),
            },
        }

    @classmethod
    def compute_wordcloud(
        cls,
        df: pd.DataFrame,
        text_column: str,
        top_n: int = 80,
        stopwords: Optional[List[str]] = None,
        min_length: int = 2,
    ) -> Dict[str, Any]:
        text_series = df[text_column].dropna().astype(str)
        if text_series.empty:
            raise ValueError("目标列没有可用于词云的文本数据")
        stopword_set = set(stopwords or []) | cls.DEFAULT_STOPWORDS
        joined_text = "\n".join(text_series.tolist())
        token_counts: Dict[str, int] = {}
        for token in jieba.lcut(joined_text):
            token = token.strip()
            if len(token) < int(min_length) or token in stopword_set:
                continue
            token_counts[token] = token_counts.get(token, 0) + 1
        words = sorted(token_counts.items(), key=lambda item: item[1], reverse=True)[: max(1, int(top_n))]
        return {
            "words": [{"name": word, "value": count} for word, count in words],
            "token_count": int(sum(token_counts.values())),
            "unique_tokens": int(len(token_counts)),
        }

    @staticmethod
    def compute_aggregation(
        df: pd.DataFrame,
        group_by: str,
        metric: Optional[str] = None,
        agg_method: str = "count",
        top_n: int = 50,
    ) -> Dict[str, Any]:
        if group_by not in df.columns:
            raise ValueError(f"列不存在: {group_by}")
        top_n = max(1, int(top_n))
        if metric:
            if metric not in df.columns:
                raise ValueError(f"列不存在: {metric}")
            if agg_method != "count" and not pd.api.types.is_numeric_dtype(df[metric]):
                raise ValueError("聚合指标列必须是数值型")
            grouped = df.groupby(group_by)[metric]
            if agg_method == "sum":
                result = grouped.sum()
            elif agg_method == "mean":
                result = grouped.mean()
            elif agg_method == "max":
                result = grouped.max()
            elif agg_method == "min":
                result = grouped.min()
            else:
                result = grouped.count()
        else:
            result = df[group_by].value_counts()
        result = result.sort_values(ascending=False).head(top_n)
        return {
            "labels": result.index.astype(str).tolist(),
            "values": [float(v) if isinstance(v, (float, np.floating)) else int(v) for v in result.tolist()],
            "agg_method": agg_method,
            "metric": metric,
        }
