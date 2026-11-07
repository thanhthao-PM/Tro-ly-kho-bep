"""
Root API v1 Router: Gom toàn bộ các routers con theo Revision 6.3.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.inventory import router as inventory_router
from app.api.v1.endpoints.sales import router as sales_router
from app.api.v1.endpoints.disposals import router as disposals_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.menu import router as menu_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.assistant import router as assistant_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(inventory_router)
api_router.include_router(sales_router)
api_router.include_router(disposals_router)
api_router.include_router(documents_router)
api_router.include_router(menu_router)
api_router.include_router(reports_router)
api_router.include_router(assistant_router)
