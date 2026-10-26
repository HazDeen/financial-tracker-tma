import { Download } from 'lucide-react';
import { BrandMark } from './BrandMark';

const APK_URL = 'https://finance.hazdeen.xyz/moi-finansy-1.4.0.apk';
const QR_URL = `${import.meta.env.BASE_URL}android-download-qr.svg`;

export function AndroidDownload() {
  // The installed Android app already contains the interface.
  if (import.meta.env.BASE_URL === '/__android__/') return null;

  return (
    <section className="android-download" aria-label="Скачать приложение для Android">
      <div className="android-download-copy">
        <span className="android-download-label"><BrandMark /> Мои финансы на Android</span>
        <h2>Финансы всегда под рукой</h2>
        <p>Сканируйте QR-код камерой телефона или скачайте приложение прямо здесь.</p>
        <a className="button primary android-download-button" href={APK_URL} download="moi-finansy-1.4.0.apk">
          <Download size={17} aria-hidden="true" /> Скачать APK
        </a>
        <small>Версия 1.4.0 · Android 8.0 и новее</small>
        <details className="android-download-help">
          <summary>Как установить?</summary>
          <p>Откройте скачанный APK на телефоне. Если Android попросит, разрешите установку из выбранного браузера. Затем войдите в свой аккаунт — ваши данные общие с сайтом.</p>
        </details>
      </div>
      <figure className="android-download-qr">
        <a href={APK_URL} aria-label="Скачать APK 1.4.0 для Android">
          <img src={QR_URL} width="144" height="144" alt="QR-код для скачивания приложения Мои финансы для Android" />
        </a>
        <figcaption>Наведите камеру телефона</figcaption>
      </figure>
    </section>
  );
}
