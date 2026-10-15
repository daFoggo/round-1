from fastapi import FastAPI
from app.config import settings
from app.routers import health_router, qa_router

# Khởi tạo FastAPI Application
app = FastAPI(
    title=settings.app_name,
    description="Hệ thống hỏi đáp bảng tính Excel cho cuộc thi AI Tài Năng 2026",
    version="1.0.0"
)

# Đăng ký các router
app.include_router(health_router)
app.include_router(qa_router)
