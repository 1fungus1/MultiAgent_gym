from datetime import datetime, timedelta

from tests.conftest import login


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_permissions_and_admin_queries(client):
    admin_token = login(client, "admin")
    member_token = login(client, "zhangsan")

    unauthorized = client.get("/api/admin/dashboard")
    assert unauthorized.json()["code"] == 401

    forbidden = client.get(
        "/api/admin/dashboard",
        headers=auth_headers(member_token),
    )
    assert forbidden.json()["code"] == 401

    dashboard = client.get(
        "/api/admin/dashboard",
        headers=auth_headers(admin_token),
    ).json()
    assert dashboard["code"] == 200
    assert dashboard["data"]["memberCount"] == 1
    assert dashboard["data"]["courseCount"] == 2

    members = client.get(
        "/api/admin/members/page?pageNum=1&pageSize=10&keyword=张三",
        headers=auth_headers(admin_token),
    ).json()
    assert members["code"] == 200
    assert members["data"]["total"] == 1
    assert members["data"]["records"][0]["username"] == "zhangsan"


def test_course_reservation_and_cancellation_flow(client):
    admin_token = login(client, "admin")
    member_token = login(client, "zhangsan")

    courses = client.get(
        "/api/member/courses",
        headers=auth_headers(member_token),
    ).json()
    assert courses["code"] == 200
    course = courses["data"][0]

    reserved = client.post(
        "/api/member/appointments",
        json={"courseId": course["id"]},
        headers=auth_headers(member_token),
    ).json()
    assert reserved["code"] == 200

    duplicate = client.post(
        "/api/member/appointments",
        json={"courseId": course["id"]},
        headers=auth_headers(member_token),
    ).json()
    assert duplicate["code"] == 400

    appointments = client.get(
        "/api/member/appointments",
        headers=auth_headers(member_token),
    ).json()
    appointment = appointments["data"][0]
    assert appointment["status"] == "reserved"
    assert appointment["courseEndTime"]
    assert appointment["updateTime"]

    canceled = client.put(
        f"/api/member/appointments/{appointment['id']}/cancel",
        headers=auth_headers(member_token),
    ).json()
    assert canceled["code"] == 200

    admin_courses = client.get(
        "/api/admin/courses",
        headers=auth_headers(admin_token),
    ).json()
    updated_course = next(item for item in admin_courses["data"] if item["id"] == course["id"])
    assert updated_course["bookedCount"] == 0


def test_create_member_and_course(client):
    admin_token = login(client, "admin")

    created_member = client.post(
        "/api/admin/members",
        headers=auth_headers(admin_token),
        json={
            "member": {
                "name": "李四",
                "phone": "13900000000",
                "gender": "男",
                "age": 30,
                "cardType": "季卡",
                "expireTime": "2027-12-31",
                "status": 1,
            },
            "username": "lisi",
            "password": "654321",
        },
    ).json()
    assert created_member["code"] == 200
    assert login(client, "lisi", "654321")

    start = (datetime.now() + timedelta(days=2)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    end = start.replace(hour=11)
    created_course = client.post(
        "/api/admin/courses",
        headers=auth_headers(admin_token),
        json={
            "name": "新建测试课程",
            "type": "力量",
            "coachId": 1,
            "startTime": start.strftime("%Y-%m-%d %H:%M"),
            "endTime": end.strftime("%Y-%m-%d %H:%M"),
            "capacity": 10,
            "bookedCount": 0,
            "status": 1,
        },
    ).json()
    assert created_course["code"] == 200

def test_profile_password_and_admin_appointment_cancel(client):
    admin_token = login(client, "admin")
    member_token = login(client, "zhangsan")

    profile = client.get(
        "/api/member/profile",
        headers=auth_headers(member_token),
    ).json()
    assert profile["code"] == 200
    member_id = profile["data"]["id"]

    updated_profile = client.put(
        "/api/member/profile",
        headers=auth_headers(member_token),
        json={"phone": "13811112222", "age": 23, "gender": "男"},
    ).json()
    assert updated_profile["code"] == 200

    wrong_password = client.put(
        "/api/member/profile/password",
        headers=auth_headers(member_token),
        json={"oldPassword": "wrong", "newPassword": "newpass"},
    ).json()
    assert wrong_password["code"] == 400

    changed_password = client.put(
        "/api/member/profile/password",
        headers=auth_headers(member_token),
        json={"oldPassword": "123456", "newPassword": "newpass"},
    ).json()
    assert changed_password["code"] == 200
    assert login(client, "zhangsan", "newpass")

    course = client.get(
        "/api/member/courses",
        headers=auth_headers(member_token),
    ).json()["data"][0]
    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(member_token),
        json={"courseId": course["id"]},
    ).json()["code"] == 200

    appointments = client.get(
        "/api/admin/appointments",
        headers=auth_headers(admin_token),
    ).json()["data"]
    appointment = next(
        item for item in appointments if item["memberId"] == member_id
    )
    canceled = client.put(
        f"/api/admin/appointments/{appointment['id']}/cancel",
        headers=auth_headers(admin_token),
    ).json()
    assert canceled["code"] == 200


