import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.exceptions import BusinessException
from app.schemas import CurrentUser

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def _is_md5_hash(value: str) -> bool:
    return len(value) == 32 and all(character in "0123456789abcdefABCDEF" for character in value)


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False

    if stored_hash.startswith(("$argon2", "$scrypt", "$pbkdf2")):
        try:
            return password_hash.verify(password, stored_hash)
        except Exception:
            return False

    if _is_md5_hash(stored_hash):
        legacy_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, stored_hash.lower())

    if settings.allow_legacy_plaintext_passwords:
        return hmac.compare_digest(password, stored_hash)
    return False


def needs_password_rehash(stored_hash: str, password: str) -> bool:
    if stored_hash.startswith("$argon2"):
        try:
            return password_hash.verify_and_update(password, stored_hash)[1] is not None
        except Exception:
            return True
    return True


def create_access_token(user: CurrentUser) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user.username,
        "userId": user.user_id,
        "username": user.username,
        "role": user.role,
        "relatedId": user.related_id,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> CurrentUser:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return CurrentUser(
            user_id=int(payload["userId"]),
            username=str(payload["username"]),
            role=str(payload["role"]),
            related_id=(
                int(payload["relatedId"]) if payload.get("relatedId") is not None else None
            ),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exception:
        raise BusinessException("登录已失效", 401) from exception

