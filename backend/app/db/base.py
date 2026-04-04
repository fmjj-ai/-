import re
from typing import Any
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy import Column, Integer, DateTime
from datetime import datetime

class CustomBase:
    """
    自定义 SQLAlchemy Base，包含公共字段和自动表名生成
    """
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 自动将类名（CamelCase）转换为表名（snake_case）
    @declared_attr
    def __tablename__(cls) -> str:
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

Base = declarative_base(cls=CustomBase)
