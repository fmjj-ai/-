import pandas as pd
import pytest

from app.workers.sentiment_worker import build_sentiment_signature, run_sentiment_task


def _progress(_value: float, _message: str) -> None:
    return None


def test_build_sentiment_signature_is_stable_for_equivalent_stopwords_order():
    left = build_sentiment_signature(
        dataset_fingerprint='abc',
        config={
            'text_column': 'content',
            'method': 'snownlp',
            'stopwords': ['的', '了', '的'],
            'extract_tfidf': True,
            'top_k': 20,
        },
    )
    right = build_sentiment_signature(
        dataset_fingerprint='abc',
        config={
            'text_column': 'content',
            'method': 'snownlp',
            'stopwords': ['了', '的'],
            'extract_tfidf': True,
            'top_k': 20,
        },
    )

    assert left == right


def test_run_sentiment_task_returns_signature_and_result_summary(tmp_path):
    df = pd.DataFrame({'content': ['很好', '一般', '很差']})
    file_path = tmp_path / 'dataset.parquet'
    df.to_parquet(file_path)

    result = run_sentiment_task(
        dataset_id=1,
        file_path=str(file_path),
        config={
            'text_column': 'content',
            'method': 'snownlp',
            'extract_tfidf': False,
            'generate_wordcloud': False,
        },
        project_id=1,
        update_progress=_progress,
    )

    assert result['signature']
    assert result['dataset_id'] == 1
    assert result['row_count'] == 3
    assert result['text_column'] == 'content'


def test_run_sentiment_task_rejects_deepseek_without_api_key(tmp_path):
    df = pd.DataFrame({'content': ['很好', '很差']})
    file_path = tmp_path / 'dataset.parquet'
    df.to_parquet(file_path)

    with pytest.raises(ValueError, match='API Key'):
        run_sentiment_task(
            dataset_id=1,
            file_path=str(file_path),
            config={
                'text_column': 'content',
                'method': 'deepseek',
                'extract_tfidf': False,
                'generate_wordcloud': False,
            },
            project_id=1,
            update_progress=_progress,
        )
