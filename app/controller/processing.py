from fastapi import APIRouter

# Public status polling is exposed from controller/documents.py to preserve the
# required /api/documents/{documentId}/status contract.
router = APIRouter(tags=["Processing"])
