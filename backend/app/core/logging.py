import logging
import sys
from .config import settings

def setup_logging():
    """
    配置全局日志格式与级别
    """
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 针对部分第三方库可能需要调整日志级别以减少噪音
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# 获取默认 logger 的快捷方式
logger = logging.getLogger(settings.PROJECT_NAME)
