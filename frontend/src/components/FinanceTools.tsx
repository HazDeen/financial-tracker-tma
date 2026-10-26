import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Calculator, Download, FileText, Trash2, Upload } from 'lucide-react';
import { CompanyReports } from '../api/company-reports';
import type { CompanyReport } from '../api/company-reports';
import { errorMessage } from '../api/client';
import { coupons, deposit, emptyFigures, figureKeys, figureValues, incomeTax, multiples, readNumber, taxBreakdown, taxSource } from '../lib/finance-tools';
import type { FigureKey, Figures } from '../lib/finance-tools';
import './FinanceTools.css';

const money = (value: number) => value.toLocaleString('ru-RU', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) + ' ₽';
const tabs = [{ id: 'deposit', label: 'Вклад' }, { id: 'tax', label: 'НДФЛ' }, { id: 'bonds', label: 'Облигации' }, { id: 'companies', label: 'Компании' }] as const;
function Field({ label, value, onChange, hint, integer = false }: { label: string; value: string; onChange: (value: string) => void; hint?: string; integer?: boolean }) {
  const hintId = useId();
  return <label className="ft-field"><span>{label}</span><input type="text" aria-label={label} aria-describedby={hint ? hintId : undefined} inputMode={integer ? 'numeric' : 'decimal'} value={value} onChange={e => onChange(e.target.value)} />{hint && <small id={hintId}>{hint}</small>}</label>;
}
function number(value: string) {
  const result = readNumber(value);
  if (result === null || !Number.isFinite(result)) throw new Error('Заполните поля числами. Дробную часть можно отделить запятой.');
  return result;
}
function calculate<T,>(fn: () => T): { value: T; error?: never } | { value?: never; error: string } {
  try { return { value: fn() }; } catch (e) { return { error: e instanceof Error ? e.message : 'Проверьте значения' }; }
}
function Result({ label, amount, children }: { label: string; amount: string; children?: ReactNode }) {
  return <aside className="ft-result"><span>{label}</span><output>{amount}</output>{children}</aside>;
}
function CalculationError({ message }: { message: string }) { return <p className="ft-error" role="alert">{message}</p>; }
function DepositCalculator() {
  const [principal, setPrincipal] = useState('100000'); const [rate, setRate] = useState('12');
  const [months, setMonths] = useState('12'); const [compound, setCompound] = useState(false);
  const result = calculate(() => deposit(number(principal), number(rate), number(months), compound));
  return <div className="ft-calculator"><section className="panel ft-inputs"><h2>Проценты по вкладу</h2><p>Сравните выплату процентов и ежемесячную капитализацию.</p>
    <div className="ft-fields"><Field label="Сумма вклада, ₽" value={principal} onChange={setPrincipal} /><Field label="Ставка, % годовых" value={rate} onChange={setRate} /><Field label="Срок, месяцев" value={months} onChange={setMonths} integer /></div>
    <label className="ft-check"><input type="checkbox" checked={compound} onChange={e => setCompound(e.target.checked)} />Прибавлять проценты к вкладу каждый месяц</label>
    <p className="ft-note">Расчёт по месячной ставке: годовая ставка ÷ 12. В банке сумма зависит от числа дней, пополнений и условий договора. Здесь доход до налога.</p>
  </section>{result.error ? <CalculationError message={result.error} /> : result.value && <Result label="Проценты за весь срок" amount={money(result.value.interest)}><dl><div><dt>{compound ? 'Проценты за первый месяц' : 'Проценты в месяц'}</dt><dd>{money(result.value.monthly)}</dd></div><div><dt>Вклад и проценты</dt><dd>{money(result.value.total)}</dd></div></dl><p>{compound ? 'Ежемесячная капитализация увеличивает базу начисления.' : `${principal} × ${rate}% ÷ 12 — ежемесячный доход.`}</p></Result>}</div>;
}
function TaxCalculator() {
  const [income, setIncome] = useState('3000000'); const [kind, setKind] = useState(false);
  const result = calculate(() => { const base = number(income); return { base, tax: incomeTax(base, kind), rows: taxBreakdown(base, kind) }; });
  return <><div className="ft-calculator"><section className="panel ft-inputs"><h2>Налог на доходы</h2><p>Годовая налоговая база резидента РФ, без вычетов и специальных льгот.</p>
    <label className="ft-field"><span>Группа доходов</span><select value={kind ? 'investment' : 'general'} onChange={e => setKind(e.target.value === 'investment')}><option value="general">Основная: зарплата, аренда и другие</option><option value="investment">Ценные бумаги: шкала 13 / 15%</option></select></label>
    <Field label="Налоговая база за год, ₽" value={income} onChange={setIncome} />
    <p className="ft-note">Повышенная ставка применяется только к части дохода сверх порога. Зарплата и инвестиционные доходы здесь считаются отдельно. Укажите уже облагаемую сумму, а не общий оборот.</p>
    <a className="ft-source" href={taxSource} target="_blank" rel="noreferrer">Шкалы ФНС с 2025 года, актуально для 2026 ↗</a>
  </section>{result.error ? <CalculationError message={result.error} /> : result.value && <Result label="НДФЛ за год, оценка" amount={money(result.value.tax)}><dl><div><dt>После налога</dt><dd>{money(result.value.base - result.value.tax)}</dd></div><div><dt>Средняя ставка</dt><dd>{(result.value.base ? result.value.tax / result.value.base * 100 : 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 })}%</dd></div></dl><p>Итоговое удержание зависит от округлений налогового агента.</p></Result>}</div>
    {result.value && <section className="panel ft-tax-breakdown"><h3>Как складывается налог</h3><div className="ft-table-wrap"><table><thead><tr><th>Часть базы</th><th>Ставка</th><th>Налог</th></tr></thead><tbody>{result.value.rows.map(row => <tr key={row.rate}><td>{money(row.base)}</td><td>{Math.round(row.rate * 100)}%</td><td>{money(row.tax)}</td></tr>)}{!result.value.rows.length && <tr><td colSpan={3}>При нулевой базе налога нет</td></tr>}</tbody></table></div></section>}</>;
}
function BondCalculator() {
  const [nominal, setNominal] = useState('1000'); const [rate, setRate] = useState('12'); const [quantity, setQuantity] = useState('100');
  const [payments, setPayments] = useState('2'); const [other, setOther] = useState('0');
  const result = calculate(() => coupons(number(nominal), number(rate), number(quantity), number(payments), number(other)));
  return <div className="ft-calculator"><section className="panel ft-inputs"><h2>Купонный доход</h2><p>Годовой купон и налог по облигациям с фиксированной ставкой.</p><div className="ft-fields">
    <Field label="Номинал одной облигации, ₽" value={nominal} onChange={setNominal} /><Field label="Купонная ставка, % годовых" value={rate} onChange={setRate} />
    <Field label="Количество облигаций" value={quantity} onChange={setQuantity} integer /><Field label="Выплат в год" value={payments} onChange={setPayments} integer />
    <Field label="Другие доходы этой налоговой базы за год, ₽" value={other} onChange={setOther} hint="Для учёта порога 2,4 млн ₽. Зарплату не включайте." />
  </div><p className="ft-note">Для резидента РФ: 13% до 2,4 млн ₽ соответствующей базы и 15% сверх порога. Налог на купоны — разница налога с ними и без них. Не учитываются ИИС, льготы, НКД, комиссии, продажа, амортизация номинала и плавающие купоны. Купонная ставка не равна доходности к погашению.</p><a className="ft-source" href="https://www.nalog.gov.ru/rn28/news/activities_fts/16548710/" target="_blank" rel="noreferrer">Налог на купоны: разъяснение ФНС ↗</a></section>
  {result.error ? <CalculationError message={result.error} /> : result.value && <Result label="Купоны за год после налога" amount={money(result.value.net)}><dl><div><dt>До налога за год</dt><dd>{money(result.value.gross)}</dd></div><div><dt>Налог на купоны</dt><dd>{money(result.value.tax)}</dd></div><div><dt>Одна выплата до налога</dt><dd>{money(result.value.perPayment)}</dd></div></dl><p>Предполагаются одинаковые выплаты и владение весь год.</p></Result>}</div>;
}
const figureLabels: Record<FigureKey, string> = { marketCap: 'Рыночная капитализация', netIncome: 'Чистая прибыль за год', revenue: 'Выручка за год', equity: 'Капитал на конец периода', averageEquity: 'Средний капитал за год', debt: 'Процентный долг', cash: 'Денежные средства', ebitda: 'EBITDA за год' };
const explanations = [
  ['pe', 'P/E', 'Капитализация / чистая прибыль'], ['ps', 'P/S', 'Капитализация / выручка'], ['pb', 'P/B', 'Капитализация / капитал на конец периода'],
  ['evEbitda', 'EV/EBITDA', '(Капитализация + долг − деньги) / EBITDA'], ['roe', 'ROE', 'Чистая прибыль / средний капитал × 100%'],
] as const;
function CompaniesCalculator() {
  const [figures, setFigures] = useState<Figures>(emptyFigures); const [company, setCompany] = useState(''); const [period, setPeriod] = useState('2025, год');
  const [file, setFile] = useState<File | null>(null); const [reports, setReports] = useState<CompanyReport[]>([]);
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null); const fileInput = useRef<HTMLInputElement>(null);
  const lock = useRef(false);
  const result = calculate(() => multiples(figures));
  useEffect(() => { let alive = true; CompanyReports.list().then(data => { if (alive) setReports(data); }).catch(e => { if (alive) setError(errorMessage(e, 'Не удалось загрузить отчёты')); }).finally(() => { if (alive) setLoading(false); }); return () => { alive = false; }; }, []);
  const action = async (fn: () => Promise<void>) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(''); setNotice('');
    try { await fn(); } catch (e) { setError(e instanceof Error ? errorMessage(e, e.message) : 'Не удалось выполнить действие'); }
    finally { lock.current = false; setBusy(false); }
  };
  const save = () => action(async () => {
    if (!company.trim() || !period.trim() || !file) throw new Error('Укажите компанию, период и выберите файл отчёта');
    if (file.size > 10 * 1024 * 1024) throw new Error('Размер отчёта — не больше 10 МБ');
    const saved = await CompanyReports.upload(company.trim(), period.trim(), file, figureValues(figures));
    setReports(previous => [saved, ...previous]); setFile(null); if (fileInput.current) fileInput.current.value = '';
    setNotice('Отчёт и введённые показатели сохранены в аккаунте.');
  });
  return <div className="ft-companies"><section className="panel ft-inputs"><div className="ft-section-title"><div><h2>Показатели компании</h2><p>Все суммы — в рублях, в одном масштабе и по одной отчётности. Прибыль, выручка и EBITDA — за полный год или последние 12 месяцев.</p></div><Calculator size={23} /></div>
    <div className="ft-fields"><label className="ft-field"><span>Компания</span><input value={company} maxLength={160} onChange={e => setCompany(e.target.value)} placeholder="Название компании" /></label><label className="ft-field"><span>Период отчёта</span><input value={period} maxLength={80} onChange={e => setPeriod(e.target.value)} placeholder="Например, 2025, год" /></label>
    {figureKeys.map(key => <Field key={key} label={`${figureLabels[key]}, ₽`} value={figures[key]} onChange={value => setFigures(previous => ({ ...previous, [key]: value }))} hint={key === 'averageEquity' ? '(Капитал на начало + на конец года) ÷ 2' : undefined} />)}</div>
    <p className="ft-note">Пустое поле означает, что данных нет; ноль введите явно. P/E, P/S, P/B и EV/EBITDA не выводятся при неположительном знаменателе. ROE допускает убыток при положительном среднем капитале.</p>
    {result.error && <CalculationError message={result.error} />}
    <div className="ft-multiples" aria-label="Рассчитанные показатели">{explanations.map(([key, title, formula]) => <div key={key}><span>{title}</span><output>{result.value?.[key] == null ? '—' : result.value[key].toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + (key === 'roe' ? '%' : '×')}</output><small>{formula}</small></div>)}</div>
    <p className="ft-note">Сравнивайте компании одной отрасли и сопоставимые периоды. Эти коэффициенты сами по себе не являются рекомендацией купить или продать акции.</p>
    <a className="ft-source" href="https://ipoguide.moex.com/2/0/index.html" target="_blank" rel="noreferrer">О мультипликаторах: руководство Московской биржи ↗</a>
  </section><section className="panel ft-reports"><h2>Отчёты компаний</h2><p>Прикрепите исходный отчёт к введённым показателям. Файлы сохраняются в вашем аккаунте; автоматического извлечения цифр из PDF и таблиц пока нет.</p>
    <form onSubmit={e => { e.preventDefault(); void save(); }}><label className="ft-upload"><Upload size={21} /><span>Выберите отчёт <small>PDF, XLSX или CSV · до 10 МБ · до 20 файлов</small></span><input ref={fileInput} aria-label="Файл отчёта компании" type="file" accept=".pdf,.xlsx,.csv" disabled={busy || loading} onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>{file && <p className="ft-file-name">{file.name}</p>}<button className="button primary" disabled={busy || loading || !file || !company.trim() || !period.trim() || !!result.error}>{busy ? 'Сохраняем…' : 'Сохранить отчёт и показатели'}</button></form>
    {error && <div className="alert" role="alert"><span>{error}</span><button disabled={busy} onClick={() => void action(async () => { setReports(await CompanyReports.list()); setLoading(false); })}>Обновить список</button></div>}
    {notice && <p className="ft-success" role="status">{notice}</p>}
    <div className="ft-report-list">{loading ? <p role="status">Загружаем отчёты…</p> : !reports.length ? <div className="ft-empty"><FileText size={26} /><p>Сохранённых отчётов пока нет</p></div> : reports.map(report => <article key={report.id}><FileText size={20} /><div className="ft-report-copy"><h3>{report.company}</h3><p>{report.period} · {report.filename} · {(report.size / 1024).toFixed(1)} КБ</p><button className="text-button" disabled={busy} onClick={() => { setFigures(Object.fromEntries(figureKeys.map(key => [key, report.metrics[key] ?? ''])) as Figures); setCompany(report.company); setPeriod(report.period); setNotice('Показатели отчёта загружены в калькулятор.'); }}>Загрузить показатели</button></div><div className="ft-report-actions"><button className="icon-button" aria-label={`Скачать отчёт ${report.company}`} disabled={busy} onClick={() => void action(() => CompanyReports.download(report))}><Download size={18} /></button><button className="icon-button" aria-label={`Удалить отчёт ${report.company}`} disabled={busy} onClick={() => setDeleting(report.id)}><Trash2 size={18} /></button></div>{deleting === report.id && <div className="ft-delete"><span>Удалить файл и сохранённые показатели?</span><button disabled={busy} onClick={() => void action(async () => { await CompanyReports.remove(report.id); setReports(previous => previous.filter(item => item.id !== report.id)); setDeleting(null); setNotice('Отчёт удалён.'); })}>Удалить</button><button disabled={busy} onClick={() => setDeleting(null)}>Отмена</button></div>}</article>)}</div>
  </section></div>;
}
export function FinanceTools() {
  const [tab, setTab] = useState<typeof tabs[number]['id']>('deposit');
  return <div className="finance-tools"><div className="ft-tabs" role="tablist" aria-label="Финансовые расчёты" onKeyDown={e => {
    const index = tabs.findIndex(item => item.id === tab);
    const next = e.key === 'ArrowRight' ? (index + 1) % tabs.length : e.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : null;
    if (next !== null) { e.preventDefault(); setTab(tabs[next].id); document.getElementById(`ft-tab-${tabs[next].id}`)?.focus(); }
  }}>{tabs.map(item => <button key={item.id} id={`ft-tab-${item.id}`} role="tab" type="button" aria-selected={tab === item.id} aria-controls={`ft-panel-${item.id}`} tabIndex={tab === item.id ? 0 : -1} onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
    {tabs.map(item => <div key={item.id} id={`ft-panel-${item.id}`} role="tabpanel" aria-labelledby={`ft-tab-${item.id}`} hidden={tab !== item.id}>{item.id === 'deposit' ? <DepositCalculator /> : item.id === 'tax' ? <TaxCalculator /> : item.id === 'bonds' ? <BondCalculator /> : <CompaniesCalculator />}</div>)}
  </div>;
}
