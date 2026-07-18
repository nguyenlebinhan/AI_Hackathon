from fastapi import APIRouter

from app.api.v1.admin_users import router as admin_users_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.staff_directory import router as staff_directory_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(admin_users_router)
router.include_router(staff_directory_router)
router.include_router(documents_router)
router.include_router(audit_logs_router)
