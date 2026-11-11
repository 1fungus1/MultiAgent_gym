from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import BusinessException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.schemas import CurrentUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise BusinessException("请先登录", 401)
    return decode_access_token(credentials.credentials)


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "admin":
        raise BusinessException("需要管理员权限", 401)
    return user


def require_member(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != "member":
        raise BusinessException("需要会员权限", 401)
    return user


Database = get_db
