import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.agent.actions import (
    PendingAppointmentAction,
    create_pending_action_token,
)
from app.agent.identity import AgentUserIdentity
from app.agent.knowledge import KnowledgeHit
from app.agent.protocol import (
    APPOINTMENT_AGENT,
    COURSE_AGENT,
    MAIN_AGENT,
    OPERATIONS_AGENT,
)
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.rag import get_hybrid_retriever
from app.schemas import CurrentUser
from app.services import (
    appointment_service,
    course_service,
    dashboard_service,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentToolContext:
    db: Session
    user: CurrentUser
    knowledge_sources: list[KnowledgeHit]
    identity: AgentUserIdentity
    pending_action_token: str | None = None
    pending_action: PendingAppointmentAction | None = None
    pending_action_error: str | None = None
    confirmation_allowed: bool = False
    action_completed: bool = False
    knowledge_search_used: bool = False


def _handoff_tool(target: str, description: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": f"transfer_to_{target}_agent",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "简短说明为什么需要转移会话权",
                    }
                },
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    }


def _read_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_fitness_knowledge",
                "description": "检索项目健身知识库，补充训练、营养、安全和恢复依据。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "需要检索的问题或关键词",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_available_courses",
                "description": "查询数据库中当前仍可预约的未来课程和剩余名额。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "课程名称关键词",
                        },
                        "course_type": {
                            "type": "string",
                            "description": "课程类型",
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_my_appointments",
                "description": "查询当前会员自己的预约记录。",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        },
    ]


APPOINTMENT_TOOLS = [
    *_read_tools(),
    {
        "type": "function",
        "function": {
            "name": "prepare_course_reservation",
            "description": "准备预约课程，只生成待确认操作，不修改数据库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "integer",
                        "description": "要预约的课程 ID",
                    }
                },
                "required": ["course_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_appointment_cancellation",
            "description": "准备取消当前会员的预约，只生成待确认操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "要取消的预约 ID",
                    }
                },
                "required": ["appointment_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_course_waitlist",
            "description": "课程满员时准备加入候补队列，只生成待确认操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "integer",
                        "description": "需要候补的课程 ID",
                    }
                },
                "required": ["course_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_appointment_change",
            "description": "准备将会员现有预约改到另一门课程，只生成待确认操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "原预约 ID",
                    },
                    "new_course_id": {
                        "type": "integer",
                        "description": "目标课程 ID",
                    },
                },
                "required": ["appointment_id", "new_course_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_pending_appointment_action",
            "description": (
                "执行后端注入的待确认预约操作。只有用户明确确认后才能调用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discard_pending_appointment_action",
            "description": "用户拒绝确认或决定放弃时，清除待确认操作，不修改数据库。",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    _handoff_tool(
        COURSE_AGENT,
        "当用户需要课程推荐或筛选课程时，转移给课程推荐 Agent。",
    ),
    _handoff_tool(MAIN_AGENT, "当问题不属于预约、取消或改约时，转回主 Agent。"),
]

COURSE_TOOLS = [
    *_read_tools(),
    _handoff_tool(
        APPOINTMENT_AGENT,
        "当用户明确要求预约、取消或改约时，转移给预约 Agent。",
    ),
    _handoff_tool(MAIN_AGENT, "当问题不属于课程推荐时，转回主 Agent。"),
]

OPERATIONS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_today_operations",
            "description": "管理员查询今日课程、预约、容量、满员课程等真实数据。",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    _handoff_tool(MAIN_AGENT, "当问题不属于运营分析时，转回主 Agent。"),
]

MAIN_TOOLS = [
    _read_tools()[0],
    _handoff_tool(
        APPOINTMENT_AGENT,
        "用户涉及预约、取消预约或改约时，必须转移给预约 Agent。",
    ),
    _handoff_tool(
        COURSE_AGENT,
        "用户要求推荐、筛选或比较课程时，必须转移给课程推荐 Agent。",
    ),
    _handoff_tool(
        OPERATIONS_AGENT,
        "管理员要求分析今日课程、预约人数、满员课程或运营情况时，转移给运营 Agent。",
    ),
]

AGENT_TOOLS = {
    MAIN_AGENT: MAIN_TOOLS,
    APPOINTMENT_AGENT: APPOINTMENT_TOOLS,
    COURSE_AGENT: COURSE_TOOLS,
    OPERATIONS_AGENT: OPERATIONS_TOOLS,
}


