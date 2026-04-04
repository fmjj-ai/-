from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

DataT = TypeVar("DataT")

class ErrorDetail(BaseModel):
    error_code: str
    message: str
    debug_info: Optional[dict[str, Any]] = None
    suggestion: Optional[str] = None

class StandardResponse(BaseModel, Generic[DataT]):
    success: bool
    data: Optional[DataT] = None
    error: Optional[ErrorDetail] = None
