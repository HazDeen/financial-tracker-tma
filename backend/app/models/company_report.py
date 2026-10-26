from datetime import datetime
from sqlalchemy import DateTime, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class CompanyReport(Base):
    __tablename__ = "company_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    company: Mapped[str] = mapped_column(String(160))
    period: Mapped[str] = mapped_column(String(80))
    filename: Mapped[str] = mapped_column(String(200))
    size: Mapped[int]
    metrics: Mapped[dict] = mapped_column(JSON)
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
