import { useEffect, useRef, useState } from 'react';
import { Deposits } from '../api/deposits';
import type { SavedDeposit } from '../api/deposits';
import { errorMessage } from '../api/client';
import { readNumber } from '../lib/finance-tools';
import { todayISO } from '../lib/period';

const money = (value: string | number) => Number(value).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' });
const day = (value: string) => new Date(value + 'T12:00:00').toLocaleDateString('ru-RU');
export function SavedDeposits({ onChanged }: { onChanged?: () => void }) {
  const [rows, setRows] = useState<SavedDeposit[]>([]);
  const [title, setTitle] = useState(''); const [principal, setPrincipal] = useState('');
  const [rate, setRate] = useState(''); const [months, setMonths] = useState('12');
  const [openedOn, setOpenedOn] = useState(todayISO());
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [closing, setClosing] = useState<number | null>(null); const lock = useRef(false);
  useEffect(() => {
    let alive = true;
    Deposits.list().then(data => { if (alive) setRows(data); }).catch(e => { if (alive) setError(errorMessage(e)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);
  async function action(fn: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(''); setNotice('');
    try { await fn(); onChanged?.(); } catch (e) { setError(errorMessage(e, e instanceof Error ? e.message : 'Не удалось сохранить вклад')); }
    finally { lock.current = false; setBusy(false); }
  }
  const upcoming = rows.filter(row => row.next_payment_date && row.next_payment_date <= todayISO().slice(0, 7) + '-31');
  return <section className="panel ft-reports ft-saved-deposits"><h2>Мои вклады</h2>
    <p>Добавьте вклад с ежемесячной выплатой процентов. В день выплаты доход автоматически учитывается в операциях, балансе и отчётах при открытии приложения. Начисления за прошлые месяцы также будут добавлены.</p>
    <form onSubmit={e => { e.preventDefault(); const submittedDate = String(new FormData(e.currentTarget).get('opened_on') || openedOn); void action(async () => {
      const amount = readNumber(principal); const annual = readNumber(rate); const term = readNumber(months);
      if (amount === null || annual === null || term === null || ![amount, annual, term].every(Number.isFinite) || !Number.isInteger(term)) throw new Error('Проверьте сумму, ставку и срок');
      const saved = await Deposits.create({ title: title.trim(), principal: amount, annual_rate: annual, months: term, opened_on: submittedDate });
      setRows(previous => [saved, ...previous]); setTitle(''); setPrincipal(''); setRate(''); setNotice('Вклад добавлен. Наступившие выплаты учтены в доходах.');
    }); }}><fieldset disabled={busy || loading} className="ft-deposit-fields"><div className="ft-fields">
      <label className="ft-field"><span>Банк или название вклада</span><input required maxLength={128} value={title} onChange={e => setTitle(e.target.value)} placeholder="Например, накопительный вклад" /></label>
      <label className="ft-field"><span>Сумма, ₽</span><input required inputMode="decimal" value={principal} onChange={e => setPrincipal(e.target.value)} /></label>
      <label className="ft-field"><span>Ставка, % годовых</span><input required inputMode="decimal" value={rate} onChange={e => setRate(e.target.value)} /></label>
      <label className="ft-field"><span>Срок, месяцев</span><input required type="number" min="1" max="600" value={months} onChange={e => setMonths(e.target.value)} /></label>
      <label className="ft-field"><span>Дата открытия</span><input required name="opened_on" type="date" min="2000-01-01" max={todayISO()} value={openedOn} onChange={e => setOpenedOn(e.target.value)} /></label>
    </div><p className="ft-note">Выплата раз в месяц в день открытия, первая — через месяц. Оценка до налога: сумма × ставка ÷ 12, без капитализации. Тело вклада учитывайте отдельно в начальном балансе; его внесение и возврат не создают доход.</p>
    <button className="button primary" disabled={!title.trim()}>{busy ? 'Сохраняем…' : 'Добавить вклад'}</button></fieldset></form>
    {error && <p className="ft-error" role="alert">{error}<button className="text-button" disabled={busy} onClick={() => void action(async () => { setRows(await Deposits.list()); setLoading(false); })}>Обновить список</button></p>}
    {notice && <p className="ft-success" role="status">{notice}</p>}
    {!!upcoming.length && <p className="ft-note">Ожидается до конца месяца: <strong>{money(upcoming.reduce((sum, row) => sum + Number(row.monthly_income), 0))}</strong></p>}
    <div className="ft-report-list">{loading ? <p role="status">Загружаем вклады…</p> : !rows.length ? <p className="ft-empty">Сохранённых вкладов пока нет</p> : rows.map(row => <article key={row.id}>
      <div className="ft-report-copy"><h3>{row.title}</h3><p>{money(row.principal)} · {row.annual_rate}% годовых · до {day(row.ends_on)}</p>
        <p><strong>{money(row.monthly_income)} в месяц</strong> · начислено {money(row.accrued_income)}</p>
        <p>{!row.is_active ? 'Вклад закрыт' : row.next_payment_date ? `Следующая выплата ${day(row.next_payment_date)}` : 'Срок завершён'}</p>
      </div>{row.is_active && row.next_payment_date && <button className="text-button" disabled={busy} onClick={() => setClosing(row.id)}>Закрыть вклад</button>}
      {closing === row.id && <div className="ft-delete"><span>Прекратить будущие начисления? Учтённый доход сохранится.</span><button disabled={busy} onClick={() => void action(async () => { const saved = await Deposits.close(row.id); setRows(previous => previous.map(item => item.id === saved.id ? saved : item)); setClosing(null); setNotice('Вклад закрыт.'); })}>Закрыть вклад</button><button disabled={busy} onClick={() => setClosing(null)}>Отмена</button></div>}
    </article>)}</div></section>;
}
