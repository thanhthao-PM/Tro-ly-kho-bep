"""
FastAPI Application Entry Point.
Hệ thống Trợ lý kho bếp (AI Kitchen Inventory Assistant).
"""
import uuid
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống quản lý kho bếp, kiểm soát giá vốn FEFO, xử lý hàng cận date và gợi ý bổ sung hàng thông minh.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

cors_origins = list(settings.CORS_ORIGINS)
if settings.APP_ENV != "production":
    cors_origins.extend(("http://localhost:3001", "http://127.0.0.1:3001"))
cors_origins = list(dict.fromkeys(cors_origins))

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Idempotent-Replay"]
)


# Middleware gắn Request ID
@app.middleware("http")
async def add_request_id_and_timing(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Handler bắt lỗi validation của Pydantic
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dữ liệu gửi lên không đúng định dạng yêu cầu.",
                "details": exc.errors(),
                "request_id": request_id
            }
        }
    )


# Mount API v1 Routers
from app.api.v1.router import api_router
app.include_router(api_router)


# Health check endpoint (H1)
@app.get("/health", tags=["Health"], summary="Liveness check")
@app.get("/api/v1/health", tags=["Health"], summary="API v1 liveness check")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timezone": settings.TIMEZONE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
