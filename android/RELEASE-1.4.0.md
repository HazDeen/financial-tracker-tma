# Мои финансы 1.4.0

APK: `moi-finansy-1.4.0.apk`, versionCode 5, Android 8.0+. Подписан прежним ключом, устанавливается поверх версии 1.3.0.

Единый логотип: синяя иконка личного бюджета с белым контуром и мятной линией движения денег. Заменены favicon Vite, значки сайта и экраны загрузки, нативный экран запуска Android и иконка приложения. Добавлены адаптивная и монохромная иконки Android, иконка закладки iPhone. Кнопка скачивания и QR-код на сайте ведут на APK 1.4.0.

## Обновление сервера

1. Загрузите APK в `/home/hazdeen/moi-finansy-1.4.0.apk`.
2. Скопируйте его в оба каталога:

```sh
sudo install -m 644 /home/hazdeen/moi-finansy-1.4.0.apk /var/www/smart-finance/frontend/public/
sudo install -m 644 /home/hazdeen/moi-finansy-1.4.0.apk /var/www/smart-finance/frontend/dist/
```

3. Обновите исходники и выполните `npm run build` в `frontend`, либо распакуйте `frontend-1.4.0.zip` в корень проекта. Готовая веб-сборка находится внутри `frontend/dist/`. APK в `frontend/public/` сохраняет скачивание при следующих веб-сборках.
4. Обновите страницу сайта. Иконки браузера имеют новую версию адреса, чтобы сбросить старый значок Vite.

Прямая ссылка: https://finance.hazdeen.xyz/moi-finansy-1.4.0.apk

Этот релиз не меняет серверные API. При обновлении с версии до 1.3.0 сначала примените инструкции и миграции из `RELEASE-1.3.0.md`.

Логотип редактируется в `branding/mark.json`. Команда `python3 scripts/generate-branding.py` обновляет SVG и Android VectorDrawable; PNG для Apple и старых браузеров экспортируются из `branding/logo.svg` в размерах 180×180 и 32×32.

Сборка и подпись проверяются Android SDK. На физическом телефоне APK в этой сессии не запускался.
