from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Database, require_member
from app.core.responses import success
from app.schemas import (
    ApiResponse,
    AppointmentVO,
    CheckinRequest,
    CheckinVO,
    CourseVO,
    CurrentUser,
    MemberVO,
    PasswordRequest,
    ProfileUpdate,
    ReserveRequest,
)
from app.services import appointment_service, attendance_service, course_service, member_service

router = APIRouter(prefix="/member", tags=["会员"])
profile_router = APIRouter(prefix="/profile")
course_router = APIRouter(prefix="/courses")
appointment_router = APIRouter(prefix="/appointments")


@profile_router.get("", response_model=ApiResponse[MemberVO])
def get_profile(
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    return success(member_service.get_profile(db, user.related_id))


@profile_router.put("", response_model=ApiResponse[None])
def update_profile(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    member_service.update_profile(db, user.related_id, payload)
    return success()


@profile_router.put("/password", response_model=ApiResponse[None])
def update_password(
    payload: PasswordRequest,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    member_service.update_password(db, user.user_id, payload)
    return success()


@course_router.get("", response_model=ApiResponse[list[CourseVO]])
def member_courses(db: Session = Depends(Database)) -> dict:
    return success(course_service.member_course_options(db))


@appointment_router.get("", response_model=ApiResponse[list[AppointmentVO]])
def member_appointments(
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    return success(appointment_service.list_member_appointments(db, user.related_id))


@appointment_router.post("", response_model=ApiResponse[None])
def reserve_course(
    request: ReserveRequest,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    appointment_service.reserve(db, user.related_id, request.course_id)
    return success()


@appointment_router.post("/waitlist", response_model=ApiResponse[None])
def join_waitlist(
    request: ReserveRequest,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    appointment_service.join_waitlist(db, user.related_id, request.course_id)
    return success()


@appointment_router.post("/check-in", response_model=ApiResponse[CheckinVO])
def check_in(
    request: CheckinRequest,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    return success(attendance_service.check_in(db, user.related_id, request.token))


@appointment_router.post(
    "/{appointment_id}/confirm-waitlist",
    response_model=ApiResponse[None],
)
def confirm_waitlist(
    appointment_id: int,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    appointment_service.confirm_waitlist_offer(
        db,
        appointment_id,
        user.related_id,
    )
    return success()


@appointment_router.post(
    "/{appointment_id}/decline-waitlist",
    response_model=ApiResponse[None],
)
def decline_waitlist(
    appointment_id: int,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    appointment_service.decline_waitlist_offer(
        db,
        appointment_id,
        user.related_id,
    )
    return success()


@appointment_router.put("/{appointment_id}/cancel", response_model=ApiResponse[None])
def cancel_appointment(
    appointment_id: int,
    user: CurrentUser = Depends(require_member),
    db: Session = Depends(Database),
) -> dict:
    appointment_service.cancel(db, appointment_id, user.related_id, False)
    return success()


router.include_router(profile_router)
router.include_router(course_router)
router.include_router(appointment_router)
