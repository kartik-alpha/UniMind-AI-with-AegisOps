from datetime import datetime, timedelta
from typing import Any, Union
import uuid
import jwt
import bcrypt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "jti": str(uuid.uuid4())}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decodes and validates a JWT access token supporting zero-downtime secret rotation.
    Tries active settings.SECRET_KEY first; falls back to settings.OLD_SECRET_KEYS.
    Also validates that the token has not been revoked.
    """
    try:
        from app.adapters.factory import AdapterFactory
        cache = AdapterFactory.get_cache()
        if cache.is_token_revoked(token):
            raise jwt.InvalidTokenError("Token has been revoked")
    except Exception as e:
        if isinstance(e, jwt.InvalidTokenError):
            raise

    keys_to_try = [settings.SECRET_KEY] + [k for k in getattr(settings, "OLD_SECRET_KEYS", []) if k]
    last_exc = None
    for key in keys_to_try:
        try:
            return jwt.decode(token, key, algorithms=[settings.ALGORITHM])
        except jwt.PyJWTError as e:
            last_exc = e
            continue
    raise last_exc or jwt.InvalidSignatureError("Signature verification failed")


def revoke_access_token(token: str, ttl_seconds: int = 86400) -> bool:
    from app.adapters.factory import AdapterFactory
    return AdapterFactory.get_cache().revoke_token(token, ttl_seconds=ttl_seconds)


def rotate_secret_key(new_secret_key: str) -> None:
    """
    Rotates the active platform JWT secret key with zero downtime.
    Retains the current secret key in OLD_SECRET_KEYS to preserve active user sessions.
    """
    if not new_secret_key or len(new_secret_key) < 16:
        raise ValueError("New secret key must be at least 16 characters long.")
    if settings.SECRET_KEY not in settings.OLD_SECRET_KEYS:
        settings.OLD_SECRET_KEYS.insert(0, settings.SECRET_KEY)
    settings.SECRET_KEY = new_secret_key