def test_admin_member_coach_and_course_crud(client):
    admin_token = login(client, "admin")

    assert client.post(
        "/api/admin/coaches",
        headers=auth_headers(admin_token),
        json={
            "name": "测试教练",
            "phone": "13500000000",
            "specialty": "体态",
            "entryDate": "2026-01-01",
            "status": 1,
        },
    ).json()["code"] == 200
    coach_page = client.get(
        "/api/admin/coaches/page?pageNum=1&pageSize=10&keyword=测试",
        headers=auth_headers(admin_token),
    ).json()
    assert coach_page["data"]["total"] == 1
    coach_id = coach_page["data"]["records"][0]["id"]

    assert client.put(
        f"/api/admin/coaches/{coach_id}",
        headers=auth_headers(admin_token),
        json={"name": "更新教练", "status": 1},
    ).json()["code"] == 200

    start = (datetime.now() + timedelta(days=3)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    created_course = client.post(
        "/api/admin/courses",
        headers=auth_headers(admin_token),
        json={
            "name": "CRUD 测试课程",
            "type": "测试",
            "coachId": coach_id,
            "startTime": start.strftime("%Y-%m-%d %H:%M"),
            "endTime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
            "capacity": 12,
            "bookedCount": 0,
            "status": 1,
        },
    ).json()
    assert created_course["code"] == 200

    course_page = client.get(
        "/api/admin/courses/page?pageNum=1&pageSize=10&keyword=CRUD",
        headers=auth_headers(admin_token),
    ).json()
    course = course_page["data"]["records"][0]
    assert client.put(
        f"/api/admin/courses/{course['id']}",
        headers=auth_headers(admin_token),
        json={"name": "CRUD 测试课程已更新", "capacity": 15},
    ).json()["code"] == 200
    assert client.delete(
        f"/api/admin/courses/{course['id']}",
        headers=auth_headers(admin_token),
    ).json()["code"] == 200
    assert client.delete(
        f"/api/admin/coaches/{coach_id}",
        headers=auth_headers(admin_token),
    ).json()["code"] == 200

    assert client.post(
        "/api/admin/members",
        headers=auth_headers(admin_token),
        json={
            "member": {
                "name": "待删除会员",
                "phone": "13700000000",
                "gender": "女",
                "age": 26,
                "cardType": "月卡",
                "expireTime": "2027-05-01",
                "status": 1,
            },
            "username": "delete_me",
            "password": "abcdef",
        },
    ).json()["code"] == 200
    member_page = client.get(
        "/api/admin/members/page?pageNum=1&pageSize=10&keyword=待删除会员",
        headers=auth_headers(admin_token),
    ).json()
    member = member_page["data"]["records"][0]

    assert client.put(
        f"/api/admin/members/{member['id']}",
        headers=auth_headers(admin_token),
        json={
            "member": {"name": "待删除会员", "status": 1},
            "username": "delete_me",
            "password": "",
        },
    ).json()["code"] == 200
    assert login(client, "delete_me", "abcdef")
    assert client.delete(
        f"/api/admin/members/{member['id']}",
        headers=auth_headers(admin_token),
    ).json()["code"] == 200
