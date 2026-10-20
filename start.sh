#!/usr/bin/env bash
set -euo pipefail
FINANCE_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$FINANCE_ROOT"
if [ ! -x .venv/bin/python ]; then
  "${FINANCE_PYTHON:-python3}" -m venv .venv
fi
if ! .venv/bin/python -c 'import fastapi, aiosqlite, asyncpg, multipart, pdfplumber, pandas, google.genai' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  npm ci --prefix frontend
fi
# Один источник для сайта и API: cookie работает без настройки доменов.
VITE_API_URL=/api/v1 npm run build --prefix frontend
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///$FINANCE_ROOT/backend/web-finance.db}"
cd backend
exec ../.venv/bin/python -m uvicorn main:app --host "${FINANCE_HOST:-127.0.0.1}" --port "${PORT:-8000}"
