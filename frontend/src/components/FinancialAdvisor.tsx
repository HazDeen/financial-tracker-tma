import { useEffect, useRef, useState } from 'react';
import { ArrowUp, ArrowUpRight, MessageSquare, RotateCcw, Wallet } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { FinanceService, errorMessage } from '../api/client';
import type { AIAdvisorResponse, AdvisorMessage } from '../types';
import type { ReportPeriod } from '../lib/period';
import { periodLabel } from '../lib/period';
import './FinancialAdvisor.css';

const questions = ['Разбери мой бюджет', 'На что уходит больше всего денег?', 'Сколько можно отложить?'];
export function FinancialAdvisor({ period, disabled }: { period: ReportPeriod; disabled: boolean }) {
  const [messages, setMessages] = useState<AdvisorMessage[]>([]);
  const [result, setResult] = useState<AIAdvisorResponse | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [failed, setFailed] = useState('');
  const lock = useRef(false);
  const alive = useRef(true);
  const latest = useRef<HTMLDivElement>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => {
    if (messages.length) latest.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [messages.length, busy]);
  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || lock.current || disabled) return;
    lock.current = true;
    setBusy(true); setError(''); setFailed('');
    const history = messages.slice(-12);
    setMessages([...messages, { role: 'user', content: text }]);
    setDraft('');
    try {
      const answer = await FinanceService.chatAdvice(period.start, period.end, text, history);
      if (!alive.current) return;
      setResult(answer);
      setMessages([...messages, { role: 'user', content: text }, { role: 'assistant', content: answer.markdown_insights }]);
    } catch (e) {
      if (!alive.current) return;
      setMessages(messages);
      setFailed(text);
      setDraft(text);
      setError(errorMessage(e, 'Не удалось получить разбор. Попробуйте ещё раз.'));
    } finally {
      lock.current = false;
      if (alive.current) setBusy(false);
    }
  };
  return (
    <div className="advisor-layout">
      <section className="advisor-conversation panel" aria-labelledby="advisor-title">
        <header className="advisor-header">
          <span className="advisor-symbol"><MessageSquare size={22} /></span>
          <div><h2 id="advisor-title">Финансовый помощник</h2><p>{periodLabel(period)}</p></div>
          {messages.length > 0 && <button className="icon-button" aria-label="Начать новый диалог" disabled={busy} onClick={() => { setMessages([]); setResult(null); setError(''); setDraft(''); }}><RotateCcw size={18} /></button>}
        </header>
        <div className="advisor-thread" role="log" aria-label="Диалог о финансах" aria-live="polite" aria-busy={busy}>
          {!messages.length && <div className="advisor-welcome">
            <span className="eyebrow">ОТ ЦИФР — К РЕШЕНИЯМ</span>
            <h3>Давайте разберёмся,<br />что говорят ваши расходы.</h3>
            <p>Найду, на что уходит больше всего денег, объясню итог периода и предложу следующие шаги.</p>
            <button className="button primary" disabled={busy || disabled} onClick={() => void ask(questions[0])}>Получить рекомендации <ArrowUpRight size={18} /></button>
            <small>Разбор учитывает записанные операции за выбранные даты.</small>
          </div>}
          {messages.map((message, index) => <article key={index} className={`advisor-message ${message.role}`}>
            <span className="advisor-message-label">{message.role === 'user' ? 'Вы' : 'Помощник'}</span>
            <div className="advisor-prose"><ReactMarkdown components={{ a: ({ children }) => <span>{children}</span>, img: () => null }}>{message.content}</ReactMarkdown></div>
          </article>)}
          {busy && <p className="advisor-thinking" role="status"><span />Смотрю операции и готовлю ответ…</p>}
          <div ref={latest} />
        </div>
        {error && <div className="alert" role="alert"><span>{error}</span><button disabled={busy || disabled} onClick={() => void ask(failed)}>Повторить</button></div>}
        <div className="advisor-prompts" aria-label="Быстрые вопросы">{questions.slice(messages.length ? 0 : 1).map(q => <button key={q} disabled={busy || disabled} onClick={() => void ask(q)}>{q}</button>)}</div>
        <form className="advisor-composer" onSubmit={e => { e.preventDefault(); void ask(draft); }}>
          <label className="sr-only" htmlFor="advisor-question">Вопрос о финансах</label>
          <textarea id="advisor-question" rows={2} maxLength={1500} placeholder="Спросите о своём бюджете…" value={draft} disabled={busy || disabled} onChange={e => setDraft(e.target.value)} onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void ask(draft); }
          }} />
          <button type="submit" aria-label="Отправить вопрос" disabled={busy || disabled || !draft.trim()}><ArrowUp size={21} /></button>
        </form>
        <p className="advisor-footnote">{result?.source === 'gemini' ? 'Пояснение подготовлено Gemini. Карточки рассчитаны по вашим операциям.' : result?.source === 'rules' ? 'Базовый разбор по операциям. AI-пояснение сейчас недоступно.' : 'Здесь можно обсудить бюджет. Ответы не заменяют ваши финансовые решения.'} Диалог хранится только до обновления данных или закрытия страницы.</p>
      </section>
      <aside className="advisor-actions" aria-label="Рекомендации по бюджету">
        <div className="advisor-actions-heading"><span className="eyebrow">СЛЕДУЮЩИЕ ШАГИ</span><h2>Что можно сделать</h2></div>
        {result ? result.recommendations.map((card, index) => <article key={card.id} className={`advisor-action ${card.priority}`}>
          <div className="advisor-action-top"><span>{String(index + 1).padStart(2, '0')}</span><small>{card.priority === 'warning' ? 'Стоит проверить' : 'По вашим данным'}</small></div>
          <h3>{card.title}</h3><p>{card.observation}</p><div className="advisor-action-step"><ArrowUpRight size={17} /><p>{card.action}</p></div>
        </article>) : <div className="advisor-action-placeholder"><Wallet size={26} /><h3>Советы с опорой на цифры</h3><p>Запустите разбор — здесь появятся наблюдения и конкретные действия по вашему бюджету.</p></div>}
        <p className="advisor-scope">В этом разборе: доходы, расходы и категории за выбранный период. Баланс, расписание платежей и другие периоды пока не учитываются.</p>
      </aside>
    </div>
  );
}