def _merge_sources(context: AgentToolContext, hits: list[KnowledgeHit]) -> None:
    existing = {source.item_id for source in context.knowledge_sources}
    context.knowledge_sources.extend(
        hit for hit in hits if hit.item_id not in existing
    )


def _course_snapshot(course: Any) -> dict[str, Any]:
    return {
        "id": course.id,
        "name": course.name,
        "type": course.type,
        "coachName": course.coach_name,
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
        "bookedCount": course.booked_count,
        "remaining": max(course.capacity - course.booked_count, 0),
    }


def _appointment_snapshot(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
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
        "updateTime": (
            item.update_time.strftime("%Y-%m-%d %H:%M")
            if item.update_time
            else None
        ),
    }


def _available_course_by_id(context: AgentToolContext, course_id: int) -> Any:
    course = next(
        (
            item
            for item in course_service.available_courses(context.db)
            if item.id == course_id
        ),
        None,
    )
    if course is None:
        raise BusinessException("课程不存在、已满或不可预约")
    return course


def _member_course_by_id(context: AgentToolContext, course_id: int) -> Any:
    course = next(
        (
            item
            for item in course_service.member_course_options(context.db)
            if item.id == course_id
        ),
        None,
    )
    if course is None:
        raise BusinessException("课程不存在或不可候补")
    return course


def _member_appointment(context: AgentToolContext, appointment_id: int) -> Any:
    if context.user.role != "member":
        raise BusinessException("只有会员可以操作自己的预约")
    appointments = appointment_service.list_member_appointments(
        context.db,
        context.user.related_id,
    )
    appointment = next(
        (item for item in appointments if item.id == appointment_id),
        None,
    )
    if appointment is None:
        raise BusinessException("预约不存在")
    if appointment.status != "reserved":
        raise BusinessException("该预约已取消")
    return appointment


