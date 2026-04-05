import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.artifact import Artifact


@pytest.fixture()
def client():
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    db.add_all([
        Artifact(project_id=1, task_id='task-1', name='词云图_alpha', type='png', file_path='a.png', size=1),
        Artifact(project_id=1, task_id='task-2', name='词云图_beta', type='png', file_path='b.png', size=1),
        Artifact(project_id=1, task_id='task-1', name='报告_alpha', type='pdf', file_path='c.pdf', size=1),
        Artifact(project_id=2, task_id='task-1', name='词云图_other', type='png', file_path='d.png', size=1),
    ])
    db.commit()
    db.close()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_list_artifacts_filters_by_type_name_prefix_and_task_id(client: TestClient):
    response = client.get(
        '/api/v1/artifacts/',
        params={
            'project_id': 1,
            'type': 'png',
            'name_prefix': '词云图_',
            'task_id': 'task-1',
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    names = [item['name'] for item in payload['data']]
    assert names == ['词云图_alpha']


def test_list_artifacts_applies_limit(client: TestClient):
    response = client.get(
        '/api/v1/artifacts/',
        params={
            'project_id': 1,
            'type': 'png',
            'name_prefix': '词云图_',
            'limit': 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['success'] is True
    assert len(payload['data']) == 1
