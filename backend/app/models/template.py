from sqlalchemy import Column, String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.db.base import Base

class Template(Base):
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False, index=True)  # 清洗模板, 图表模板, 统计分析模板, 建模模板, 导出模板
    content = Column(JSON, nullable=False)
    project_id = Column(Integer, ForeignKey("project.id"), nullable=True, index=True)

    project = relationship("Project", backref="templates")
