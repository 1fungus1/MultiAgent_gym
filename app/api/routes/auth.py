from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Database
from app.core.responses import success
from app.core.security import create_access_token
from app.schemas import ApiResponse, CurrentUser, LoginRequest, LoginResponse
from app.services.auth_service import login_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(
    request: LoginRequest,
    db: Session = Depends(Database),
) -> dict:
    user = login_user(db, request)
    current_user = CurrentUser(
        user_id=user.id,
        username=user.username,
        role=user.role,
        related_id=user.related_id,
    )
    return success(
        LoginResponse(
            token=create_access_token(current_user),
            user_id=user.id,
            username=user.username,
            role=user.role,
            related_id=user.related_id,
        )
    )

