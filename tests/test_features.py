from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Course
from app.services.appointment_service import expire_waitlist_offers
from app.services.attendance_service import mark_no_shows
from tests.conftest import login


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_member(
    client,
    admin_token: str,
    *,
    name: str,
    username: str,
    phone: str,
) -> None:
    result = client.post(
        "/api/admin/members",
        headers=auth_headers(admin_token),
        json={
            "member": {
                "name": name,
                "phone": phone,
                "gender": "男",
                "age": 28,
                "cardType": "年卡",
                "expireTime": "2027-12-31",
                "status": 1,
            },
            "username": username,
            "password": "123456",
        },
    ).json()
    assert result["code"] == 200


def first_course(client, token: str) -> dict:
    return client.get(
        "/api/member/courses",
        headers=auth_headers(token),
    ).json()["data"][0]


def test_expired_membership_blocks_reservation_until_renewal(client):
    admin_token = login(client, "admin")
    member_token = login(client, "zhangsan")
    course = first_course(client, member_token)
    with SessionLocal() as db:
        member_course = db.get(Course, course["id"])
        member_course.booked_count = 0
        db.commit()
    with SessionLocal() as db:
        from app.models import Member

        member = db.get(Member, 1)
        member.expire_time = date.today() - timedelta(days=1)
        db.commit()

    expired = client.post(
        "/api/member/appointments",
        headers=auth_headers(member_token),
        json={"courseId": course["id"]},
    ).json()
    assert expired["code"] == 400
    assert "过期" in expired["message"]

    renewed = client.put(
        "/api/admin/members/1/renew",
        headers=auth_headers(admin_token),
        json={"months": 1},
    ).json()
    assert renewed["code"] == 200
    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(member_token),
        json={"courseId": course["id"]},
    ).json()["code"] == 200


def test_waitlist_offer_and_confirmation_flow(client):
    admin_token = login(client, "admin")
    first_token = login(client, "zhangsan")
    create_member(
        client,
        admin_token,
        name="李四",
        username="lisi",
        phone="13900000000",
    )
    second_token = login(client, "lisi")
    course = first_course(client, first_token)
    with SessionLocal() as db:
        record = db.get(Course, course["id"])
        record.capacity = 1
        record.booked_count = 0
        db.commit()

    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(first_token),
        json={"courseId": course["id"]},
    ).json()["code"] == 200
    first_appointment = client.get(
        "/api/member/appointments",
        headers=auth_headers(first_token),
    ).json()["data"][0]

    waitlisted = client.post(
        "/api/member/appointments/waitlist",
        headers=auth_headers(second_token),
        json={"courseId": course["id"]},
    ).json()
    assert waitlisted["code"] == 200
    second_appointment = client.get(
        "/api/member/appointments",
        headers=auth_headers(second_token),
    ).json()["data"][0]
    assert second_appointment["status"] == "waitlisted"

    assert client.put(
        f"/api/member/appointments/{first_appointment['id']}/cancel",
        headers=auth_headers(first_token),
    ).json()["code"] == 200
    promoted = client.get(
        "/api/member/appointments",
        headers=auth_headers(second_token),
    ).json()["data"][0]
    assert promoted["status"] == "pending_confirmation"
    notifications = client.get(
        "/api/notifications",
        headers=auth_headers(second_token),
    ).json()["data"]
    assert notifications["unreadCount"] >= 1
    assert any(item["type"] == "waitlist_offer" for item in notifications["records"])

    confirmed = client.post(
        f"/api/member/appointments/{promoted['id']}/confirm-waitlist",
        headers=auth_headers(second_token),
    ).json()
    assert confirmed["code"] == 200
    final_appointment = client.get(
        "/api/member/appointments",
        headers=auth_headers(second_token),
    ).json()["data"][0]
    assert final_appointment["status"] == "reserved"


def test_expired_waitlist_offer_releases_capacity(client):
    admin_token = login(client, "admin")
    first_token = login(client, "zhangsan")
    create_member(
        client,
        admin_token,
        name="王五",
        username="wangwu",
        phone="13700000000",
    )
    second_token = login(client, "wangwu")
    course = first_course(client, first_token)
    with SessionLocal() as db:
        record = db.get(Course, course["id"])
        record.capacity = 1
        record.booked_count = 0
        db.commit()
    client.post(
        "/api/member/appointments",
        headers=auth_headers(first_token),
        json={"courseId": course["id"]},
    )
    first_appointment = client.get(
        "/api/member/appointments",
        headers=auth_headers(first_token),
    ).json()["data"][0]
    client.post(
        "/api/member/appointments/waitlist",
        headers=auth_headers(second_token),
        json={"courseId": course["id"]},
    )
    client.put(
        f"/api/member/appointments/{first_appointment['id']}/cancel",
        headers=auth_headers(first_token),
    )
    with SessionLocal() as db:
        from app.models import Appointment

        offer = db.scalar(
            select(Appointment).where(
                Appointment.course_id == course["id"],
                Appointment.status == "pending_confirmation",
            )
        )
        offer.update_time = datetime.now() - timedelta(minutes=20)
        db.commit()
        assert expire_waitlist_offers(db) == 1
        db.commit()
        record = db.get(Course, course["id"])
        assert record.booked_count == 0

    promoted = client.get(
        "/api/member/appointments",
        headers=auth_headers(second_token),
    ).json()["data"][0]
    assert promoted["status"] == "canceled"


def test_qr_checkin_and_operations_report(client):
    admin_token = login(client, "admin")
    member_token = login(client, "zhangsan")
    course = first_course(client, member_token)
    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(member_token),
        json={"courseId": course["id"]},
    ).json()["code"] == 200
    with SessionLocal() as db:
        record = db.get(Course, course["id"])
        record.start_time = datetime.now() - timedelta(minutes=5)
        record.end_time = datetime.now() + timedelta(minutes=55)
        db.commit()

    code = client.get(
        f"/api/admin/courses/{course['id']}/checkin-code",
        headers=auth_headers(admin_token),
    ).json()
    assert code["code"] == 200
    assert code["data"]["qrCode"].startswith("data:image/png;base64,")

    checked_in = client.post(
        "/api/member/appointments/check-in",
        headers=auth_headers(member_token),
        json={"token": code["data"]["token"]},
    ).json()
    assert checked_in["code"] == 200, checked_in
    assert checked_in["data"]["courseName"] == course["name"]

    report = client.get(
        "/api/admin/dashboard/daily-report",
        headers=auth_headers(admin_token),
    ).json()
    assert report["code"] == 200
    assert report["data"]["checkedInCount"] >= 1


def test_no_show_marking_creates_notification(client):
    member_token = login(client, "zhangsan")
    course = first_course(client, member_token)
    assert client.post(
        "/api/member/appointments",
        headers=auth_headers(member_token),
        json={"courseId": course["id"]},
    ).json()["code"] == 200
    with SessionLocal() as db:
        record = db.get(Course, course["id"])
        record.start_time = datetime.now() - timedelta(hours=3)
        record.end_time = datetime.now() - timedelta(hours=2)
        db.commit()
        marked = mark_no_shows(db)
        db.commit()
    assert marked >= 1

    appointments = client.get(
        "/api/member/appointments",
        headers=auth_headers(member_token),
    ).json()["data"]
    assert any(item["status"] == "no_show" for item in appointments)
    notifications = client.get(
        "/api/notifications",
        headers=auth_headers(member_token),
    ).json()["data"]
    assert any(item["type"] == "no_show" for item in notifications["records"])
