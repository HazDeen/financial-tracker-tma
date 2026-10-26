"""Private report attachments and user-entered financial figures; no automatic extraction."""
import json
from decimal import Decimal
from io import BytesIO
from pathlib import PurePosixPath
from typing import Optional
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.models.company_report import CompanyReport

router = APIRouter()
MAX_SIZE = 10 * 1024 * 1024


class Figures(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    marketCap: Optional[Decimal] = Field(None, ge=0, le=10**15)
    netIncome: Optional[Decimal] = Field(None, ge=-10**15, le=10**15)
    revenue: Optional[Decimal] = Field(None, ge=0, le=10**15)
    equity: Optional[Decimal] = Field(None, ge=-10**15, le=10**15)
    averageEquity: Optional[Decimal] = Field(None, ge=-10**15, le=10**15)
    debt: Optional[Decimal] = Field(None, ge=0, le=10**15)
    cash: Optional[Decimal] = Field(None, ge=0, le=10**15)
    ebitda: Optional[Decimal] = Field(None, ge=-10**15, le=10**15)


def summary(report):
    return {key: getattr(report, key) for key in
            ("id", "company", "period", "filename", "size", "metrics", "created_at")}


@router.get("")
async def list_reports(user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    reports = (await db.scalars(select(CompanyReport).where(CompanyReport.user_id == user_id)
                               .order_by(CompanyReport.id.desc()))).all()
    return [summary(report) for report in reports]


@router.post("", status_code=201)
async def upload_report(
    company: str = Form(..., min_length=1, max_length=160),
    period: str = Form(..., min_length=1, max_length=80),
    metrics: str = Form("{}", max_length=4000),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db),
):
    company, period = company.strip(), period.strip()
    if not company or not period:
        raise HTTPException(422, "Укажите компанию и период отчёта")
    try:
        figures = Figures.model_validate(json.loads(metrics))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Проверьте финансовые показатели")
    filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
    if not filename or len(filename) > 200 or any(ord(c) < 32 for c in filename):
        raise HTTPException(422, "Некорректное имя файла")
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".pdf", ".xlsx", ".csv"}:
        raise HTTPException(422, "Выберите PDF, XLSX или CSV")
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "Размер отчёта — не больше 10 МБ")
    if not content:
        raise HTTPException(422, "Файл пуст")
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Файл не похож на PDF")
    if suffix == ".xlsx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(archive.namelist()):
                    raise BadZipFile()
        except BadZipFile:
            raise HTTPException(422, "Файл не похож на XLSX")
    if suffix == ".csv" and b"\x00" in content:
        raise HTTPException(422, "Выберите текстовый CSV")
    count = await db.scalar(select(func.count()).select_from(CompanyReport).where(CompanyReport.user_id == user_id))
    if count >= 20:
        raise HTTPException(409, "Можно сохранить 20 отчётов. Удалите ненужные файлы.")
    report = CompanyReport(user_id=user_id, company=company, period=period, filename=filename,
                           size=len(content), metrics=figures.model_dump(mode="json"), content=content)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return summary(report)


async def owned_report(report_id, user_id, db, with_content=False):
    query = select(CompanyReport).where(CompanyReport.id == report_id, CompanyReport.user_id == user_id)
    if with_content:
        query = query.options(undefer(CompanyReport.content))
    report = await db.scalar(query)
    if report is None:
        raise HTTPException(404, "Отчёт не найден")
    return report


@router.get("/{report_id}/file")
async def download_report(report_id: int, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    report = await owned_report(report_id, user_id, db, with_content=True)
    return Response(report.content, media_type="application/octet-stream", headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(report.filename, safe=""),
        "X-Content-Type-Options": "nosniff",
    })


@router.delete("/{report_id}", status_code=204)
async def delete_report(report_id: int, user_id: int = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    report = await owned_report(report_id, user_id, db)
    await db.delete(report)
    await db.commit()
