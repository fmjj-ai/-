import os
import tempfile

import pandas as pd
import pytest

from app.workers.sentiment_worker import _resolve_wordcloud_font_path, run_sentiment_task


def _progress(_value: float, _message: str) -> None:
    return None


def test_resolve_wordcloud_font_path_prefers_existing_explicit_path(tmp_path):
    font_file = tmp_path / "fake-font.ttf"
    font_file.write_bytes(b"font")

    resolved = _resolve_wordcloud_font_path({"wc_font_path": str(font_file), "wc_font": "SimHei"})

    assert resolved == str(font_file)


def test_run_sentiment_task_skips_lda_when_effective_texts_too_few(tmp_path):
    df = pd.DataFrame({"content": ["", "的 了", "测试 文本"]})
    file_path = tmp_path / "dataset.parquet"
    df.to_parquet(file_path)

    result = run_sentiment_task(
        dataset_id=1,
        file_path=str(file_path),
        config={
            "text_column": "content",
            "method": "snownlp",
            "stopwords": ["的", "了"],
            "extract_tfidf": False,
            "run_lda": True,
            "lda_k": 5,
            "generate_wordcloud": False,
        },
        project_id=1,
        update_progress=_progress,
    )

    assert result["lda"] is None

    saved = pd.read_parquet(file_path)
    assert "sentiment_score" in saved.columns
    assert "sentiment_label" in saved.columns


def test_run_sentiment_task_rejects_deepseek_without_api_key(tmp_path):
    df = pd.DataFrame({"content": ["很好", "很差"]})
    file_path = tmp_path / "dataset.parquet"
    df.to_parquet(file_path)

    with pytest.raises(ValueError, match="API Key"):
        run_sentiment_task(
            dataset_id=1,
            file_path=str(file_path),
            config={
                "text_column": "content",
                "method": "deepseek",
                "extract_tfidf": False,
                "generate_wordcloud": False,
            },
            project_id=1,
            update_progress=_progress,
        )