def _set_pending_action(
    context: AgentToolContext,
    action: PendingAppointmentAction,
) -> dict[str, Any]:
    token = create_pending_action_token(action)
    context.pending_action = action
    context.pending_action_token = token
    context.pending_action_error = None
    context.confirmation_allowed = False
    return {
        "status": "awaiting_confirmation",
        "action": action.action,
        "summary": action.summary,
        "instruction": "请向用户展示操作摘要并等待明确确认，不要声称已经执行。",
    }


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    context: AgentToolContext,
) -> dict[str, Any]:
    try:
        if name == "search_fitness_knowledge":
            context.knowledge_search_used = True
            hits = get_hybrid_retriever().search(
                str(arguments.get("query", "")).strip(),
                top_k=settings.agent_knowledge_top_k,
            )
            _merge_sources(context, hits)
            return {
                "results": [
                    {
                        "itemId": hit.item_id,
                        "title": hit.title,
                        "chapter": hit.chapter,
                        "content": hit.content[:2400],
                    }
                    for hit in hits
                ]
            }

        if name == "list_available_courses":
            keyword = str(arguments.get("keyword") or "").strip().lower()
            course_type = str(arguments.get("course_type") or "").strip().lower()
            limit = max(1, min(int(arguments.get("limit") or 8), 10))
            courses = course_service.available_courses(context.db)
            if keyword:
                courses = [
                    course for course in courses if keyword in course.name.lower()
                ]
            if course_type:
                courses = [
                    course
                    for course in courses
                    if course.type and course_type in course.type.lower()
                ]
            return {"courses": [_course_snapshot(course) for course in courses[:limit]]}

        if name == "get_my_appointments":
            if context.user.role != "member":
                return {"error": "只有会员可以查询个人预约"}
            appointments = appointment_service.list_member_appointments(
                context.db,
                context.user.related_id,
            )
            return {
                "appointments": [
                    _appointment_snapshot(item) for item in appointments
                ]
            }

        if name == "prepare_course_reservation":
            if context.user.role != "member" or context.user.related_id is None:
                return {"error": "只有会员可以预约课程"}
            course_id = int(arguments.get("course_id") or 0)
            course = _available_course_by_id(context, course_id)
            summary = (
                f"预约课程：{course.name}，时间："
                f"{course.start_time.strftime('%Y-%m-%d %H:%M')}，"
                f"教练：{course.coach_name}"
            )
            return _set_pending_action(
                context,
                PendingAppointmentAction(
                    action="reserve",
                    member_id=context.user.related_id,
                    course_id=course.id,
                    summary=summary,
                ),
            )

        if name == "prepare_course_waitlist":
            if context.user.role != "member" or context.user.related_id is None:
                return {"error": "只有会员可以加入候补"}
            course_id = int(arguments.get("course_id") or 0)
            course = _member_course_by_id(context, course_id)
            if not course.can_waitlist:
                raise BusinessException("课程仍有名额，请直接预约")
            summary = (
                f"加入候补：{course.name}，时间："
                f"{course.start_time.strftime('%Y-%m-%d %H:%M')}，"
                "有名额时会通知您在限定时间内确认。"
            )
            return _set_pending_action(
                context,
                PendingAppointmentAction(
                    action="waitlist",
                    member_id=context.user.related_id,
                    course_id=course.id,
                    summary=summary,
                ),
            )

        if name == "prepare_appointment_cancellation":
            appointment_id = int(arguments.get("appointment_id") or 0)
            appointment = _member_appointment(context, appointment_id)
            summary = (
                f"取消预约：{appointment.course_name}，时间："
                f"{appointment.course_time.strftime('%Y-%m-%d %H:%M')}"
                if appointment.course_time
                else f"取消预约：{appointment.course_name}"
            )
            return _set_pending_action(
                context,
                PendingAppointmentAction(
                    action="cancel",
                    member_id=context.user.related_id or 0,
                    appointment_id=appointment.id,
                    summary=summary,
                ),
            )

        if name == "prepare_appointment_change":
            appointment_id = int(arguments.get("appointment_id") or 0)
            new_course_id = int(arguments.get("new_course_id") or 0)
            appointment = _member_appointment(context, appointment_id)
            new_course = _available_course_by_id(context, new_course_id)
            if appointment.course_id == new_course_id:
                raise BusinessException("新课程与原课程相同")
            summary = (
                f"将预约从“{appointment.course_name}”改为“{new_course.name}”，"
                f"新课程时间：{new_course.start_time.strftime('%Y-%m-%d %H:%M')}"
            )
            return _set_pending_action(
                context,
                PendingAppointmentAction(
                    action="change",
                    member_id=context.user.related_id or 0,
                    appointment_id=appointment.id,
                    target_course_id=new_course.id,
                    summary=summary,
                ),
            )

        if name == "confirm_pending_appointment_action":
            if (
                not context.confirmation_allowed
                or context.pending_action is None
            ):
                raise BusinessException("当前没有经过用户确认的待执行操作")
            action = context.pending_action
            if context.user.role != "member" or context.user.related_id != action.member_id:
                raise BusinessException("不能执行其他会员的预约操作")
            if action.action == "reserve" and action.course_id is not None:
                appointment_service.reserve(
                    context.db,
                    action.member_id,
                    action.course_id,
                )
            elif action.action == "waitlist" and action.course_id is not None:
                appointment_service.join_waitlist(
                    context.db,
                    action.member_id,
                    action.course_id,
                )
            elif action.action == "cancel" and action.appointment_id is not None:
                appointment_service.cancel(
                    context.db,
                    action.appointment_id,
                    action.member_id,
                    False,
                )
            elif (
                action.action == "change"
                and action.appointment_id is not None
                and action.target_course_id is not None
            ):
                appointment_service.change_course(
                    context.db,
                    action.appointment_id,
                    action.member_id,
                    action.target_course_id,
                )
            else:
                raise BusinessException("待确认操作数据不完整")
            context.pending_action = None
            context.pending_action_token = None
            context.action_completed = True
            return {"status": "completed", "summary": action.summary}

        if name == "discard_pending_appointment_action":
            context.pending_action = None
            context.pending_action_token = None
            context.pending_action_error = None
            context.confirmation_allowed = False
            return {"status": "discarded"}

        if name == "get_today_operations":
            if context.user.role != "admin":
                return {"error": "只有管理员可以查看运营数据"}
            return {"operations": dashboard_service.get_today_operations(context.db)}

        return {"error": f"未知工具：{name}"}
    except BusinessException as exception:
        return {"error": exception.message}
    except Exception:
        logger.exception("Agent tool failed: %s", name)
        return {"error": "业务数据查询或操作失败，请稍后重试"}


def tool_result_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)
