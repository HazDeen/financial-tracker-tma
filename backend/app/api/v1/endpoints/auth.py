import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.core.auth import COOKIE_NAME, get_current_user_id, hash_password, verify_password, token_digest
from app.core.config import settings
from app.core.database import get_db
from app.models.auth import WebAccount, WebSession

router = APIRouter()


class Credentials(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("login", mode="before")
    @classmethod
    def normalize_login(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


async def start_session(db, account, response):
    token = secrets.token_urlsafe(48)
    await db.execute(delete(WebSession).where(WebSession.expires_at < datetime.utcnow()))
    db.add(WebSession(token_hash=token_digest(token), account_id=account.id,
                      expires_at=datetime.utcnow() + timedelta(days=30)))
    await db.commit()
    response.set_cookie(COOKIE_NAME, token, max_age=30 * 86400, httponly=True,
                        secure=settings.COOKIE_SECURE, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"id": -account.id, "login": account.login}


@router.post("/register", status_code=201)
async def register(schema: Credentials, response: Response, db: AsyncSession = Depends(get_db)):
    account = WebAccount(id=secrets.randbelow(2_000_000_000) + 1, login=schema.login,
                        password_hash=await run_in_threadpool(hash_password, schema.password))
    db.add(account)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Этот логин уже занят")
    return await start_session(db, account, response)


@router.post("/login")
async def login(schema: Credentials, response: Response, db: AsyncSession = Depends(get_db)):
    account = (await db.execute(select(WebAccount).where(WebAccount.login == schema.login))).scalar_one_or_none()
    # Проверка с той же стоимостью даже для неизвестного логина.
    stored = account.password_hash if account else DUMMY_HASH
    valid = await run_in_threadpool(verify_password, schema.password, stored)
    if not account or not valid:
        raise HTTPException(401, "Неверный логин или пароль")
    return await start_session(db, account, response)


@router.get("/me")
async def me(response: Response, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    account = await db.get(WebAccount, -user_id)
    response.headers["Cache-Control"] = "no-store"
    return {"id": user_id, "login": account.login}


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        await db.execute(delete(WebSession).where(WebSession.token_hash == token_digest(token)))
        await db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", secure=settings.COOKIE_SECURE, httponly=True, samesite="lax")


DUMMY_HASH = hash_password("unused-placeholder-password")
