import os

import pandas as pd
from fastapi import HTTPException

from app.api.endpoints.datasets import get_dataset_data
from app.api.endpoints.statistics import (
    OVERVIEW_UNIQUE_COUNT_SKIPPED,
    OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD,
    get_dataset_overview,
    get_descriptive_stats,
)


class DummyDataset:
    def __init__(self, dataset_id: int, file_path: str):
        self.id = dataset_id
        self.file_path = file_path


class DummyQuery:
    def __init__(self, dataset):
        self.dataset = dataset

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.dataset


class DummyDB:
    def __init__(self, dataset):
        self.dataset = dataset

    def query(self, _model):
        return DummyQuery(self.dataset)


def test_get_dataset_data_returns_paginated_records_with_columns(tmp_path):
    file_path = tmp_path / 'sample.parquet'
    df = pd.DataFrame(
        {
            'name': ['a', 'b', 'c', 'd'],
            'value': [1, 2, 3, 4],
        }
    )
    df.to_parquet(file_path)

    response = get_dataset_data(1, page=2, size=2, db=DummyDB(DummyDataset(1, str(file_path))))

    assert response.success is True
    assert response.data['total'] == 4
    assert response.data['columns'] == ['name', 'value']
    assert len(response.data['items']) == 2
    assert response.data['items'][0]['name'] == 'c'
    assert response.data['items'][0]['_row_index'] == 2


def test_get_dataset_overview_uses_lightweight_metadata_and_column_scans(tmp_path):
    file_path = tmp_path / 'overview.parquet'
    pd.DataFrame(
        {
            'category': ['x', 'y', None],
            'value': [10, 20, 20],
        }
    ).to_parquet(file_path)

    response = get_dataset_overview(1, db=DummyDB(DummyDataset(1, str(file_path))))

    assert response.success is True
    assert response.data['row_count'] == 3
    assert response.data['col_count'] == 2
    assert response.data['memory_usage_mb'] >= 0
    assert {col['name'] for col in response.data['columns']} == {'category', 'value'}

    category_col = next(col for col in response.data['columns'] if col['name'] == 'category')
    assert category_col['missing_count'] == 1
    assert round(category_col['missing_rate'], 4) == round(1 / 3, 4)
    assert category_col['unique_count'] == 2
    assert 'unique_count_status' not in category_col


def test_get_dataset_overview_skips_expensive_unique_count_for_high_cardinality_columns(tmp_path):
    file_path = tmp_path / 'overview_high_cardinality.parquet'
    row_count = OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD + 1
    pd.DataFrame(
        {
            'id_text': [f'id_{idx}' for idx in range(row_count)],
            'bucket': ['group_a'] * row_count,
        }
    ).to_parquet(file_path)

    response = get_dataset_overview(1, db=DummyDB(DummyDataset(1, str(file_path))))

    assert response.success is True
    id_text_col = next(col for col in response.data['columns'] if col['name'] == 'id_text')
    bucket_col = next(col for col in response.data['columns'] if col['name'] == 'bucket')

    assert id_text_col['missing_count'] == 0
    assert id_text_col['unique_count'] is None
    assert id_text_col['unique_count_status'] == OVERVIEW_UNIQUE_COUNT_SKIPPED
    assert bucket_col['unique_count'] == 1
    assert 'unique_count_status' not in bucket_col


def test_get_descriptive_stats_only_reads_requested_columns(tmp_path):
    file_path = tmp_path / 'stats.parquet'
    df = pd.DataFrame(
        {
            'category': ['x', 'y', 'x'],
            'value': [10, 20, 30],
            'other': [1.5, 2.5, 3.5],
        }
    )
    df.to_parquet(file_path)

    response = get_descriptive_stats(
        1,
        columns=['category'],
        db=DummyDB(DummyDataset(1, str(file_path))),
    )

    assert response.success is True
    assert response.data['numeric'] == {}
    assert 'category' in response.data['categorical']
    assert 'other' not in response.data['categorical']
    assert 'value' not in response.data['numeric']


def test_get_descriptive_stats_summary_mode_limits_columns_and_reports_meta(tmp_path):
    file_path = tmp_path / 'stats_summary.parquet'
    pd.DataFrame(
        {
            'num_a': [1, 2, 3],
            'num_b': [4, 5, 6],
            'text_a': ['x', 'y', 'x'],
            'text_b': ['a', 'b', 'c'],
        }
    ).to_parquet(file_path)

    response = get_descriptive_stats(
        1,
        mode='summary',
        limit_columns=2,
        db=DummyDB(DummyDataset(1, str(file_path))),
    )

    assert response.success is True
    assert response.data['meta']['mode'] == 'summary'
    assert response.data['meta']['column_count'] == 2
    assert response.data['meta']['selected_columns'] == ['num_a', 'num_b']
    assert set(response.data['numeric'].keys()) == {'num_a', 'num_b'}
    assert response.data['categorical'] == {}




def test_get_descriptive_stats_summary_mode_skips_expensive_categorical_stats_for_high_cardinality_columns(tmp_path):
    file_path = tmp_path / 'stats_summary_high_cardinality.parquet'
    row_count = OVERVIEW_UNIQUE_COUNT_ROW_THRESHOLD + 1
    pd.DataFrame(
        {
            'id_text': [f'id_{idx}' for idx in range(row_count)],
            'value': list(range(row_count)),
        }
    ).to_parquet(file_path)

    response = get_descriptive_stats(
        1,
        mode='summary',
        columns=['id_text'],
        db=DummyDB(DummyDataset(1, str(file_path))),
    )

    assert response.success is True
    categorical = response.data['categorical']['id_text']
    assert categorical['unique_count'] is None
    assert categorical['top_values'] == {}
    assert categorical['unique_count_status'] == OVERVIEW_UNIQUE_COUNT_SKIPPED
    assert categorical['top_values_status'] == 'skipped_high_cardinality_scan'


def test_get_descriptive_stats_summary_mode_keeps_small_categorical_stats(tmp_path):
    file_path = tmp_path / 'stats_summary_small_categorical.parquet'
    pd.DataFrame(
        {
            'category': ['A', 'B', 'A', None, 'C', 'A'],
        }
    ).to_parquet(file_path)

    response = get_descriptive_stats(
        1,
        mode='summary',
        columns=['category'],
        db=DummyDB(DummyDataset(1, str(file_path))),
    )

    assert response.success is True
    categorical = response.data['categorical']['category']
    assert categorical['unique_count'] == 3
    assert categorical['top_values']['A'] == 3
    assert 'unique_count_status' not in categorical
    assert 'top_values_status' not in categorical
