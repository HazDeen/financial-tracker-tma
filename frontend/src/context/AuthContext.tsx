import { RecoveryCode } from '../components/RecoveryCode';
import { LoadingScreen } from '../components/LoadingScreen';
import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { AuthService, errorMessage, setCurrentAccount } from '../api/client';
import type { Account } from '../api/client';

const AuthContext = createContext<{ account: Account | null; logout: () => Promise<void> }>({ account: null, logout: async () => {} });
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [checking, setChecking] = useState(true);
  const [connectionError, setConnectionError] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [register, setRegister] = useState(false);
  const [recover, setRecover] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const [pendingAccount, setPendingAccount] = useState<(Account & { recovery_code: string }) | null>(null);
  const [saved, setSaved] = useState(false);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const update = (value: Account | null) => { setCurrentAccount(value); setAccount(value); };
  const check = async () => {
    setChecking(true); setConnectionError('');
    try { update(await AuthService.me()); }
    catch (err: any) { if (err.response?.status !== 401) setConnectionError(errorMessage(err)); }
    finally { setChecking(false); }
  };
  useEffect(() => {
    void check();
    const expired = () => { update(null); setError('Сессия истекла. Войдите снова.'); };
    window.addEventListener('session-expired', expired);
    return () => window.removeEventListener('session-expired', expired);
  }, []);
  const logout = async () => {
    try { await AuthService.logout(); update(null); setPassword(''); }
    catch (err) { setConnectionError(errorMessage(err)); }
  };
  if (checking) return <LoadingScreen message="Открываем ваше приложение" />;
  if (pendingAccount) return <main className="auth-shell"><section className="auth-panel">
    <h2>{recover ? 'Пароль восстановлен' : 'Аккаунт создан'}</h2>
    <RecoveryCode code={pendingAccount.recovery_code} />
    <label><input type="checkbox" checked={saved} onChange={event => setSaved(event.target.checked)} /> Я сохранил код восстановления</label>
    <button className="auth-submit" disabled={!saved} onClick={() => { update({ id: pendingAccount.id, login: pendingAccount.login }); setPendingAccount(null); setSaved(false); setRecover(false); setRecoveryCode(''); }}>Продолжить →</button>
  </section></main>;
  if (account) return <AuthContext.Provider value={{ account, logout }}>
    {connectionError && <div role="alert" className="auth-error">{connectionError}</div>}{children}
  </AuthContext.Provider>;
  return <main className="auth-shell">
    <section className="auth-intro" aria-label="Мои финансы">
      <div className="auth-brand"><span className="brand-symbol">₽</span> Мои финансы</div>
      <p className="auth-eyebrow">ЛИЧНЫЕ ФИНАНСЫ</p>
      <h1>Доходы и расходы.<br /><span>Всё под рукой.</span></h1>
      <p className="auth-description">Доходы, повседневные траты и обязательства — в одном месте. Добавляйте операции вручную или загружайте банковскую выписку.</p>
      <div className="auth-features"><span>01 <b>Учитывайте расходы</b></span><span>02 <b>Импортируйте выписки</b></span><span>03 <b>Следите за балансом</b></span></div>
      <p className="auth-banks">Альфа-Банк · Т-Банк · СберБанк</p>
    </section>
    <section className="auth-panel">
      <div className="auth-tabs" aria-label="Способ входа">
        <button type="button" aria-pressed={!register} onClick={() => { setRegister(false); setRecover(false); setPassword(''); setConfirmation(''); setError(''); }}>Вход</button>
        <button type="button" aria-pressed={register} onClick={() => { setRegister(true); setRecover(false); setPassword(''); setConfirmation(''); setError(''); }}>Регистрация</button>
      </div>
      <h2>{recover ? 'Восстановить пароль' : register ? 'Создать аккаунт' : 'Вход в приложение'}</h2>
      <p>{recover ? 'Введите логин, сохранённый резервный код и новый пароль. Если код не был сохранён, восстановить доступ этим способом не получится.' : register ? 'Начните вести свой финансовый учёт.' : 'Войдите, чтобы продолжить учёт финансов.'}</p>
      {connectionError && <div className="auth-error" role="alert">{connectionError} <button type="button" onClick={check}>Повторить</button></div>}
      <form onSubmit={async event => {
        event.preventDefault(); setError('');
        if ((register || recover) && password !== confirmation) { setError('Пароли не совпадают'); return; }
        setBusy(true);
        try {
          if (recover || register) { setPendingAccount(await (recover ? AuthService.resetPassword(login, password, recoveryCode) : AuthService.register(login, password))); setSaved(false); }
          else update(await AuthService.login(login, password));
          setPassword(''); setConfirmation('');
        }
        catch (err) { setError(errorMessage(err)); }
        finally { setBusy(false); }
      }}>
        <label htmlFor="login">Логин</label>
        <input id="login" autoComplete="username" autoCapitalize="none" spellCheck={false} required minLength={3} maxLength={64} pattern="[a-zA-Z0-9_.\-]+" value={login} onChange={event => setLogin(event.target.value)} placeholder="Например, alex.finance" />
        <small>От 3 символов: латинские буквы, цифры, точка, дефис.</small>
        {recover && <><label htmlFor="recovery-code">Код восстановления</label><input id="recovery-code" autoComplete="off" autoCapitalize="none" spellCheck={false} required maxLength={128} value={recoveryCode} onChange={event => setRecoveryCode(event.target.value)} /></>}
        <label htmlFor="password">{recover ? 'Новый пароль' : 'Пароль'}</label>
        <input id="password" type="password" autoComplete={register || recover ? 'new-password' : 'current-password'} required minLength={8} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} placeholder="Не менее 8 символов" />
        {(register || recover) && <><label htmlFor="confirmation">Повторите пароль</label><input id="confirmation" type="password" autoComplete="new-password" required minLength={8} value={confirmation} onChange={event => setConfirmation(event.target.value)} /></>}
        {error && <div role="alert" className="auth-error">{error}</div>}
        <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Подождите…' : recover ? 'Сохранить новый пароль' : register ? 'Создать аккаунт' : 'Войти'} <span aria-hidden="true">→</span></button>
      </form>
      {!register && !recover && <button type="button" className="text-button" onClick={() => { setRecover(true); setError(''); setPassword(''); setConfirmation(''); }}>Забыли пароль?</button>}
      {recover && <button type="button" className="text-button" onClick={() => { setRecover(false); setError(''); setPassword(''); setConfirmation(''); setRecoveryCode(''); }}>Вернуться ко входу</button>}
      <p className="auth-note">Вход сохраняется на 30 дней на этом устройстве. На общем компьютере используйте кнопку «Выйти».</p>
    </section>
  </main>;
}
