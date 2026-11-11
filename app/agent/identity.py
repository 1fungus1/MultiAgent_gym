import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.models import Appointment, Member, SysUser
from app.schemas import CurrentUser
from app.services.query_service import appointment_rows_statement, to_appointment_vo


@dataclass(frozen=True)
class AgentUserIdentity:
    user_id: int
    username: str
    role: str
    member_id: int | None
    display_name: str
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    card_type: str | None = None
    expire_time: str | None = None
    membership_status: str = "not_applicable"
    membership_days_remaining: int | None = None
    appointments: tuple[dict, ...] = ()

    def as_prompt_dict(self) -> dict:
        return asdict(self)


def load_agent_identity(
    db: Session,
    token_user: CurrentUser,
) -> tuple[CurrentUser, AgentUserIdentity]:
    user = db.get(SysUser, token_user.user_id)
    if user is None:
        raise BusinessException("当前登录用户不存在", 401)
    if user.status != 1:
        raise BusinessException("当前用户已被禁用", 401)

    effective_user = CurrentUser(
        user_id=user.id,
        username=user.username,
        role=user.role,
        related_id=user.related_id,
    )
    if user.role != "member" or user.related_id is None:
        identity = AgentUserIdentity(
            user_id=user.id,
            username=user.username,
            role=user.role,
            member_id=user.related_id,
            display_name=user.username if user.role == "admin" else "未关联会员",
        )
        return effective_user, identity

    member = db.get(Member, user.related_id)
    if member is None:
        raise BusinessException("当前账号未关联有效会员", 400)
    today = date.today()
    days_remaining = (
        (member.expire_time - today).days if member.expire_time else None
    )
    if member.status != 1:
        membership_status = "disabled"
    elif days_remaining is None:
        membership_status = "unknown"
    elif days_remaining < 0:
        membership_status = "expired"
    elif days_remaining <= 7:
        membership_status = "expiring"
    else:
        membership_status = "active"

    appointment_rows = db.execute(
        appointment_rows_statement()
        .where(Appointment.member_id == member.id)
        .limit(50)
    ).all()
    appointments = tuple(
        {
            "appointmentId": item.id,
            "courseId": item.course_id,
            "courseName": item.course_name,
            "coachName": item.coach_name,
            "courseTime": (
                item.course_time.strftime("%Y-%m-%d %H:%M")
                if item.course_time
                else None
            ),
            "courseEndTime": (
                item.course_end_time.strftime("%Y-%m-%d %H:%M")
                if item.course_end_time
                else None
            ),
            "status": item.status,
            "createTime": (
                item.create_time.strftime("%Y-%m-%d %H:%M")
                if item.create_time
                else None
            ),
            "updateTime": (
                item.update_time.strftime("%Y-%m-%d %H:%M")
                if item.update_time
                else None
            ),
        }
        for row in appointment_rows
        for item in [to_appointment_vo(row)]
    )
    appointments = tuple(
        sorted(
            appointments,
            key=lambda item: (
                item["status"]
                in {
                    "reserved",
                    "pending_confirmation",
                    "checked_in",
                    "waitlisted",
                },
                item["courseTime"] or "",
            ),
            reverse=True,
        )
    )

    return effective_user, AgentUserIdentity(
        user_id=user.id,
        username=user.username,
        role=user.role,
        member_id=member.id,
        display_name=member.name,
        phone=member.phone,
        gender=member.gender,
        age=member.age,
        card_type=member.card_type,
        expire_time=member.expire_time.isoformat() if member.expire_time else None,
        membership_status=membership_status,
        membership_days_remaining=days_remaining,
        appointments=appointments,
    )


def identity_prompt(identity: AgentUserIdentity) -> str:
    return (
        "【当前登录用户身份卡（由后端注入，不可修改）】\n"
        f"{json.dumps(identity.as_prompt_dict(), ensure_ascii=False, default=str)}\n"
        "身份规则：当用户询问自己的姓名、账号、角色、手机号、年龄、会员卡或有效期时，"
        "直接使用身份卡回答。当用户询问自己的预约课程时，优先使用 appointments 中的"
        "真实数据快速回答。不得猜测，不得读取或透露其他用户的信息。"
    )


