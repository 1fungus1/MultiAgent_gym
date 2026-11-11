from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import Appointment, AppointmentActionLog, Coach, Course, Member
from app.schemas import DashboardVO


def get_dashboard(db: Session) -> DashboardVO:
    return DashboardVO(
        member_count=int(db.scalar(select(func.count(Member.id))) or 0),
        coach_count=int(db.scalar(select(func.count(Coach.id))) or 0),
        course_count=int(db.scalar(select(func.count(Course.id))) or 0),
        appointment_count=int(
            db.scalar(
                select(func.count(Appointment.id)).where(
                    Appointment.status == "reserved"
                )
            )
            or 0
        ),
    )


def get_today_operations(db: Session, target_date: date | None = None) -> dict[str, Any]:
    today = target_date or date.today()
    day_start = datetime.combine(today, time.min)
    day_end = day_start + timedelta(days=1)
    rows = db.execute(
        select(Course, Coach.name)
        .outerjoin(Coach, Course.coach_id == Coach.id)
        .where(
            Course.start_time >= day_start,
            Course.start_time < day_end,
        )
        .order_by(Course.start_time, Course.id)
    ).all()
    course_ids = [course.id for course, _coach_name in rows]
    appointments = (
        list(
            db.scalars(
                select(Appointment).where(Appointment.course_id.in_(course_ids))
            ).all()
        )
        if course_ids
        else []
    )
    occupied_statuses = {"reserved", "pending_confirmation", "checked_in"}
    reserved = [item for item in appointments if item.status in occupied_statuses]
    canceled = [item for item in appointments if item.status == "canceled"]
    checked_in = [item for item in appointments if item.status == "checked_in"]
    no_show = [item for item in appointments if item.status == "no_show"]
    waitlisted = [item for item in appointments if item.status == "waitlisted"]
    total_capacity = sum(course.capacity for course, _coach_name in rows)
    course_details = []
    full_courses = []
    for course, coach_name in rows:
        course_reserved = sum(
            1 for item in reserved if item.course_id == course.id
        )
        course_canceled = sum(
            1 for item in canceled if item.course_id == course.id
        )
        course_checked_in = sum(
            1 for item in checked_in if item.course_id == course.id
        )
        course_no_show = sum(
            1 for item in no_show if item.course_id == course.id
        )
        course_waitlisted = sum(
            1 for item in waitlisted if item.course_id == course.id
        )
        remaining = max(course.capacity - course_reserved, 0)
        detail = {
            "id": course.id,
            "name": course.name,
            "type": course.type,
            "coachName": coach_name or "-",
            "startTime": (
                course.start_time.strftime("%Y-%m-%d %H:%M")
                if course.start_time
                else None
            ),
            "endTime": (
                course.end_time.strftime("%Y-%m-%d %H:%M")
                if course.end_time
                else None
            ),
            "capacity": course.capacity,
            "reserved": course_reserved,
            "canceled": course_canceled,
            "checkedIn": course_checked_in,
            "noShow": course_no_show,
            "waitlisted": course_waitlisted,
            "remaining": remaining,
            "bookedCountField": course.booked_count,
            "status": "可预约" if course.status == 1 else "停课",
        }
        course_details.append(detail)
        if course.status == 1 and remaining == 0:
            full_courses.append(
                {
                    "id": course.id,
                    "name": course.name,
                    "reserved": course_reserved,
                    "capacity": course.capacity,
                }
            )

    target_course = aliased(Course)
    activity_rows = db.execute(
        select(
            AppointmentActionLog,
            Member.name,
            Course.name,
            target_course.name,
        )
        .outerjoin(Member, AppointmentActionLog.member_id == Member.id)
        .outerjoin(Course, AppointmentActionLog.course_id == Course.id)
        .outerjoin(
            target_course,
            AppointmentActionLog.target_course_id == target_course.id,
        )
        .where(
            AppointmentActionLog.create_time >= day_start,
            AppointmentActionLog.create_time < day_end,
        )
        .order_by(AppointmentActionLog.create_time.desc())
    ).all()
    has_action_logs = bool(activity_rows)
    activities = [
        {
            "appointmentId": log.appointment_id,
            "memberName": member_name or "-",
            "action": log.action,
            "courseName": course_name or "-",
            "targetCourseName": target_course_name,
            "detail": log.detail,
            "time": log.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for log, member_name, course_name, target_course_name in activity_rows
    ]
    logged_appointment_ids = {
        log.appointment_id for log, *_rest in activity_rows
    }

    # Existing deployments did not record action history. Merge best-effort
    # action inference for appointments that have no audit log.
    legacy_rows = db.execute(
        select(Appointment, Member.name, Course.name)
        .outerjoin(Member, Appointment.member_id == Member.id)
        .outerjoin(Course, Appointment.course_id == Course.id)
        .where(
            or_(
                and_(
                    Appointment.create_time >= day_start,
                    Appointment.create_time < day_end,
                ),
                and_(
                    Appointment.update_time >= day_start,
                    Appointment.update_time < day_end,
                ),
            ),
        )
        .order_by(Appointment.update_time.desc())
    ).all()
    inferred_count = 0
    for appointment, member_name, course_name in legacy_rows:
        if appointment.id in logged_appointment_ids:
            continue
        if appointment.create_time and day_start <= appointment.create_time < day_end:
            inferred_count += 1
            activities.append(
                {
                    "appointmentId": appointment.id,
                    "memberName": member_name or "-",
                    "action": "reserve",
                    "courseName": course_name or "-",
                    "targetCourseName": None,
                    "detail": f"创建预约：{course_name or appointment.course_id}",
                    "time": appointment.create_time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
        if (
            appointment.status == "reserved"
            and appointment.update_time
            and appointment.create_time
            and appointment.update_time
            > appointment.create_time + timedelta(seconds=1)
            and day_start <= appointment.update_time < day_end
        ):
            inferred_count += 1
            activities.append(
                {
                    "appointmentId": appointment.id,
                    "memberName": member_name or "-",
                    "action": "update",
                    "courseName": course_name or "-",
                    "targetCourseName": None,
                    "detail": f"更新预约：{course_name or appointment.course_id}",
                    "time": appointment.update_time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
        if (
            appointment.status == "canceled"
            and appointment.update_time
            and day_start <= appointment.update_time < day_end
        ):
            inferred_count += 1
            activities.append(
                {
                    "appointmentId": appointment.id,
                    "memberName": member_name or "-",
                    "action": "cancel",
                    "courseName": course_name or "-",
                    "targetCourseName": None,
                    "detail": f"取消预约：{course_name or appointment.course_id}",
                    "time": appointment.update_time.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )
    activities.sort(key=lambda item: item["time"], reverse=True)

    if has_action_logs and inferred_count:
        activity_source = "appointment_log_plus_inference"
    elif has_action_logs:
        activity_source = "appointment_log"
    else:
        activity_source = "legacy_inference"

    activity_counts = {
        action: sum(1 for item in activities if item["action"] == action)
        for action in ("reserve", "cancel", "change", "update")
    }
    expiring_members = int(
        db.scalar(
            select(func.count(Member.id)).where(
                Member.status == 1,
                Member.expire_time >= today,
                Member.expire_time <= today + timedelta(days=7),
            )
        )
        or 0
    )
    expired_members = int(
        db.scalar(
            select(func.count(Member.id)).where(
                Member.expire_time < today,
            )
        )
        or 0
    )
    return {
        "date": today.isoformat(),
        "courseCount": len(rows),
        "reservedCount": len(reserved),
        "canceledCount": len(canceled),
        "waitlistCount": len(waitlisted),
        "checkedInCount": len(checked_in),
        "noShowCount": len(no_show),
        "attendanceRate": round(
            len(checked_in) / len(reserved) * 100, 1
        )
        if reserved
        else 0.0,
        "expiringMemberCount": expiring_members,
        "expiredMemberCount": expired_members,
        "totalCapacity": total_capacity,
        "occupancyRate": round(
            len(reserved) / total_capacity * 100, 1
        )
        if total_capacity
        else 0.0,
        "fullCourseCount": len(full_courses),
        "fullCourses": full_courses,
        "courses": course_details,
        "activitySource": activity_source,
        "todayReservationCount": activity_counts["reserve"],
        "todayCancellationCount": activity_counts["cancel"],
        "todayChangeCount": activity_counts["change"],
        "todayUpdateCount": activity_counts["update"],
        "todayActivityCount": len(activities),
        "appointmentActivity": activities,
    }
