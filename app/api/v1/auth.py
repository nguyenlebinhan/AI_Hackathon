from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.audit import RequestMetadata
from app.database.async_session import get_async_db
from app.dependencies.auth import (
    AuthContext,
    get_auth_context,
    get_current_active_user,
)
from app.model.users import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenPairResponse,
)
from app.schemas.user import UserPublic
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    return await AuthService(session, settings).login(
        payload,
        request=RequestMetadata.from_request(request),
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    return await AuthService(session, settings).refresh(
        payload,
        request=RequestMetadata.from_request(request),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    await AuthService(session, settings).logout(
        actor=context.user,
        auth_session=context.auth_session,
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    request: Request,
    actor: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    await AuthService(session, settings).logout_all(
        actor=actor,
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    actor: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    await AuthService(session, settings).change_password(
        payload,
        actor=actor,
        request=RequestMetadata.from_request(request),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserPublic)
async def me(
    actor: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    return UserPublic.model_validate(actor)

