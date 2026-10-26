export function RecoveryCode({ code }: { code: string }) {
  return <div className="recovery-code" role="status">
    <h3>Сохраните код восстановления</h3>
    <p>Он понадобится, если вы забудете пароль. Храните его в менеджере паролей или другом надёжном месте. Код даёт доступ к аккаунту — не передавайте его другим.</p>
    <code>{code}</code>
    <a className="text-button" download="finance-recovery-code.txt" href={`data:text/plain;charset=utf-8,${encodeURIComponent('Мои финансы — код восстановления\n' + code + '\nКод одноразовый. Не передавайте его другим.')}`}>Скачать код</a>
    <p>Предыдущий код больше не действует. Этот код показывается только сейчас.</p>
  </div>;
}
