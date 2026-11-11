from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from app.core.config import settings

PendingActionType = Literal["reserve", "waitlist", "cancel", "change"]


class AgentActionError(ValueError):
    """Raised when a signed appointment action cannot be used."""


@dataclass(frozen=True)
class PendingAppointmentAction:
    action: PendingActionType
    member_id: int
    summary: str
    course_id: int | None = None
    appointment_id: int | None = None
    target_course_id: int | None = None


def _encode(action: PendingAppointmentAction) -> str:
    now = datetime.now(UTC)
    payload = {
        "typ": "pending_appointment_action",
        "aud": "multiagent-gym-agent",
        "action": action.action,
        "memberId": action.member_id,
        "summary": action.summary,
        "courseId": action.course_id,
        "appointmentId": action.appointment_id,
        "targetCourseId": action.target_course_id,
        "iat": now,
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_pending_action_token(action: PendingAppointmentAction) -> str:
    return _encode(action)


def decode_pending_action_token(token: str | None) -> PendingAppointmentAction | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience="multiagent-gym-agent",
            options={"require": ["exp", "iat", "action", "memberId"]},
        )
    except jwt.PyJWTError as exception:
        raise AgentActionError("待确认操作已失效，请重新发起") from exception

    if payload.get("typ") != "pending_appointment_action":
        raise AgentActionError("待确认操作类型无效")
    action_type = payload.get("action")
    if action_type not in {"reserve", "waitlist", "cancel", "change"}:
        raise AgentActionError("待确认操作类型无效")
    try:
        return PendingAppointmentAction(
            action=action_type,
            member_id=int(payload["memberId"]),
            summary=str(payload["summary"]),
            course_id=(
                int(payload["courseId"])
                if payload.get("courseId") is not None
                else None
            ),
            appointment_id=(
                int(payload["appointmentId"])
                if payload.get("appointmentId") is not None
                else None
            ),
            target_course_id=(
                int(payload["targetCourseId"])
                if payload.get("targetCourseId") is not None
                else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exception:
        raise AgentActionError("待确认操作数据不完整") from exception
