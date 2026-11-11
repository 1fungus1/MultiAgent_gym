import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException

logger = logging.getLogger(__name__)


def success(data: Any = None, message: str = "操作成功") -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


def error(code: int, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "data": None}


def json_response(payload: dict[str, Any], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def handle_business_exception(
        _request: Request, exception: BusinessException
    ) -> JSONResponse:
        # 保持原前端约定：业务错误放在响应体 code 中，HTTP 状态仍为 200。
        return json_response(error(exception.code, exception.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        errors = exception.errors()
        message = "参数错误"
        if errors:
            first = errors[0]
            raw_message = str(first.get("msg", "参数错误"))
            message = raw_message.removeprefix("Value error, ")
        return json_response(error(400, message))

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        _request: Request, exception: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exception)
        return json_response(error(500, "服务器内部错误，请稍后重试"))

