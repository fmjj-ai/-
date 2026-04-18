import pandas as pd
import pytest
from fastapi import HTTPException

from app.api.endpoints.processing import process_dataset
from app.api.endpoints.statistics import get_correlation_matrix


class DummyDataset:
    def __init__(self, dataset_id: int, file_path: str):
        self.id = dataset_id
        self.file_path = file_path
        self.row_count = 0
        self.col_count = 0
        self.schema_info = []


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

    def commit(self):
        return None

    def rollback(self):
        return None


def test_process_dataset_one_hot_encode_rewrites_existing_columns_as_numeric_flags(tmp_path):
    file_path = tmp_path / 'encoding.parquet'
    pd.DataFrame(
        {
            '性别': ['A.男', 'B.女', 'B.女', None],
            '性别_A.男': [True, False, False, False],
            '性别_B.女': [False, True, True, False],
        }
    ).to_parquet(file_path)

    dataset = DummyDataset(1, str(file_path))
    response = process_dataset(
        1,
        operations=[
            {
                'type': 'one_hot_encode',
                'params': {
                    'columns': ['性别'],
                    'keep_original': True,
                },
            }
        ],
        db=DummyDB(dataset),
    )

    result_df = pd.read_parquet(file_path)

    assert response.success is True
    assert result_df['性别_A.男'].tolist() == [1, 0, 0, 0]
    assert result_df['性别_B.女'].tolist() == [0, 1, 1, 0]
    assert str(result_df['性别_A.男'].dtype).startswith('int')
    assert str(result_df['性别_B.女'].dtype).startswith('int')
    assert result_df.columns.tolist().count('性别_A.男') == 1
    assert result_df.columns.tolist().count('性别_B.女') == 1


def test_get_correlation_matrix_filters_constant_and_all_null_numeric_columns(tmp_path):
    file_path = tmp_path / 'correlation.parquet'
    pd.DataFrame(
        {
            '有效列A': [1, 2, 3, 4],
            '有效列B': [4, 3, 2, 1],
            '常量列': [7, 7, 7, 7],
            '全空列': [None, None, None, None],
        }
    ).to_parquet(file_path)

    response = get_correlation_matrix(1, db=DummyDB(DummyDataset(1, str(file_path))))

    assert response.success is True
    assert response.data['columns'] == ['有效列A', '有效列B']
    assert len(response.data['data']) == 4


def test_get_correlation_matrix_rejects_when_effective_numeric_columns_are_insufficient(tmp_path):
    file_path = tmp_path / 'correlation_insufficient.parquet'
    pd.DataFrame(
        {
            '常量列': [1, 1, 1],
            '全空列': [None, None, None],
            '文本列': ['A', 'B', 'C'],
        }
    ).to_parquet(file_path)

    with pytest.raises(HTTPException) as exc_info:
        get_correlation_matrix(1, db=DummyDB(DummyDataset(1, str(file_path))))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == '有效数值列不足 2 个，无法计算相关性热力图'
