from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Database, require_admin
from app.core.responses import success
from app.schemas import (
    AdminMemberRequest,
    AdminMemberVO,
    ApiResponse,
    AppointmentVO,
    CoachPayload,
    CoachVO,
    CoursePayload,
    CourseVO,
    DashboardVO,
    MembershipRenewalRequest,
    PageResult,
)
from app.services import (
    appointment_service,
    attendance_service,
    coach_service,
    course_service,
    dashboard_service,
    member_service,
    query_service,
)

router = APIRouter(prefix="/admin", tags=["管理员"], dependencies=[Depends(require_admin)])
member_router = APIRouter(prefix="/members")
coach_router = APIRouter(prefix="/coaches")
course_router = APIRouter(prefix="/courses")
appointment_router = APIRouter(prefix="/appointments")
dashboard_router = APIRouter(prefix="/dashboard")


@member_router.get("", response_model=ApiResponse[list[AdminMemberVO]])
def list_members(db: Session = Depends(Database)) -> dict:
    return success(member_service.list_members(db))


@member_router.get("/page", response_model=ApiResponse[PageResult[AdminMemberVO]])
def page_members(
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=10, alias="pageSize"),
    keyword: str | None = None,
    db: Session = Depends(Database),
) -> dict:
    return success(member_service.page_members(db, page_num, page_size, keyword))


@member_router.post("", response_model=ApiResponse[None])
def create_member(
    request: AdminMemberRequest,
    db: Session = Depends(Database),
) -> dict:
    member_service.create_member(db, request)
    return success()


@member_router.put("/{member_id}", response_model=ApiResponse[None])
def update_member(
    member_id: int,
    request: AdminMemberRequest,
    db: Session = Depends(Database),
) -> dict:
    member_service.update_member(db, member_id, request)
    return success()


@member_router.delete("/{member_id}", response_model=ApiResponse[None])
def delete_member(member_id: int, db: Session = Depends(Database)) -> dict:
    member_service.delete_member(db, member_id)
    return success()


@member_router.put("/{member_id}/renew", response_model=ApiResponse[None])
def renew_member(
    member_id: int,
    request: MembershipRenewalRequest,
    db: Session = Depends(Database),
) -> dict:
    member_service.renew_membership(db, member_id, request.months)
    return success()


@coach_router.get("", response_model=ApiResponse[list[CoachVO]])
def list_coaches(db: Session = Depends(Database)) -> dict:
    return success(coach_service.list_coaches(db))


@coach_router.get("/page", response_model=ApiResponse[PageResult[CoachVO]])
def page_coaches(
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=10, alias="pageSize"),
    keyword: str | None = None,
    db: Session = Depends(Database),
) -> dict:
    return success(coach_service.page_coaches(db, page_num, page_size, keyword))


@coach_router.post("", response_model=ApiResponse[None])
def create_coach(payload: CoachPayload, db: Session = Depends(Database)) -> dict:
    coach_service.create_coach(db, payload)
    return success()


@coach_router.put("/{coach_id}", response_model=ApiResponse[None])
def update_coach(
    coach_id: int,
    payload: CoachPayload,
    db: Session = Depends(Database),
) -> dict:
    coach_service.update_coach(db, coach_id, payload)
    return success()


@coach_router.delete("/{coach_id}", response_model=ApiResponse[None])
def delete_coach(coach_id: int, db: Session = Depends(Database)) -> dict:
    coach_service.delete_coach(db, coach_id)
    return success()


@course_router.get("", response_model=ApiResponse[list[CourseVO]])
def list_courses(db: Session = Depends(Database)) -> dict:
    return success(query_service.list_courses(db))


@course_router.get("/page", response_model=ApiResponse[PageResult[CourseVO]])
def page_courses(
    page_num: int = Query(default=1, alias="pageNum"),
    page_size: int = Query(default=10, alias="pageSize"),
    keyword: str | None = None,
    db: Session = Depends(Database),
) -> dict:
    return success(course_service.page_courses(db, page_num, page_size, keyword))


@course_router.post("", response_model=ApiResponse[None])
def create_course(payload: CoursePayload, db: Session = Depends(Database)) -> dict:
    course_service.create_course(db, payload)
    return success()


@course_router.put("/{course_id}", response_model=ApiResponse[None])
def update_course(
    course_id: int,
    payload: CoursePayload,
    db: Session = Depends(Database),
) -> dict:
    course_service.update_course(db, course_id, payload)
    return success()


@course_router.delete("/{course_id}", response_model=ApiResponse[None])
def delete_course(course_id: int, db: Session = Depends(Database)) -> dict:
    course_service.delete_course(db, course_id)
    return success()


@course_router.get("/{course_id}/checkin-code", response_model=ApiResponse[dict])
def checkin_code(course_id: int, db: Session = Depends(Database)) -> dict:
    return success(attendance_service.create_checkin_payload(db, course_id))


@appointment_router.get("", response_model=ApiResponse[list[AppointmentVO]])
def list_appointments(db: Session = Depends(Database)) -> dict:
    return success(query_service.list_appointments(db))


@appointment_router.put("/{appointment_id}/cancel", response_model=ApiResponse[None])
def cancel_appointment(appointment_id: int, db: Session = Depends(Database)) -> dict:
    appointment_service.cancel(db, appointment_id, None, True)
    return success()


@dashboard_router.get("", response_model=ApiResponse[DashboardVO])
def dashboard(db: Session = Depends(Database)) -> dict:
    return success(dashboard_service.get_dashboard(db))


@dashboard_router.get("/daily-report", response_model=ApiResponse[dict])
def daily_report(db: Session = Depends(Database)) -> dict:
    return success(dashboard_service.get_today_operations(db))


router.include_router(member_router)
router.include_router(coach_router)
router.include_router(course_router)
router.include_router(appointment_router)
router.include_router(dashboard_router)
