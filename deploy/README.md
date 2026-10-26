# Обновление finance.hazdeen.xyz

Frontend обслуживается по `/`. Все адреса `/api` и `/api/*` передаются backend на `127.0.0.1:8003` с сохранением префикса. `/api` и `/api/` возвращают JSON, методы приложения расположены под `/api/v1`, документация — `/api/docs`, схема — `/api/openapi.json`. Веб-интерфейс не должен возвращаться для API-маршрутов.

`handle /api/*` не захватывает точный путь `/api`: без отдельного совпадения он попадает в SPA fallback. Исправление: именованный matcher `@api path /api /api/*` из `finance.Caddyfile`.

## Полное обновление сайта, API и APK

Сначала загрузите подписанный `moi-finansy-1.4.0.apk` в `/home/hazdeen/` через SFTP. Затем на сервере:

```sh
cd /var/www/smart-finance
git pull --ff-only
bash scripts/update-server.sh /home/hazdeen/moi-finansy-1.4.0.apk
```

Скрипт проверяет контрольную сумму APK, находит Python-окружение backend, применяет миграции (включая `finance_profiles` и `web_recovery_codes`), копирует APK в `frontend/public/`, собирает frontend с `/api/v1`, перезапускает `smart-finance-api`, исправляет конфигурацию Caddy и проверяет ответы API. База берётся из существующего `backend/.env` или переменной `DATABASE_URL`; используйте те же настройки, с которыми запущен backend. Если Python находится в другом каталоге, передайте его явно:

```sh
FINANCE_PYTHON=/полный/путь/к/python bash scripts/update-server.sh /home/hazdeen/moi-finansy-1.4.0.apk
```

Все Caddy-сайты, кроме `finance.hazdeen.xyz`, сохраняются. Перед заменой конфигурация проверяется через `caddy validate`; резервная копия хранится в `/var/backups/smart-finance/`. Если перезагрузка конфигурации не удаётся, скрипт возвращает предыдущий файл.

Для применения только маршрутизации Caddy:

```sh
sudo python3 scripts/configure-caddy.py
```

Эта команда предполагает, что backend уже обновлён и перезапущен. Посмотреть полный результат без применения: `python3 scripts/configure-caddy.py --dry-run`.


После перезапуска backend скрипт ждёт его готовности до 60 секунд, прежде чем менять Caddy. Затем повторяет проверку через публичный HTTPS-домен. Временные ошибки подключения и HTTP 502/503/504 повторяются; другие ошибки сообщаются сразу, без попытки разобрать HTML как JSON. Проверить сайт отдельно без обновления: `python3 scripts/check-server.py`.
