from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PrimaryKey = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Member(TimestampMixin, Base):
    __tablename__ = "member"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    gender: Mapped[str | None] = mapped_column(String(10))
    age: Mapped[int | None] = mapped_column(Integer)
    card_type: Mapped[str | None] = mapped_column(String(30))
    expire_time: Mapped[date | None] = mapped_column(Date)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SysUser(TimestampMixin, Base):
    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    related_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("member.id", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (Index("idx_sys_user_related_id", "related_id"),)


class Coach(TimestampMixin, Base):
    __tablename__ = "coach"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    specialty: Mapped[str | None] = mapped_column(String(100))
    entry_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class Course(TimestampMixin, Base):
    __tablename__ = "course"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str | None] = mapped_column(String(50))
    coach_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("coach.id"),
        nullable=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    booked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (Index("idx_course_coach_start", "coach_id", "start_time"),)


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointment"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("member.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("course.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="reserved")

    __table_args__ = (
        UniqueConstraint("member_id", "course_id", name="uk_member_course"),
        Index("idx_appointment_course_status", "course_id", "status"),
    )


class AppointmentActionLog(Base):
    __tablename__ = "appointment_action_log"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    course_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_course_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(255))
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_appointment_log_create_time", "create_time"),
        Index("idx_appointment_log_member", "member_id"),
    )


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(PrimaryKey, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    member_id: Mapped[int | None] = mapped_column(BigInteger)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    related_id: Mapped[int | None] = mapped_column(BigInteger)
    is_read: Mapped[bool] = mapped_column(nullable=False, default=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_notification_user_read", "user_id", "is_read"),
        Index("idx_notification_create_time", "create_time"),
    )
