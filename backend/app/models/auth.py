from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class WebAccount(Base):
    __tablename__ = "web_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebSession(Base):
    __tablename__ = "web_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("web_accounts.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class WebRecoveryCode(Base):
    __tablename__ = "web_recovery_codes"
    account_id: Mapped[int] = mapped_column(ForeignKey("web_accounts.id"), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64))
