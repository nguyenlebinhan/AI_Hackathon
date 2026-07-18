from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import RequestMetadata
from app.core.permissions import Permission
from app.database.async_session import get_async_db
from app.dependencies.permissions import require_permission
from app.model.users import User
from app.schemas.user import StaffDirectoryEntry
from app.services.user_service import UserService

router = APIRouter(tags=["Staff directory"])


@router.get("/staff-directory", response_model=list[StaffDirectoryEntry])
async def staff_directory(
    request: Request,
    actor: Annotated[
        User,
        Depends(require_permission(Permission.STAFF_DIRECTORY_READ_PROVINCE)),
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[StaffDirectoryEntry]:
    return await UserService(session).province_directory(
        actor=actor,
        offset=offset,
        limit=limit,
        request=RequestMetadata.from_request(request),
    )

