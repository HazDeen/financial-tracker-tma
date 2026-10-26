# Мои финансы — веб-интерфейс

React, TypeScript и Vite. Из корня проекта `./start.sh` собирает интерфейс и запускает приложение на http://127.0.0.1:8000.

Для разработки: `npm install`, затем `npm run dev` из этого каталога; API проксируется на `127.0.0.1:8000`. Production-сборка: `npm run build`. Проверка кода: `npm run lint`.

Единый логотип подключается компонентом `BrandMark` из `public/brand-mark.svg`. Значок вкладки, закладки iPhone и Android-иконки используют тот же оригинал `../branding/mark.json`; генерация — `python3 scripts/generate-branding.py` из корня проекта. Подробности: `../branding/README.md`.

Ссылка на APK и QR-код находятся в `AndroidDownload` и `public/android-download-qr.svg`. При смене версии их нужно обновлять вместе. APK хранится на production-сервере в `public/` и при веб-сборке копируется в `dist/`.
