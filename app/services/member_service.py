from datetime import date, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.security import hash_password, verify_password
from app.models import Appointment, Course, Member, SysUser
from app.schemas import (
    AdminMemberRequest,
    AdminMemberVO,
    MemberPayload,
    MemberVO,
    PageResult,
    PasswordRequest,
    ProfileUpdate,
)
from app.services.notification_service import notify_member


def _member_vo(member: Member, username: str | None = None) -> AdminMemberVO:
    return AdminMemberVO(
        id=member.id,
        name=member.name,
        phone=member.phone,
        gender=member.gender,
        age=member.age,
        card_type=member.card_type,
        expire_time=member.expire_time,
        status=member.status,
        username=username,
    )


def _member_query():
    return select(Member, SysUser.username).outerjoin(
        SysUser,
        (SysUser.related_id == Member.id) & (SysUser.role == "member"),
    )


def _member_filters(keyword: str):
    if not keyword:
        return []
    pattern = f"%{keyword}%"
    return [
        or_(
            Member.name.like(pattern),
            Member.phone.like(pattern),
            SysUser.username.like(pattern),
        )
    ]


def list_members(db: Session) -> list[AdminMemberVO]:
    statement = _member_query().order_by(Member.id.desc())
    return [_member_vo(member, username) for member, username in db.execute(statement).all()]


def page_members(
    db: Session, page_num: int, page_size: int, keyword: str | None
) -> PageResult[AdminMemberVO]:
    current = max(page_num, 1)
    size = min(max(page_size, 1), 100)
    search_text = (keyword or "").strip()
    filters = _member_filters(search_text)

    statement = _member_query().order_by(Member.id.desc())
    count_statement = (
        select(func.count(func.distinct(Member.id)))
        .select_from(Member)
        .outerjoin(
            SysUser,
            (SysUser.related_id == Member.id) & (SysUser.role == "member"),
        )
    )
    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = int(db.scalar(count_statement) or 0)
    rows = db.execute(statement.offset((current - 1) * size).limit(size)).all()
    return PageResult(
        records=[_member_vo(member, username) for member, username in rows],
        total=total,
        page_num=current,
        page_size=size,
    )


def _validate_member_payload(member: MemberPayload, username: str, password: str) -> None:
    if not member.name:
        raise BusinessException("会员姓名不能为空")
    if not member.phone:
        raise BusinessException("会员手机号不能为空")
    if not member.gender:
        raise BusinessException("会员性别不能为空")
    if member.age is None or member.age < 0:
        raise BusinessException("会员年龄不能为空")
    if not member.card_type:
        raise BusinessException("会员卡类型不能为空")
    if member.expire_time is None:
        raise BusinessException("会员到期时间不能为空")
    if not username:
        raise BusinessException("会员登录账号不能为空")
    if not password:
        raise BusinessException("会员登录密码不能为空")


def create_member(db: Session, request: AdminMemberRequest) -> None:
    payload = request.member
    if payload is None:
        raise BusinessException("会员信息不能为空")
    username = (request.username or "").strip()
    password = request.password or ""
    _validate_member_payload(payload, username, password)

    if db.scalar(select(SysUser.id).where(SysUser.username == username)) is not None:
        raise BusinessException("会员登录账号已存在")

    member = Member(
        name=payload.name,
        phone=payload.phone,
        gender=payload.gender,
        age=payload.age,
        card_type=payload.card_type,
        expire_time=payload.expire_time,
        status=payload.status if payload.status is not None else 1,
    )
    db.add(member)
    db.flush()
    db.add(
        SysUser(
            username=username,
            password=hash_password(password),
            role="member",
            related_id=member.id,
            status=member.status,
        )
    )
    db.flush()


