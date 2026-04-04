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

class FileFormatNotSupportedException(AppException):
    def __init__(self, message: str = "文件格式不支持", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(400, "FILE_FORMAT_NOT_SUPPORTED", message, debug_info, "请上传支持的文件格式，如 Excel、CSV 或 JSON")

class EncodingException(AppException):
    def __init__(self, message: str = "文件编码错误", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(400, "ENCODING_ERROR", message, debug_info, "请确保文件使用 UTF-8 编码")

class MissingColumnException(AppException):
    def __init__(self, message: str = "缺失必要的数据列", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(400, "MISSING_COLUMN", message, debug_info, "请检查数据表是否包含所需的所有列")

class DateParseException(AppException):
    def __init__(self, message: str = "日期解析失败", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(400, "DATE_PARSE_ERROR", message, debug_info, "请检查日期列格式是否正确")

class ExternalAPIException(AppException):
    def __init__(self, message: str = "外部 API 调用失败", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(502, "EXTERNAL_API_ERROR", message, debug_info, "请检查 API 鉴权、限流状态或网络连接，然后重试")

class OutOfMemoryException(AppException):
    def __init__(self, message: str = "内存不足", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(500, "OUT_OF_MEMORY", message, debug_info, "数据量过大，请尝试抽样、分块处理或增加系统资源")

class PermissionDeniedException(AppException):
    def __init__(self, message: str = "权限不足", debug_info: Optional[Dict[str, Any]] = None):
        super().__init__(403, "PERMISSION_DENIED", message, debug_info, "您没有执行此操作的权限，请联系管理员")

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
