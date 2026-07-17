from fastapi import APIRouter

from app.model.schemas.base import APIModel

router = APIRouter(tags=["Health"])


class HealthResponse(APIModel):
    status: str
    service: str


@router.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", service="vads-api")
