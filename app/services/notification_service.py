from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Member, Notification, SysUser
from app.schemas import NotificationListVO, NotificationVO


def create_notification(
    db: Session,
    *,
    user_id: int,
    type: str,
    title: str,
    content: str,
    member_id: int | None = None,
    related_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        member_id=member_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
        is_read=False,
    )
    db.add(notification)
    return notification


def notify_member(
    db: Session,
    *,
    member_id: int,
    type: str,
    title: str,
    content: str,
    related_id: int | None = None,
) -> Notification | None:
    user = db.scalar(
        select(SysUser).where(
            SysUser.related_id == member_id,
            SysUser.role == "member",
        )
    )
    if user is None:
        return None
    return create_notification(
        db,
        user_id=user.id,
        member_id=member_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
    )


def list_notifications(db: Session, user_id: int, limit: int = 30) -> NotificationListVO:
    rows = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.create_time.desc())
            .limit(min(max(limit, 1), 100))
        ).all()
    )
    unread_count = int(
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )
    return NotificationListVO(
        unread_count=unread_count,
        records=[NotificationVO.model_validate(row) for row in rows],
    )


def mark_read(db: Session, user_id: int, notification_id: int) -> None:
    db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        .values(is_read=True)
    )


def mark_all_read(db: Session, user_id: int) -> None:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user_id)
        .values(is_read=True)
    )


def notify_expiring_memberships(db: Session, today: date | None = None) -> int:
    current_date = today or date.today()
    deadline = current_date + timedelta(days=7)
    day_start = datetime.combine(current_date, time.min)
    members = list(
        db.scalars(
            select(Member).where(
                Member.status == 1,
                Member.expire_time <= deadline,
            )
        ).all()
    )
    created = 0
    for member in members:
        user = db.scalar(
            select(SysUser).where(
                SysUser.related_id == member.id,
                SysUser.role == "member",
            )
        )
        if user is None:
            continue
        existing = db.scalar(
            select(Notification.id).where(
                Notification.user_id == user.id,
                Notification.type == "membership_expiry",
                Notification.member_id == member.id,
                Notification.create_time >= day_start,
            )
        )
        if existing is not None:
            continue
        if member.expire_time and member.expire_time < current_date:
            title = "会员卡已过期"
            content = "您的会员卡已过期，续费后才能预约新课程。"
        else:
            title = "会员卡即将到期"
            content = f"您的会员卡将于 {member.expire_time} 到期，请及时续费。"
        create_notification(
            db,
            user_id=user.id,
            member_id=member.id,
            type="membership_expiry",
            title=title,
            content=content,
            related_id=member.id,
        )
        created += 1
    return created