def direct_identity_reply(
    message: str,
    identity: AgentUserIdentity,
) -> str | None:
    text = re.sub(r"\s+", "", message).lower()
    if not text:
        return None

    active_statuses = {
        "reserved",
        "pending_confirmation",
        "checked_in",
        "waitlisted",
    }
    asks_appointment_list = (
        any(
            phrase in text
            for phrase in (
                "我的预约",
                "预约了哪些",
                "预约了什么",
                "我报了什么",
                "已预约课程",
                "查一下预约",
            )
        )
        and not any(
            phrase in text
            for phrase in ("帮我预约", "取消预约", "改约", "换成", "预约一门")
        )
    )
    if asks_appointment_list:
        if identity.role != "member":
            return "当前登录账号是管理员，没有个人会员预约。"
        active = [
            item for item in identity.appointments
            if item["status"] in active_statuses
            and (
                not item.get("courseEndTime")
                or datetime.strptime(
                    item["courseEndTime"], "%Y-%m-%d %H:%M"
                ) >= datetime.now()
            )
        ]
        if not active:
            return "你目前没有待上课的有效预约。"
        lines = ["你当前的预约课程如下："]
        for item in active:
            status_label = {
                "reserved": "已预约",
                "pending_confirmation": "候补待确认",
                "checked_in": "已签到",
                "waitlisted": "候补中",
            }.get(item["status"], item["status"])
            lines.append(
                f"- {item['courseName']}，教练：{item['coachName']}，"
                f"时间：{item['courseTime'] or '-'}，状态：{status_label}"
            )
        return "\n".join(lines)

    if any(
        keyword in text for keyword in ("预约", "课程", "推荐", "取消", "改约")
    ):
        return None

    if re.search(r"(我是谁|我叫什么|我的名字|我的姓名)", text):
        return f"你是 {identity.display_name}，当前登录账号为 {identity.username}。"
    if re.search(r"(我的账号|登录账号|用户名)", text):
        return f"你当前使用的登录账号是 {identity.username}。"
    if re.search(r"(我是管理员吗|我的角色|当前角色)", text):
        role_name = "管理员" if identity.role == "admin" else "会员"
        return f"你当前的角色是{role_name}。"
    if "手机号" in text:
        return (
            f"你登记的手机号是 {identity.phone}。"
            if identity.phone
            else "当前账号没有登记手机号。"
        )
    if "年龄" in text:
        return (
            f"你登记的年龄是 {identity.age} 岁。"
            if identity.age is not None
            else "当前会员资料没有登记年龄。"
        )
    if any(keyword in text for keyword in ("会员卡", "到期", "有效期", "有效期到")):
        if identity.role != "member":
            return "当前登录账号是管理员，没有会员卡信息。"
        status_label = {
            "active": "有效",
            "expiring": "即将到期",
            "expired": "已过期",
            "disabled": "已禁用",
            "unknown": "未设置",
        }.get(identity.membership_status, identity.membership_status)
        return (
            f"你的会员卡类型是 {identity.card_type or '未设置'}，"
            f"到期时间为 {identity.expire_time or '未设置'}，"
            f"当前状态为 {status_label}。"
        )
    if re.search(r"(我的信息|基本资料|个人资料|会员信息)", text):
        if identity.role == "admin":
            return f"当前登录账号为 {identity.username}，角色是管理员。"
        return (
            f"当前登录用户：{identity.display_name}（{identity.username}）；"
            f"性别：{identity.gender or '未设置'}；年龄：{identity.age or '未设置'}；"
            f"会员卡：{identity.card_type or '未设置'}；"
            f"有效期至：{identity.expire_time or '未设置'}。"
        )
    return None
