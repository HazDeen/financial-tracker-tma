import { useState } from 'react';
import { AuthService, errorMessage } from '../api/client';
import { RecoveryCode } from './RecoveryCode';

export function RecoverySettings() {
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return <section className="panel">
    <div className="section-heading"><div><h2>Восстановление пароля</h2><p>Подготовьте резервный код на случай потери пароля</p></div></div>
    <form className="entry-form" onSubmit={async event => {
      event.preventDefault(); setBusy(true); setError('');
      try { setCode((await AuthService.recoveryCode(password)).recovery_code); setPassword(''); }
      catch (err) { setError(errorMessage(err)); }
      finally { setBusy(false); }
    }}>
      <label>Текущий пароль<input type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={event => setPassword(event.target.value)} /></label>
      <p className="field-hint">Новый код заменит предыдущий. Сохраните его перед выходом из аккаунта.</p>
      <button className="button primary" disabled={busy}>{busy ? 'Создаём код…' : 'Создать резервный код'}</button>
      {error && <p role="alert" className="alert">{error}</p>}
    </form>
    {code && <RecoveryCode code={code} />}
  </section>;
}
