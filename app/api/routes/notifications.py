from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Database, get_current_user
from app.core.responses import success
from app.schemas import ApiResponse, CurrentUser, NotificationListVO
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("", response_model=ApiResponse[NotificationListVO])
def list_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(Database),
) -> dict:
    return success(notification_service.list_notifications(db, user.user_id, limit))


@router.put("/read-all", response_model=ApiResponse[None])
def mark_all_read(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(Database),
) -> dict:
    notification_service.mark_all_read(db, user.user_id)
    return success()


@router.put("/{notification_id}/read", response_model=ApiResponse[None])
def mark_read(
    notification_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(Database),
) -> dict:
    notification_service.mark_read(db, user.user_id, notification_id)
    return success()

