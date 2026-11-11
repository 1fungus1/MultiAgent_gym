from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Coach, Course, Member, SysUser


def seed_demo_data(db: Session) -> None:
    user_count = int(db.scalar(select(func.count(SysUser.id))) or 0)
    if user_count > 0:
        return

    admin = SysUser(
        username="admin",
        password=hash_password("123456"),
        role="admin",
        related_id=None,
        status=1,
    )
    member = Member(
        name="张三",
        phone="13800000000",
        gender="男",
        age=22,
        card_type="月卡",
        expire_time=(datetime.now() + timedelta(days=60)).date(),
        status=1,
    )
    db.add_all([admin, member])
    db.flush()
    db.add(
        SysUser(
            username="zhangsan",
            password=hash_password("123456"),
            role="member",
            related_id=member.id,
            status=1,
        )
    )

    coaches = [
        Coach(
            name="李教练",
            phone="13600000001",
            specialty="燃脂塑形",
            entry_date=(datetime.now() - timedelta(days=500)).date(),
            status=1,
        ),
        Coach(
            name="王教练",
            phone="13600000002",
            specialty="普拉提",
            entry_date=(datetime.now() - timedelta(days=700)).date(),
            status=1,
        ),
    ]
    db.add_all(coaches)
    db.flush()

    first_course_time = datetime(2026, 12, 3, 9, 0)
    second_course_time = datetime(2026, 12, 4, 14, 30)
    courses = [
        Course(
            name="燃脂团课",
            type="有氧",
            coach_id=coaches[0].id,
            start_time=first_course_time,
            end_time=first_course_time + timedelta(hours=1),
            capacity=20,
            booked_count=0,
            status=1,
        ),
        Course(
            name="普拉提塑形",
            type="塑形",
            coach_id=coaches[1].id,
            start_time=second_course_time,
            end_time=second_course_time + timedelta(hours=1),
            capacity=16,
            booked_count=0,
            status=1,
        ),
    ]
    db.add_all(courses)
    db.flush()
    db.flush()
