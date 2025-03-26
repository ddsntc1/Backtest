from fastapi import FastAPI, Request
from routes import backtest
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import traceback

app = FastAPI(title = "트리플더블 과제테스트")

app.include_router(backtest.router)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "요청 파라미터가 유효하지 않습니다.",
            "detail": exc.errors(),
            "code": 422,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # 서버 에러 로그 찍기
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "서버 내부 오류가 발생했습니다.",
            "code": 500,
            "path": request.url.path
        }
    )