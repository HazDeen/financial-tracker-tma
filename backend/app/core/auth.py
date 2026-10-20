import hashlib
import secrets
from datetime import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.auth import WebSession

COOKIE_NAME = "finance_session"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return secrets.compare_digest(candidate, digest)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user_id(request: Request, db: AsyncSession = Depends(get_db)) -> int:
    token = request.cookies.get(COOKIE_NAME)
    session = await db.get(WebSession, token_digest(token)) if token else None
    if session is None or session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Войдите в аккаунт")
    # Отдельное пространство ID не смешивает веб-аккаунты с Telegram.
    return -session.account_id
