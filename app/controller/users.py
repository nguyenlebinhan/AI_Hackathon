from fastapi import APIRouter

# Authentication and user-management endpoints are intentionally deferred.
router = APIRouter(prefix="/users", tags=["Users"])
