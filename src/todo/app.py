import time
from datetime import datetime, timezone
from fastapi import FastAPI, Request

from .services.logging import logger
from .api import router


tags_metadata = [
    {
        'name': '/auth',
        'description': 'Авторизация и регистрация'
    },
    {
        'name': '/todos',
        'description': 'Операции с задачами'
    },
]

app = FastAPI(
    title='ToDo Service',
    openapi_tags=tags_metadata,
)

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = datetime.now(timezone.utc)
    request_id = str(time.time_ns())

    try:
        response = await call_next(request)
        process_time = datetime.now(timezone.utc) - start_time

        logger.log({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "status_code": response.status_code,
            "process_time": str(process_time),
        })

        return response

    except Exception as e:
        process_time = datetime.now(timezone.utc) - start_time
        logger.log({
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "status": "error",
            "error": str(e),
            "process_time": str(process_time),
        })
        raise

app.include_router(router)
