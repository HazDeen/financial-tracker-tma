export function LoadingScreen({
  message = "Готовим ваши финансы",
}: {
  message?: string;
}) {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <div className="loading-brand">
        <span className="brand-symbol">₽</span>
      </div>
      <h1>
        Мои финансы<span className="brand-dot">.</span>
      </h1>
      <p>{message}</p>
      <span className="loading-line">
        <i />
      </span>
      <small>Всё важное — под рукой</small>
    </div>
  );
}
