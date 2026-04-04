from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    """
    基础业务异常类
    包含 HTTP 状态码、错误码、提示信息、调试信息及建议
    """
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        debug_info: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.debug_info = debug_info or {}
        self.suggestion = suggestion

class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(404, "NOT_FOUND", message, debug_info, "请检查资源标识是否正确")

class ValidationException(AppException):
    def __init__(self, message: str = "参数校验失败", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(400, "VALIDATION_ERROR", message, debug_info, "请检查输入参数是否符合要求")

class BusinessException(AppException):
    def __init__(self, error_code: str, message: str, debug_info: Optional[Dict[str, Any]] = None, suggestion: Optional[str] = None):
        super().__init__(400, error_code, message, debug_info, suggestion)

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    全局业务异常处理函数，转换为标准 JSON 错误结构
    """
    error_content = {
        "success": False,
        "error": {
            "error_code": exc.error_code,
            "message": exc.message,
            "debug_info": exc.debug_info,
            "suggestion": exc.suggestion
        }
    }
    return JSONResponse(status_code=exc.status_code, content=error_content)

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    捕获未处理的全局异常
    """
    error_content = {
        "success": False,
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "debug_info": {"detail": str(exc)},
            "suggestion": "请联系系统管理员或稍后重试"
        }
    }
    return JSONResponse(status_code=500, content=error_content)
