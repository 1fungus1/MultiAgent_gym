from itertools import count

from app.agent.actions import (
    PendingAppointmentAction,
    create_pending_action_token,
    decode_pending_action_token,
)
from app.agent.knowledge import get_knowledge_base
from app.agent.protocol import (
    APPOINTMENT_AGENT,
    COURSE_AGENT,
    MAIN_AGENT,
    OPERATIONS_AGENT,
)
from app.agent.service import _current_time_text
from app.agent.tools import AGENT_TOOLS
from app.db.session import SessionLocal
from app.services import appointment_service, dashboard_service
from tests.conftest import login


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def tool_call(call_id: str, name: str, arguments: str = "{}") -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": arguments,
                            },
                        }
                    ],
                }
            }
        ]
    }


def final_answer(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                }
            }
        ]
    }


def install_completion_sequence(monkeypatch, responses):
    call_counter = count()
    calls = []
    response_list = list(responses)

    def fake_completion(payload):
        calls.append(payload)
        index = next(call_counter)
        return response_list[index]

    monkeypatch.setattr("app.agent.service._post_completion", fake_completion)
    return calls


def test_knowledge_base_parsing_and_retrieval():
    knowledge = get_knowledge_base()
    assert len(knowledge.chunks) == 50

    hits = knowledge.search("力量训练每周应该练几次", top_k=3)
    assert hits
    assert any(hit.item_id.startswith(("RES-", "PRO-")) for hit in hits)

    protein_hits = knowledge.search("蛋白质摄入怎么安排", top_k=3)
    assert protein_hits
    assert any(hit.item_id.startswith("NUT-") for hit in protein_hits)
    assert knowledge.search("现在有哪些可以预约的课程", top_k=3) == []


def test_agent_time_context_contains_shanghai_datetime():
    current = _current_time_text()
    assert "Asia/Shanghai" in current
    assert len(current) >= 25


def test_identity_and_reservation_snapshot_are_answered_without_llm(
    client, monkeypatch
):
    token = login(client, "zhangsan")
    course = client.get(
        "/api/member/courses",
        headers=auth_headers(token),
    ).json()["data"][0]
    client.post(
        "/api/member/appointments",
        headers=auth_headers(token),
        json={"courseId": course["id"]},
    )

    def fail_if_called(_payload):
        raise AssertionError("基础身份和预约快照不应调用 LLM")

    monkeypatch.setattr("app.agent.service._post_completion", fail_if_called)
    identity = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": "我是谁？", "history": []},
    ).json()
    appointments = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": "我的预约有哪些？", "history": []},
    ).json()

    assert identity["code"] == 200
    assert "张三" in identity["data"]["reply"]
    assert "zhangsan" in identity["data"]["reply"]
    assert appointments["code"] == 200
    assert course["name"] in appointments["data"]["reply"]
    assert appointments["data"]["activeAgent"] == MAIN_AGENT


def test_agent_least_privilege_and_handoff_tools():
    main_tools = {
        item["function"]["name"] for item in AGENT_TOOLS[MAIN_AGENT]
    }
    appointment_tools = {
        item["function"]["name"] for item in AGENT_TOOLS[APPOINTMENT_AGENT]
    }
    course_tools = {
        item["function"]["name"] for item in AGENT_TOOLS[COURSE_AGENT]
    }
    operation_tools = {
        item["function"]["name"] for item in AGENT_TOOLS[OPERATIONS_AGENT]
    }

    assert "transfer_to_appointment_agent" in main_tools
    assert "transfer_to_course_agent" in main_tools
    assert "confirm_pending_appointment_action" not in main_tools
    assert "prepare_course_reservation" in appointment_tools
    assert "prepare_course_waitlist" in appointment_tools
    assert "confirm_pending_appointment_action" in appointment_tools
    assert "list_available_courses" in course_tools
    assert "get_today_operations" in operation_tools


def test_course_question_hands_off_to_course_agent(client, monkeypatch):
    token = login(client, "zhangsan")
    calls = install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "handoff_course",
                "transfer_to_course_agent",
                '{"reason":"用户要求课程推荐"}',
            ),
            final_answer("推荐燃脂团课，目前剩余 20 个名额。"),
        ],
    )
    response = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": "推荐一门减脂课程", "history": []},
    ).json()

    assert response["code"] == 200
    assert response["data"]["activeAgent"] == COURSE_AGENT
    assert response["data"]["agentPath"] == [MAIN_AGENT, COURSE_AGENT]
    assert response["data"]["handoff"]["toAgent"] == COURSE_AGENT
    assert len(calls) == 2
    assert "燃脂团课" in calls[1]["messages"][0]["content"]
    assert "zhangsan" in calls[0]["messages"][0]["content"]


