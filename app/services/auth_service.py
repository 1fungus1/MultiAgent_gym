from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessException
from app.core.security import hash_password, needs_password_rehash, verify_password
from app.models import SysUser
from app.schemas import LoginRequest


def login_user(db: Session, request: LoginRequest) -> SysUser:
    user = db.scalar(select(SysUser).where(SysUser.username == request.username))
    if user is None:
        raise BusinessException("用户不存在")
    if not verify_password(request.password, user.password):
        raise BusinessException("密码错误")
    if user.status != 1:
        raise BusinessException("用户被禁用")

    if needs_password_rehash(user.password, request.password):
        user.password = hash_password(request.password)
        db.flush()
    return user

