from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ApiResponse(APIModel, Generic[T]):
    code: int
    message: str
    data: T | None = None


class PageResult(APIModel, Generic[T]):
    records: list[T]
    total: int
    page_num: int = Field(alias="pageNum")
    page_size: int = Field(alias="pageSize")


class CurrentUser(APIModel):
    user_id: int = Field(alias="userId")
    username: str
    role: str
    related_id: int | None = Field(default=None, alias="relatedId")


class LoginRequest(APIModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(APIModel):
    token: str
    user_id: int = Field(alias="userId")
    username: str
    role: str
    related_id: int | None = Field(alias="relatedId")


class MemberPayload(APIModel):
    id: int | None = None
    name: str | None = None
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    card_type: str | None = Field(default=None, alias="cardType")
    expire_time: date | None = Field(default=None, alias="expireTime")
    status: int | None = None

    @field_validator("expire_time", mode="before")
    @classmethod
    def parse_expire_time(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip())

    @field_serializer("expire_time")
    def serialize_expire_time(self, value: date | None) -> str | None:
        return value.strftime("%Y-%m-%d") if value else None


class ProfileUpdate(APIModel):
    phone: str | None = None
    gender: str | None = None
    age: int | None = None


class PasswordRequest(APIModel):
    old_password: str | None = Field(default=None, alias="oldPassword")
    new_password: str | None = Field(default=None, alias="newPassword")


class AdminMemberRequest(APIModel):
    member: MemberPayload | None = None
    username: str | None = None
    password: str | None = None


class AdminMemberVO(APIModel):
    id: int
    name: str
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    card_type: str | None = Field(default=None, alias="cardType")
    expire_time: date | None = Field(default=None, alias="expireTime")
    status: int
    username: str | None = None

    @field_serializer("expire_time")
    def serialize_expire_time(self, value: date | None) -> str | None:
        return value.strftime("%Y-%m-%d") if value else None


class MemberVO(APIModel):
    id: int
    name: str
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    card_type: str | None = Field(default=None, alias="cardType")
    expire_time: date | None = Field(default=None, alias="expireTime")
    status: int

    @field_serializer("expire_time")
    def serialize_expire_time(self, value: date | None) -> str | None:
        return value.strftime("%Y-%m-%d") if value else None


class CoachPayload(APIModel):
    id: int | None = None
    name: str | None = None
    phone: str | None = None
    specialty: str | None = None
    entry_date: date | None = Field(default=None, alias="entryDate")
    status: int | None = None

    @field_validator("entry_date", mode="before")
    @classmethod
    def parse_entry_date(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip())

    @field_serializer("entry_date")
    def serialize_entry_date(self, value: date | None) -> str | None:
        return value.strftime("%Y-%m-%d") if value else None


class CoachVO(APIModel):
    id: int
    name: str
    phone: str | None = None
    specialty: str | None = None
    entry_date: date | None = Field(default=None, alias="entryDate")
    status: int

    @field_serializer("entry_date")
    def serialize_entry_date(self, value: date | None) -> str | None:
        return value.strftime("%Y-%m-%d") if value else None


class CoursePayload(APIModel):
    id: int | None = None
    name: str | None = None
    type: str | None = None
    coach_id: int | None = Field(default=None, alias="coachId")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    capacity: int | None = None
    booked_count: int | None = Field(default=None, alias="bookedCount")
    status: int | None = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_datetime(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, pattern)
            except ValueError:
                continue
        return datetime.fromisoformat(text)

    @field_serializer("start_time", "end_time")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M") if value else None


class CourseVO(APIModel):
    id: int
    name: str
    type: str | None = None
    coach_id: int | None = Field(default=None, alias="coachId")
    coach_name: str = Field(alias="coachName")
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    capacity: int
    booked_count: int = Field(alias="bookedCount")
    remaining: int
    can_waitlist: bool = Field(alias="canWaitlist")
    status: int
    time_status: str = Field(alias="timeStatus")

    @field_serializer("start_time", "end_time")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M") if value else None


class ReserveRequest(APIModel):
    course_id: int = Field(alias="courseId")


class MembershipRenewalRequest(APIModel):
    months: int = Field(ge=1, le=36)


class CheckinRequest(APIModel):
    token: str = Field(min_length=10, max_length=2000)


class CheckinVO(APIModel):
    appointment_id: int = Field(alias="appointmentId")
    course_id: int = Field(alias="courseId")
    course_name: str = Field(alias="courseName")
    checked_in_at: datetime = Field(alias="checkedInAt")

    @field_serializer("checked_in_at")
    def serialize_checked_in_at(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")


class NotificationVO(APIModel):
    id: int
    type: str
    title: str
    content: str
    related_id: int | None = Field(default=None, alias="relatedId")
    is_read: bool = Field(alias="isRead")
    create_time: datetime = Field(alias="createTime")

    @field_serializer("create_time")
    def serialize_create_time(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M")


class NotificationListVO(APIModel):
    unread_count: int = Field(alias="unreadCount")
    records: list[NotificationVO]


class AppointmentVO(APIModel):
    id: int
    member_id: int = Field(alias="memberId")
    member_name: str = Field(alias="memberName")
    course_id: int = Field(alias="courseId")
    course_name: str = Field(alias="courseName")
    coach_name: str = Field(alias="coachName")
    course_time: datetime | None = Field(default=None, alias="courseTime")
    course_end_time: datetime | None = Field(default=None, alias="courseEndTime")
    status: str
    create_time: datetime | None = Field(default=None, alias="createTime")
    update_time: datetime | None = Field(default=None, alias="updateTime")

    @field_serializer("course_time", "course_end_time")
    def serialize_course_time(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M") if value else None

    @field_serializer("create_time", "update_time")
    def serialize_create_time(self, value: datetime | None) -> str | None:
        return value.strftime("%Y-%m-%d %H:%M") if value else None


class DashboardVO(APIModel):
    member_count: int = Field(alias="memberCount")
    coach_count: int = Field(alias="coachCount")
    course_count: int = Field(alias="courseCount")
    appointment_count: int = Field(alias="appointmentCount")


class AgentHistoryMessage(APIModel):
    role: str
    content: str


class AgentChatRequest(APIModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[AgentHistoryMessage] = Field(default_factory=list, max_length=20)
    active_agent: str = Field(default="main", alias="activeAgent")
    pending_action_token: str | None = Field(
        default=None,
        alias="pendingActionToken",
    )
    confirmation_approved: bool = Field(
        default=False,
        alias="confirmationApproved",
    )


class AgentSource(APIModel):
    item_id: str = Field(alias="itemId")
    title: str
    chapter: str
    score: float


class AgentHandoffVO(APIModel):
    from_agent: str = Field(alias="fromAgent")
    to_agent: str = Field(alias="toAgent")
    reason: str


class AgentPendingActionVO(APIModel):
    action: str
    summary: str
    token: str


class AgentChatVO(APIModel):
    reply: str
    sources: list[AgentSource]
    active_agent: str = Field(alias="activeAgent")
    agent_path: list[str] = Field(alias="agentPath")
    handoff: AgentHandoffVO | None = None
    pending_action: AgentPendingActionVO | None = Field(
        default=None,
        alias="pendingAction",
    )


class HealthVO(APIModel):
    status: str
    database: str
