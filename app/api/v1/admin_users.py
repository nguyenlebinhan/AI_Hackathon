from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import RequestMetadata
from app.core.permissions import Permission
from app.database.async_session import get_async_db
from app.dependencies.permissions import require_permission
from app.model.users import User
from app.schemas.user import (
    AdminResetPasswordRequest,
    AdminUserCreateRequest,
    UserPublic,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/admin/users", tags=["Admin users"])


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_permission(Permission.USERS_CREATE))],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> UserPublic:
    user = await UserService(session).create_user(
        payload,
        actor=actor,
        request=RequestMetadata.from_request(request),
    )
    return UserPublic.model_validate(user)


@router.get("", response_model=list[UserPublic])
async def list_users(
    actor: Annotated[
        User, Depends(require_permission(Permission.USERS_READ_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[UserPublic]:
    users = await UserService(session).list_commune_users(
        actor=actor,
        offset=offset,
        limit=limit,
    )
    return [UserPublic.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: Annotated[str, Path(min_length=1, max_length=40)],
    actor: Annotated[
        User, Depends(require_permission(Permission.USERS_READ_COMMUNE))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> UserPublic:
    user = await UserService(session).get_commune_user(
        actor=actor,
        target_user_id=user_id,
    )
    return UserPublic.model_validate(user)


@router.patch("/{user_id}/lock", response_model=UserPublic)
async def lock_user(
    user_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.USERS_UPDATE_STATUS))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> UserPublic:
    user = await UserService(session).lock_user(
        actor=actor,
        target_user_id=user_id,
        request=RequestMetadata.from_request(request),
    )
    return UserPublic.model_validate(user)


@router.patch("/{user_id}/unlock", response_model=UserPublic)
async def unlock_user(
    user_id: Annotated[str, Path(min_length=1, max_length=40)],
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.USERS_UPDATE_STATUS))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> UserPublic:
    user = await UserService(session).unlock_user(
        actor=actor,
        target_user_id=user_id,
        request=RequestMetadata.from_request(request),
    )
    return UserPublic.model_validate(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: Annotated[str, Path(min_length=1, max_length=40)],
    payload: AdminResetPasswordRequest,
    request: Request,
    actor: Annotated[
        User, Depends(require_permission(Permission.USERS_RESET_PASSWORD))
    ],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> Response:
    await UserService(session).reset_password(
        actor=actor,
        target_user_id=user_id,
        temporary_password=payload.temporary_password.get_secret_value(),
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

