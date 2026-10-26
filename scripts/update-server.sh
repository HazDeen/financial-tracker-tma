#!/usr/bin/env bash
# Run on the existing Linux server after git pull and uploading the signed APK.
set -euo pipefail
FINANCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FINANCE_APK="${1:-/home/hazdeen/moi-finansy-1.4.0.apk}"
cd "$FINANCE_ROOT"
for finance_command in node npm pm2 caddy systemctl python3 curl sha256sum; do
  command -v "$finance_command" >/dev/null || { echo "Required command missing: $finance_command" >&2; exit 1; }
done
if [ ! -f "$FINANCE_APK" ]; then
  echo "Upload moi-finansy-1.4.0.apk to $FINANCE_APK first, or pass its path as the first argument." >&2
  exit 1
fi
FINANCE_EXPECTED_SHA="$(awk 'NR == 1 {print $1}' android/SHA256SUMS-1.4.0.txt)"
FINANCE_ACTUAL_SHA="$(sha256sum "$FINANCE_APK" | awk '{print $1}')"
if [ "$FINANCE_ACTUAL_SHA" != "$FINANCE_EXPECTED_SHA" ]; then
  echo 'APK checksum mismatch. Upload the signed release APK 1.4.0 again.' >&2
  exit 1
fi
if [ -z "${DATABASE_URL:-}" ] && [ ! -f backend/.env ]; then
  echo 'backend/.env or DATABASE_URL is required: refusing to migrate a default database.' >&2
  exit 1
fi
if [ -z "${FINANCE_PYTHON:-}" ]; then
  for finance_candidate in "$FINANCE_ROOT/.venv/bin/python" "$FINANCE_ROOT/venv/bin/python" "$FINANCE_ROOT/backend/.venv/bin/python" "$FINANCE_ROOT/backend/venv/bin/python" "$(command -v python3)"; do
    if [ -x "$finance_candidate" ] && "$finance_candidate" -c 'import alembic, asyncpg, fastapi' >/dev/null 2>&1; then
      FINANCE_PYTHON="$finance_candidate"
      break
    fi
  done
fi
if [ -z "${FINANCE_PYTHON:-}" ]; then
  echo 'Backend Python environment not found. Set FINANCE_PYTHON to its Python executable.' >&2
  exit 1
fi
printf 'Applying database migrations using %s\n' "$FINANCE_PYTHON"
(cd backend && "$FINANCE_PYTHON" -m alembic upgrade head)
# Keep the APK in public so every future frontend build includes it.
install -m 644 "$FINANCE_APK" frontend/public/moi-finansy-1.4.0.apk
npm ci --prefix frontend
VITE_API_URL=/api/v1 npm run build --prefix frontend
pm2 restart smart-finance-api
if [ "$(id -u)" -eq 0 ]; then
  python3 scripts/configure-caddy.py
else
  sudo python3 scripts/configure-caddy.py
fi
curl --fail --silent --show-error https://finance.hazdeen.xyz/api | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"; print("/api: JSON response OK")'
curl --fail --silent --show-error https://finance.hazdeen.xyz/api/openapi.json | python3 -c 'import json,sys; assert "/api/v1/auth/login" in json.load(sys.stdin)["paths"]; print("API schema: OK")'
printf 'Updated. APK: https://finance.hazdeen.xyz/moi-finansy-1.4.0.apk\n'
