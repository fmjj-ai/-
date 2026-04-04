from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 创建数据库引擎
# check_same_thread=False 允许跨线程共享同一连接（FastAPI中由于多线程处理请求需要这个参数）
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI, 
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    依赖注入：获取数据库 Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
