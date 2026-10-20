import { useRef, useState } from 'react';
import { FinanceService, errorMessage } from '../api/client';

interface Preview { total: number; income: string; expense: string; transactions: { transaction_date: string; description: string; amount: string; transaction_type: string }[] }
const rub = (value: string) => Number(value).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' });
export function StatementImport({ onSuccess }: { onSuccess: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState('');
  const input = useRef<HTMLInputElement>(null);
  return <section className="statement-import">
    <p>Альфа-Банк, Т-Банк и СберБанк. CSV или PDF с текстовым слоем, до 10 МБ. Учёт в рублях.</p>
    <p>Сначала проверьте суммы и операции. Сканированные PDF и неподдерживаемые макеты нужно экспортировать в CSV.</p>
    <label className="statement-file">Выбрать выписку
      <input ref={input} type="file" accept=".csv,.pdf" disabled={busy} onChange={async event => {
        const selected = event.target.files?.[0];
        setPreview(null); setResult(''); setError(''); setFile(null);
        if (!selected) return;
        if (selected.size > 10 * 1024 * 1024) { setError('Максимальный размер — 10 МБ'); return; }
        setBusy(true);
        try { setPreview(await FinanceService.previewStatement(selected)); setFile(selected); }
        catch (err) { setError(errorMessage(err)); }
        finally { setBusy(false); }
      }} />
    </label>
    {busy && <p role="status">Обрабатываем выписку…</p>}
    {error && <p role="alert" className="auth-error">{error}</p>}
    {preview && !result && <>
      <h3>{file?.name}</h3><p>Найдено операций: {preview.total}</p>
      <div className="statement-totals"><span>Доходы <b>{rub(preview.income)}</b></span><span>Расходы <b>{rub(preview.expense)}</b></span></div>
      <div className="statement-rows">{preview.transactions.map((tx, index) => <div key={index}>
        <span><small>{new Date(tx.transaction_date).toLocaleDateString('ru-RU')}</small>{tx.description}</span>
        <strong className={tx.transaction_type === 'income' ? 'text-emerald-300' : 'text-rose-300'}>{tx.transaction_type === 'income' ? '+' : '−'}{rub(tx.amount)}</strong>
      </div>)}</div>
      {preview.total > 20 && <p>Показаны первые 20 операций.</p>}
      <button type="button" className="auth-submit" disabled={busy} onClick={async () => {
        if (!file) return; setBusy(true); setError('');
        try { const response = await FinanceService.uploadStatement(file); setResult(response.message); onSuccess(); }
        catch (err) { setError(errorMessage(err)); }
        finally { setBusy(false); }
      }}>Импортировать {preview.total} операций</button>
    </>}
    {result && <p role="status" className="text-emerald-300">{result}</p>}
    <div className="statement-examples">Тестовые CSV с вымышленными операциями: <a href="/examples/alfabank.csv" download>Альфа-Банк</a> · <a href="/examples/tbank.csv" download>Т-Банк</a> · <a href="/examples/sberbank.csv" download>СберБанк</a></div>
  </section>;
}