def update_member(db: Session, member_id: int, request: AdminMemberRequest) -> None:
    member = db.get(Member, member_id)
    if member is None:
        raise BusinessException("会员不存在")

    payload = request.member
    if payload is not None:
        changes = payload.model_dump(exclude_unset=True, exclude={"id"})
        for field, value in changes.items():
            if value is not None or field in {"phone", "gender", "age"}:
                setattr(member, field, value)
        if member.name is None or member.name == "":
            raise BusinessException("会员姓名不能为空")
        if member.age is not None and member.age < 0:
            raise BusinessException("会员年龄不能小于0")

    user = db.scalar(
        select(SysUser).where(
            SysUser.related_id == member_id,
            SysUser.role == "member",
        )
    )
    username = (request.username or "").strip()
    password = request.password or ""

    if username:
        duplicate = db.scalar(
            select(SysUser.id).where(
                SysUser.username == username,
                SysUser.id != (user.id if user else 0),
            )
        )
        if duplicate is not None:
            raise BusinessException("会员登录账号已存在")

    if user is None:
        if username or password:
            if not username or not password:
                raise BusinessException("创建会员账号需要同时填写账号和密码")
            db.add(
                SysUser(
                    username=username,
                    password=hash_password(password),
                    role="member",
                    related_id=member.id,
                    status=member.status,
                )
            )
    else:
        if username:
            user.username = username
        if password:
            user.password = hash_password(password)
        user.status = member.status

    db.flush()


def delete_member(db: Session, member_id: int) -> None:
    member = db.get(Member, member_id)
    if member is None:
        raise BusinessException("会员不存在")

    appointments = db.scalars(
        select(Appointment)
        .where(Appointment.member_id == member_id)
        .with_for_update()
    ).all()
    for appointment in appointments:
        if appointment.status != "reserved":
            continue
        course = db.scalar(
            select(Course).where(Course.id == appointment.course_id).with_for_update()
        )
        if course and course.booked_count > 0:
            course.booked_count -= 1

    db.execute(delete(Appointment).where(Appointment.member_id == member_id))
    db.execute(
        delete(SysUser).where(
            SysUser.related_id == member_id,
            SysUser.role == "member",
        )
    )
    db.delete(member)
    db.flush()


def _require_member(db: Session, related_id: int | None) -> Member:
    if related_id is None:
        raise BusinessException("当前账号未关联会员信息")
    member = db.get(Member, related_id)
    if member is None:
        raise BusinessException("会员不存在")
    return member


def get_profile(db: Session, related_id: int | None) -> MemberVO:
    member = _require_member(db, related_id)
    return MemberVO.model_validate(member)


def update_profile(db: Session, related_id: int | None, payload: ProfileUpdate) -> None:
    member = _require_member(db, related_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if field == "age" and value is not None and value < 0:
            raise BusinessException("会员年龄不能小于0")
        setattr(member, field, value)
    db.flush()


def update_password(
    db: Session,
    user_id: int,
    request: PasswordRequest,
) -> None:
    user = db.get(SysUser, user_id)
    if user is None:
        raise BusinessException("用户不存在")
    if not request.old_password:
        raise BusinessException("请输入旧密码")
    if not request.new_password:
        raise BusinessException("请输入新密码")
    if not verify_password(request.old_password, user.password):
        raise BusinessException("旧密码错误")
    if request.new_password == request.old_password:
        raise BusinessException("新密码不能与旧密码相同")

    user.password = hash_password(request.new_password)
    user.update_time = datetime.now()
    db.flush()


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    days_in_month = (
        date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
        - date(year, month, 1)
    ).days
    return date(year, month, min(value.day, days_in_month))


def renew_membership(db: Session, member_id: int, months: int) -> None:
    member = db.get(Member, member_id)
    if member is None:
        raise BusinessException("会员不存在")
    base_date = max(member.expire_time or date.today(), date.today())
    new_expire_time = _add_months(base_date, months)
    member.expire_time = new_expire_time
    member.status = 1
    notify_member(
        db,
        member_id=member.id,
        type="membership_renewed",
        title="会员续费成功",
        content=f"会员卡已续费 {months} 个月，有效期至 {new_expire_time}。",
        related_id=member.id,
    )
    db.flush()
