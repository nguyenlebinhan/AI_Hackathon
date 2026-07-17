from fastapi import APIRouter

# Object keys are deliberately not exposed through public endpoints.
router = APIRouter(tags=["Storage"])