def test_appointment_requires_confirmation_before_database_write(
    client, monkeypatch
):
    token = login(client, "zhangsan")
    course = client.get(
        "/api/member/courses",
        headers=auth_headers(token),
    ).json()["data"][0]
    install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "handoff_appointment",
                "transfer_to_appointment_agent",
                '{"reason":"用户请求预约"}',
            ),
            tool_call(
                "prepare_reserve",
                "prepare_course_reservation",
                f'{{"course_id":{course["id"]}}}',
            ),
            final_answer("请确认是否预约该课程。"),
        ],
    )
    response = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": f"帮我预约课程 {course['id']}", "history": []},
    ).json()

    assert response["code"] == 200
    assert response["data"]["activeAgent"] == APPOINTMENT_AGENT
    assert response["data"]["pendingAction"]["action"] == "reserve"
    pending_token = response["data"]["pendingAction"]["token"]
    assert decode_pending_action_token(pending_token).course_id == course["id"]

    before_confirm = client.get(
        "/api/member/appointments",
        headers=auth_headers(token),
    ).json()["data"]
    assert before_confirm == []

    install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "confirm_reserve",
                "confirm_pending_appointment_action",
            ),
            final_answer("预约已完成。"),
        ],
    )
    confirmed = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={
            "message": "确认预约",
            "history": [{"role": "assistant", "content": "请确认是否预约该课程。"}],
            "activeAgent": APPOINTMENT_AGENT,
            "pendingActionToken": pending_token,
            "confirmationApproved": True,
        },
    ).json()

    assert confirmed["code"] == 200
    assert confirmed["data"]["pendingAction"] is None
    appointments = client.get(
        "/api/member/appointments",
        headers=auth_headers(token),
    ).json()["data"]
    assert len(appointments) == 1
    assert appointments[0]["courseId"] == course["id"]


def test_pending_action_token_rejects_tampering():
    token = create_pending_action_token(
        PendingAppointmentAction(
            action="reserve",
            member_id=1,
            course_id=1,
            summary="测试预约",
        )
    )
    assert decode_pending_action_token(token).member_id == 1
    try:
        decode_pending_action_token(token + "tampered")
    except ValueError as exception:
        assert "失效" in str(exception)
    else:
        raise AssertionError("被篡改的待确认令牌必须失效")


def test_pending_token_alone_cannot_write_database(client, monkeypatch):
    token = login(client, "zhangsan")
    course = client.get(
        "/api/member/courses",
        headers=auth_headers(token),
    ).json()["data"][0]
    action_token = create_pending_action_token(
        PendingAppointmentAction(
            action="reserve",
            member_id=1,
            course_id=course["id"],
            summary=f"预约课程：{course['name']}",
        )
    )
    install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "force_confirm",
                "confirm_pending_appointment_action",
            ),
            final_answer("缺少用户的明确确认，未执行预约。"),
        ],
    )
    response = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={
            "message": "继续",
            "history": [],
            "activeAgent": APPOINTMENT_AGENT,
            "pendingActionToken": action_token,
            "confirmationApproved": False,
        },
    ).json()

    assert response["code"] == 200
    assert client.get(
        "/api/member/appointments",
        headers=auth_headers(token),
    ).json()["data"] == []


def test_operations_agent_handoff_for_admin(client, monkeypatch):
    token = login(client, "admin")
    calls = install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "handoff_operations",
                "transfer_to_operations_agent",
                '{"reason":"管理员查看运营数据"}',
            ),
            final_answer("今日当前没有课程和预约数据。"),
        ],
    )
    response = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": "分析今天的课程和预约情况", "history": []},
    ).json()

    assert response["code"] == 200
    assert response["data"]["activeAgent"] == OPERATIONS_AGENT
    assert response["data"]["agentPath"] == [MAIN_AGENT, OPERATIONS_AGENT]
    assert "今日运营数据" in calls[1]["messages"][0]["content"]


def test_member_cannot_enter_operations_agent(client, monkeypatch):
    token = login(client, "zhangsan")
    install_completion_sequence(
        monkeypatch,
        [
            tool_call(
                "handoff_operations",
                "transfer_to_operations_agent",
                '{"reason":"测试越权"}',
            ),
            final_answer("运营数据仅管理员可查看。"),
        ],
    )
    response = client.post(
        "/api/agent/chat",
        headers=auth_headers(token),
        json={"message": "查看今日运营数据", "history": []},
    ).json()

    assert response["code"] == 200
    assert response["data"]["activeAgent"] == MAIN_AGENT
    assert response["data"]["agentPath"] == [MAIN_AGENT]


def test_change_and_cancel_appointment_transactions(client):
    token = login(client, "zhangsan")
    courses = client.get(
        "/api/member/courses",
        headers=auth_headers(token),
    ).json()["data"]
    old_course, new_course = courses[:2]
    profile = client.get(
        "/api/member/profile",
        headers=auth_headers(token),
    ).json()["data"]
    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(token),
        json={"courseId": old_course["id"]},
    ).json()["code"] == 200
    appointment = client.get(
        "/api/member/appointments",
        headers=auth_headers(token),
    ).json()["data"][0]

    with SessionLocal() as db:
        appointment_service.change_course(
            db,
            appointment["id"],
            profile["id"],
            new_course["id"],
        )
        db.commit()

    changed = client.get(
        "/api/member/appointments",
        headers=auth_headers(token),
    ).json()["data"]
    new_appointment = next(
        item for item in changed if item["courseId"] == new_course["id"]
    )
    assert new_appointment["status"] == "reserved"
    assert next(
        item for item in changed if item["id"] == appointment["id"]
    )["status"] == "canceled"

    canceled = client.put(
        f"/api/member/appointments/{new_appointment['id']}/cancel",
        headers=auth_headers(token),
    ).json()
    assert canceled["code"] == 200

    with SessionLocal() as db:
        operations = dashboard_service.get_today_operations(db)
    actions = [item["action"] for item in operations["appointmentActivity"]]
    assert actions.count("reserve") >= 1
    assert "change" in actions
    assert "cancel" in actions
    assert operations["todayChangeCount"] >= 1
    assert operations["activitySource"] == "appointment_log"
