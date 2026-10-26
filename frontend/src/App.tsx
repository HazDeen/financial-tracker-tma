import { RecoverySettings } from "./components/RecoverySettings";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  ArrowRight,
  CalendarDays,
  ChartNoAxesCombined,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Download,
  Ellipsis,
  Eye,
  EyeOff,
  LayoutDashboard,
  ListFilter,
  LogOut,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Trash2,
  UserRound,
  Wallet,
  X,
} from "lucide-react";
import { plannedExpenses } from "./lib/schedule";
import { FinanceService, PersonalService, errorMessage } from "./api/client";
import { useAuth } from "./context/AuthContext";
import { StatementImport } from "./components/StatementImport";
import { PeriodForm } from "./components/PeriodForm";
import { monthPeriod, todayISO, periodLabel, shiftPeriod } from "./lib/period";
import type { ReportPeriod } from "./lib/period";
import { LoadingScreen } from "./components/LoadingScreen";
import type {
  MonthlyReportResponse,
  RecurringResponse,
  TransactionDTO,
} from "./types";

type Tab = "home" | "operations" | "schedule" | "profile";
type Kind = "income" | "expense";
type Modal =
  | { type: "transaction"; item?: TransactionDTO; kind?: Kind }
  | { type: "schedule"; item?: RecurringResponse; kind?: Kind }
  | { type: "import" }
  | { type: "period" }
  | {
      type: "delete";
      item: TransactionDTO | RecurringResponse;
      source: "transaction" | "schedule";
    }
  | null;
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
const money = (n: number | string = 0) =>
  Number(n).toLocaleString("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }) + " ₽";
const displayDate = (s: string) =>
  new Date(s.slice(0, 10) + "T12:00:00").toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
  });
const tabs = [
  { id: "home", label: "Главная", icon: LayoutDashboard },
  { id: "operations", label: "Операции", icon: ChartNoAxesCombined },
  { id: "schedule", label: "Расписание", icon: CalendarDays },
  { id: "profile", label: "Профиль", icon: UserRound },
] as const;
const titleByTab = {
  home: "Деньги под контролем",
  operations: "История операций",
  schedule: "Всё по расписанию",
  profile: "Ваш профиль",
};
function nextOccurrence(day: number) {
  const d = new Date();
  const clamp = (y: number, m: number) =>
    new Date(y, m, Math.min(day, new Date(y, m + 1, 0).getDate()), 12);
  let n = clamp(d.getFullYear(), d.getMonth());
  if (n.getDate() < d.getDate()) n = clamp(d.getFullYear(), d.getMonth() + 1);
  return `${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, "0")}-${String(n.getDate()).padStart(2, "0")}`;
}

function ModalFrame({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby="modal-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-inner">
        <header>
          <div>
            <span className="eyebrow">МОИ ФИНАНСЫ</span>
            <h2 id="modal-title">{title}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Закрыть"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
function Empty({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Wallet size={26} />
      </span>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  );
}
function TransactionRow({
  tx,
  onEdit,
  onDelete,
}: {
  tx: TransactionDTO;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const incoming = tx.transaction_type === "income";
  return (
    <div className="transaction-row">
      <span className={`transaction-icon ${incoming ? "income" : "expense"}`}>
        {incoming ? <ArrowDownLeft size={21} /> : <ArrowUpRight size={21} />}
      </span>
      <button
        className="transaction-copy"
        onClick={onEdit}
        aria-label={`Изменить: ${tx.category}`}
      >
        <strong>
          {tx.description && tx.description !== "Ручной ввод"
            ? tx.description
            : tx.category}
        </strong>
        <span>
          {tx.category} · {displayDate(tx.transaction_date)}
        </span>
      </button>
      <b className={`transaction-amount ${incoming ? "income" : "expense"}`}>
        {incoming ? "+" : "−"}
        {money(tx.amount)}
      </b>
      <button
        className="icon-button row-delete"
        aria-label={`Удалить: ${tx.category}`}
        onClick={onDelete}
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}

export default function App() {
  const { account, logout } = useAuth();
  const [tab, setTab] = useState<Tab>("home");
  const [period, setPeriod] = useState<ReportPeriod>(() =>
    monthPeriod(todayISO().slice(0, 7)),
  );
  const [report, setReport] = useState<MonthlyReportResponse | null>(null);
  const [schedule, setSchedule] = useState<RecurringResponse[]>([]);
  const [balance, setBalance] = useState({
    balance: "0",
    opening_balance: "0",
  });
  const [initial, setInitial] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modal, setModal] = useState<Modal>(null);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"all" | Kind>("all");
  const [search, setSearch] = useState("");
  const [scheduleFilter, setScheduleFilter] = useState<"all" | Kind>("all");
  const requestRef = useRef(0);
  const load = useCallback(async () => {
    const request = ++requestRef.current;
    setRefreshing(true);
    setError("");
    try {
      const [r, s, b] = await Promise.all([
        FinanceService.getPeriodReport(period.start, period.end),
        FinanceService.getRecurring(),
        PersonalService.balance(),
      ]);
      if (request !== requestRef.current) return;
      setReport(r);
      setSchedule(s);
      setBalance(b);
    } catch (e) {
      if (request === requestRef.current) setError(errorMessage(e));
    } finally {
      if (request === requestRef.current) {
        setInitial(false);
        setRefreshing(false);
      }
    }
  }, [period]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4500);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const back = (e: Event) => {
      if (modal) {
        e.preventDefault();
        if (!busy) setModal(null);
      } else if (tab !== "home") {
        e.preventDefault();
        setTab("home");
      }
    };
    window.addEventListener("android-back", back);
    return () => window.removeEventListener("android-back", back);
  }, [modal, tab, busy]);
  const perform = async (action: () => Promise<unknown>, message: string) => {
    setBusy(true);
    setError("");
    try {
      await action();
      setModal(null);
      setNotice(message);
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };
  const active = schedule
    .filter((s) => s.is_active)
    .sort((a, b) => a.next_payment_date.localeCompare(b.next_payment_date));
  const nextIncome = active.find((s) => s.transaction_type === "income");
  const reserved = plannedExpenses(
    active,
    nextIncome?.next_payment_date,
    today(),
  );
  const upcoming = active.slice(0, 4);
  const transactions = (report?.transactions || []).filter(
    (t) =>
      (filter === "all" || t.transaction_type === filter) &&
      `${t.category} ${t.description || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const PeriodControl = (
    <div className="month-control period-control">
      <button
        aria-label="Предыдущий период"
        disabled={refreshing || shiftPeriod(period, -1) === period}
        onClick={() => setPeriod(shiftPeriod(period, -1))}
      >
        <ChevronLeft size={17} />
      </button>
      <button
        className="period-select"
        aria-label={`Выбрать период: ${periodLabel(period)}`}
        onClick={() => setModal({ type: "period" })}
      >
        <CalendarDays size={16} />
        <span>{periodLabel(period)}</span>
      </button>
      <button
        aria-label="Следующий период"
        disabled={refreshing || shiftPeriod(period, 1) === period}
        onClick={() => setPeriod(shiftPeriod(period, 1))}
      >
        <ChevronRight size={17} />
      </button>
    </div>
  );
  const txRow = (tx: TransactionDTO) => (
    <TransactionRow
      key={tx.id}
      tx={tx}
      onEdit={() => setModal({ type: "transaction", item: tx })}
      onDelete={() =>
        setModal({ type: "delete", item: tx, source: "transaction" })
      }
    />
  );
  if (initial) return <LoadingScreen />;
  if (!report && error)
    return (
      <div className="connection-state">
        <span className="brand-symbol">₽</span>
        <h1>Не удалось загрузить данные</h1>
        <p>{error}</p>
        <button
          className="button primary"
          disabled={refreshing}
          onClick={() => void load()}
        >
          Попробовать снова
        </button>
      </div>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("home");
          }}
        >
          <span className="brand-symbol">₽</span>
          <span>
            Мои финансы<span className="brand-dot">.</span>
            <small>Личное пространство</small>
          </span>
        </a>
        <span className="sidebar-label">ВАШИ ФИНАНСЫ</span>
        <nav aria-label="Основная навигация">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              aria-current={tab === id ? "page" : undefined}
              onClick={() => setTab(id)}
            >
              <Icon size={20} />
              <span>{label}</span>
              {tab === id && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={20} />
          <p>
            Меньше забот.
            <br />
            <strong>Больше ясности.</strong>
          </p>
        </div>
        <button className="sidebar-account" onClick={() => setTab("profile")}>
          <span className="avatar">
            {account?.login.slice(0, 1).toUpperCase()}
          </span>
          <span>
            <strong>{account?.login}</strong>
            <small>Личный аккаунт</small>
          </span>
          <Settings2 size={17} />
        </button>
      </aside>
      <div className="workspace">
        <header className="mobile-header">
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              setTab("home");
            }}
          >
            <span className="brand-symbol">₽</span>
            <span>
              Мои финансы<span className="brand-dot">.</span>
            </span>
          </a>
          <button
            className="avatar"
            aria-label="Открыть профиль"
            onClick={() => setTab("profile")}
          >
            {account?.login.slice(0, 1).toUpperCase()}
          </button>
        </header>
        <main className="page" aria-busy={refreshing}>
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {tab === "home"
                  ? "ВАШ ЛИЧНЫЙ ОБЗОР"
                  : tab === "operations"
                    ? "ДОХОДЫ И РАСХОДЫ"
                    : tab === "schedule"
                      ? "ПЛАН НА МЕСЯЦ"
                      : "ЛИЧНОЕ ПРОСТРАНСТВО"}
              </p>
              <h1>
                {titleByTab[tab]}
                <span className="brand-dot">.</span>
              </h1>
              <p className="page-description">
                {tab === "home"
                  ? "Сегодня понятно. Завтра спокойно."
                  : tab === "operations"
                    ? "Каждая запись на своём месте."
                    : tab === "schedule"
                      ? "Зарплата, подписки и другие регулярные платежи."
                      : "Настройки, которые делают приложение вашим."}
              </p>
            </div>
            {tab === "home" || tab === "operations" ? (
              <button
                className="button primary add-main"
                onClick={() => setModal({ type: "transaction" })}
              >
                <Plus size={19} />
                Добавить операцию
              </button>
            ) : tab === "schedule" ? (
              <button
                className="button primary"
                onClick={() => setModal({ type: "schedule" })}
              >
                <Plus size={19} />
                Добавить событие
              </button>
            ) : null}
          </div>
          {error && (
            <div className="alert" role="alert">
              <span>{error}</span>
              <button onClick={() => void load()} disabled={refreshing}>
                Повторить
              </button>
            </div>
          )}
          {notice && (
            <div className="toast" role="status">
              <Check size={18} />
              {notice}
            </div>
          )}
          {tab === "home" && (
            <>
              <section className="hero-grid">
                <div className="balance-card">
                  <div className="balance-top">
                    <span>
                      <Wallet size={17} />
                      Доступно сейчас
                    </span>
                    <span className="balance-badge">Личный бюджет</span>
                  </div>
                  <strong className="balance-number">
                    {money(balance.balance)}
                  </strong>
                  <p>Начальный остаток и все внесённые операции</p>
                  <div className="balance-actions">
                    <button
                      onClick={() =>
                        setModal({ type: "transaction", kind: "expense" })
                      }
                    >
                      <Plus size={17} />
                      Расход
                    </button>
                    <button
                      onClick={() =>
                        setModal({ type: "transaction", kind: "income" })
                      }
                    >
                      <ArrowDownLeft size={18} />
                      Доход
                    </button>
                  </div>
                </div>
                <div className="forecast-card">
                  <span className="section-kicker">
                    <span className="icon-tile">
                      <CalendarDays size={20} />
                    </span>
                    До следующего дохода
                  </span>
                  <div className="forecast-title">
                    <strong>{money(Number(balance.balance) - reserved)}</strong>
                    <span>после запланированных списаний</span>
                  </div>
                  <div className="forecast-foot">
                    <span>
                      {nextIncome
                        ? `${nextIncome.title} · ${displayDate(nextIncome.next_payment_date)}`
                        : "Доход пока не запланирован"}
                    </span>
                    <b className="income">
                      {nextIncome ? "+" + money(nextIncome.amount) : "—"}
                    </b>
                  </div>
                  <p className="footnote">
                    {nextIncome
                      ? "Учтены ближайшие платежи до этой даты."
                      : "Вычтено по одному ближайшему списанию из расписания."}
                  </p>
                </div>
              </section>
              <section className="month-summary">
                <div className="section-heading">
                  <h2>
                    {period.mode === "month"
                      ? "Сводка за месяц"
                      : period.mode === "day"
                        ? "Сводка за день"
                        : "Сводка за период"}
                  </h2>
                  {PeriodControl}
                </div>
                <div className="stat-grid">
                  <div className="stat">
                    <span className="stat-icon income">
                      <ArrowDownLeft size={21} />
                    </span>
                    <div>
                      <p>Доходы</p>
                      <strong className="income">
                        +{money(report?.total_income || 0)}
                      </strong>
                    </div>
                  </div>
                  <div className="stat">
                    <span className="stat-icon expense">
                      <ArrowUpRight size={21} />
                    </span>
                    <div>
                      <p>Расходы</p>
                      <strong className="expense">
                        −{money(report?.total_expense || 0)}
                      </strong>
                    </div>
                  </div>
                  <div className="stat">
                    <span className="stat-icon">
                      <ChartNoAxesCombined size={21} />
                    </span>
                    <div>
                      <p>Итог периода</p>
                      <strong>{money(report?.net_profit || 0)}</strong>
                    </div>
                  </div>
                </div>
              </section>
              <div className="content-grid">
                <section className="panel">
                  <div className="section-heading">
                    <div>
                      <h2>Ближайшие события</h2>
                      <p>Важные даты всегда перед глазами</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setTab("schedule")}
                      aria-label="Открыть расписание"
                    >
                      <ArrowUpRight size={20} />
                    </button>
                  </div>
                  {upcoming.length ? (
                    upcoming.map((item) => (
                      <div className="event-row" key={item.id}>
                        <div className="date-tile">
                          <strong>
                            {Number(item.next_payment_date.slice(8))}
                          </strong>
                          <span>
                            {new Date(item.next_payment_date + "T12:00:00")
                              .toLocaleDateString("ru-RU", { month: "short" })
                              .replace(".", "")}
                          </span>
                        </div>
                        <div className="event-copy">
                          <strong>{item.title}</strong>
                          <span>
                            {item.next_payment_date < today()
                              ? "Ожидает подтверждения"
                              : item.transaction_type === "income"
                                ? "Ожидаемое поступление"
                                : "Плановое списание"}
                          </span>
                        </div>
                        <b className={item.transaction_type}>
                          {item.transaction_type === "income" ? "+" : "−"}
                          {money(item.amount)}
                        </b>
                      </div>
                    ))
                  ) : (
                    <Empty
                      title="Впереди — чистый лист"
                      body="Добавьте дни зарплаты и подписки. Мы соберём их в одном расписании."
                      action={
                        <button
                          className="text-button"
                          onClick={() => setModal({ type: "schedule" })}
                        >
                          Настроить расписание <ArrowRight size={16} />
                        </button>
                      }
                    />
                  )}
                </section>
                <section className="panel">
                  <div className="section-heading">
                    <div>
                      <h2>Расходы по категориям</h2>
                      <p>За выбранный период</p>
                    </div>
                    <span className="icon-tile">
                      <ListFilter size={18} />
                    </span>
                  </div>
                  {report?.expense_by_category.length ? (
                    <div className="category-list">
                      {report.expense_by_category.slice(0, 5).map((c, i) => (
                        <div className="category-row" key={c.category}>
                          <div>
                            <span>
                              <i
                                style={{
                                  background: [
                                    "#006ee8",
                                    "#4a94ed",
                                    "#7bb4f4",
                                    "#a8cff8",
                                    "#d0e4fc",
                                  ][i],
                                }}
                              />
                              {c.category}
                            </span>
                            <b>{money(c.amount)}</b>
                          </div>
                          <div className="category-track">
                            <i
                              style={{
                                width: `${Math.min(100, (Number(c.amount) / Number(report.total_expense)) * 100)}%`,
                                background: [
                                  "#006ee8",
                                  "#4a94ed",
                                  "#7bb4f4",
                                  "#a8cff8",
                                  "#d0e4fc",
                                ][i],
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="Здесь будет ваша статистика"
                      body="Добавьте первый расход — и увидите, как распределяется бюджет."
                    />
                  )}
                </section>
              </div>
              <section className="panel recent-panel">
                <div className="section-heading">
                  <div>
                    <h2>Последние операции</h2>
                    <p>Небольшие записи. Полная картина.</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setTab("operations")}
                  >
                    Все операции <ArrowRight size={16} />
                  </button>
                </div>
                {report?.transactions.length ? (
                  report.transactions.slice(0, 4).map(txRow)
                ) : (
                  <p className="quiet-copy">
                    За выбранный период записей пока нет. Начните с дохода или
                    расхода.
                  </p>
                )}
              </section>
            </>
          )}
          {tab === "operations" && (
            <section className="panel operations-panel">
              <div className="operations-toolbar">
                <div className="segmented" aria-label="Тип операций">
                  {(
                    [
                      ["all", "Все"],
                      ["income", "Доходы"],
                      ["expense", "Расходы"],
                    ] as const
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      aria-pressed={filter === value}
                      onClick={() => setFilter(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {PeriodControl}
                <button
                  className="button subtle import-button"
                  onClick={() => setModal({ type: "import" })}
                >
                  <Download size={17} />
                  Загрузить выписку
                </button>
              </div>
              <label className="search-field">
                <Search size={18} />
                <input
                  aria-label="Поиск операций"
                  placeholder="Найти по названию или категории"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {search && (
                  <button
                    className="icon-button"
                    aria-label="Очистить поиск"
                    onClick={() => setSearch("")}
                  >
                    <X size={16} />
                  </button>
                )}
              </label>
              <div className="list-caption">
                <span>{transactions.length} операций</span>
                <span>Сумма</span>
              </div>
              {transactions.length ? (
                transactions.map(txRow)
              ) : (
                <Empty
                  title="Операций пока нет"
                  body="Добавьте запись вручную или загрузите выписку. Если вы используете фильтр, попробуйте его изменить."
                  action={
                    <button
                      className="button primary"
                      onClick={() => setModal({ type: "transaction" })}
                    >
                      <Plus size={17} />
                      Добавить операцию
                    </button>
                  }
                />
              )}
            </section>
          )}
          {tab === "schedule" && (
            <>
              <div className="schedule-summary">
                <div>
                  <span className="income">Поступления в месяц</span>
                  <strong>
                    {money(
                      active
                        .filter((s) => s.transaction_type === "income")
                        .reduce((n, s) => n + Number(s.amount), 0),
                    )}
                  </strong>
                </div>
                <div>
                  <span className="expense">Обязательные расходы</span>
                  <strong>
                    {money(
                      active
                        .filter((s) => s.transaction_type === "expense")
                        .reduce((n, s) => n + Number(s.amount), 0),
                    )}
                  </strong>
                </div>
              </div>
              <div className="schedule-note">
                <CircleHelp size={18} />
                <p>
                  Это план. Подтвердите поступление или списание, когда оно
                  произойдёт. Только после этого сумма попадёт в операции и
                  изменит остаток.
                </p>
              </div>
              <div className="segmented schedule-filter">
                {(
                  [
                    ["all", "Все события"],
                    ["income", "Доходы"],
                    ["expense", "Расходы"],
                  ] as const
                ).map(([v, label]) => (
                  <button
                    key={v}
                    aria-pressed={scheduleFilter === v}
                    onClick={() => setScheduleFilter(v)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="schedule-grid">
                {[...schedule]
                  .sort(
                    (a, b) =>
                      Number(b.is_active) - Number(a.is_active) ||
                      a.next_payment_date.localeCompare(b.next_payment_date),
                  )
                  .filter(
                    (s) =>
                      scheduleFilter === "all" ||
                      s.transaction_type === scheduleFilter,
                  )
                  .map((item) => (
                    <article
                      className={`schedule-card ${!item.is_active ? "paused" : ""}`}
                      key={item.id}
                    >
                      <div className="schedule-card-top">
                        <span
                          className={`transaction-icon ${item.transaction_type}`}
                        >
                          {item.transaction_type === "income" ? (
                            <ArrowDownLeft size={22} />
                          ) : (
                            <ArrowUpRight size={22} />
                          )}
                        </span>
                        <span className="schedule-tag">
                          {!item.is_active
                            ? "На паузе"
                            : item.next_payment_date < today()
                              ? "Ожидает подтверждения"
                              : displayDate(item.next_payment_date)}
                        </span>
                        <button
                          className="icon-button"
                          aria-label={`Изменить расписание: ${item.title}`}
                          onClick={() => setModal({ type: "schedule", item })}
                        >
                          <Ellipsis size={21} />
                        </button>
                      </div>
                      <h2>{item.title}</h2>
                      <p>
                        {item.category} · каждый месяц, {item.billing_day}-го
                      </p>
                      <strong
                        className={`schedule-amount ${item.transaction_type}`}
                      >
                        {item.transaction_type === "income" ? "+" : "−"}
                        {money(item.amount)}
                      </strong>
                      <div className="schedule-card-actions">
                        <button
                          className="button subtle"
                          disabled={busy || !item.is_active}
                          onClick={() =>
                            void perform(
                              () =>
                                PersonalService.confirmSchedule(
                                  item.id,
                                  item.next_payment_date,
                                  today(),
                                ),
                              item.transaction_type === "income"
                                ? "Доход подтверждён"
                                : "Расход подтверждён",
                            )
                          }
                        >
                          <Check size={16} />
                          {item.transaction_type === "income"
                            ? "Деньги получены"
                            : "Оплачено"}
                        </button>
                        <button
                          className="text-button muted"
                          disabled={busy}
                          onClick={() =>
                            void perform(
                              () => FinanceService.toggleRecurring(item.id),
                              item.is_active
                                ? "Событие приостановлено"
                                : "Событие возобновлено",
                            )
                          }
                        >
                          {item.is_active ? "Пауза" : "Возобновить"}
                        </button>
                      </div>
                    </article>
                  ))}
              </div>
              {!schedule.length && (
                <section className="panel">
                  <Empty
                    title="Начнём с дня зарплаты?"
                    body="Укажите название, сумму и день поступления. Аванс можно добавить отдельным событием."
                    action={
                      <button
                        className="button primary"
                        onClick={() =>
                          setModal({ type: "schedule", kind: "income" })
                        }
                      >
                        <Plus size={17} />
                        Добавить доход
                      </button>
                    }
                  />
                </section>
              )}
            </>
          )}
          {tab === "profile" && (
            <Profile
              balance={balance.opening_balance}
              onBalance={async (value) => {
                await PersonalService.setBalance(value);
                await load();
                setNotice("Начальный остаток сохранён");
              }}
              onPassword={async (current, next) => {
                await PersonalService.changePassword(current, next);
                setNotice(
                  "Пароль изменён. Другие устройства вышли из аккаунта.",
                );
              }}
              onLogout={logout}
            />
          )}
          <footer className="page-footer">
            <span>Мои финансы · ваше личное пространство</span>
            <span>
              <ShieldCheck size={13} />
              Личный доступ
            </span>
          </footer>
        </main>
      </div>
      <nav className="bottom-nav" aria-label="Навигация на телефоне">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            aria-current={tab === id ? "page" : undefined}
            onClick={() => setTab(id)}
          >
            <Icon size={21} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      {modal && (
        <ModalFrame
          title={
            modal.type === "transaction"
              ? modal.item
                ? "Изменить операцию"
                : "Новая операция"
              : modal.type === "schedule"
                ? modal.item
                  ? "Изменить событие"
                  : "Новое событие"
                : modal.type === "period"
                  ? "Период отчёта"
                  : modal.type === "import"
                    ? "Выписка из банка"
                    : "Удалить запись?"
          }
          onClose={() => {
            if (!busy) {
              setModal(null);
              setError("");
            }
          }}
        >
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          {modal.type === "transaction" && (
            <TransactionForm
              item={modal.item}
              kind={modal.kind}
              busy={busy}
              onSave={(data) =>
                perform(
                  () =>
                    modal.item
                      ? FinanceService.updateTransaction(modal.item.id, data)
                      : FinanceService.createTransaction(data),
                  "Операция сохранена",
                )
              }
            />
          )}
          {modal.type === "schedule" && (
            <ScheduleForm
              item={modal.item}
              kind={modal.kind}
              busy={busy}
              onDelete={() =>
                modal.item &&
                setModal({
                  type: "delete",
                  item: modal.item,
                  source: "schedule",
                })
              }
              onSave={(data) =>
                perform(
                  () =>
                    modal.item
                      ? PersonalService.updateSchedule(modal.item.id, data)
                      : FinanceService.createRecurring(data),
                  "Расписание сохранено",
                )
              }
            />
          )}
          {modal.type === "period" && (
            <PeriodForm
              value={period}
              onApply={(value) => {
                setPeriod(value);
                setModal(null);
              }}
            />
          )}
          {modal.type === "import" && (
            <StatementImport
              onSuccess={() => {
                void load();
                setNotice("Выписка импортирована");
              }}
            />
          )}
          {modal.type === "delete" && (
            <>
              <p className="dialog-copy">
                {modal.source === "transaction"
                  ? "Операция будет удалена, а суммы в обзоре пересчитаны."
                  : "Событие исчезнет из расписания. Уже подтверждённые операции останутся в истории."}
              </p>
              <div className="dialog-actions">
                <button
                  className="button subtle"
                  disabled={busy}
                  onClick={() => setModal(null)}
                >
                  Отмена
                </button>
                <button
                  className="button danger"
                  disabled={busy}
                  onClick={() =>
                    void perform(
                      () =>
                        modal.source === "transaction"
                          ? FinanceService.deleteTransaction(modal.item.id)
                          : FinanceService.deleteRecurring(modal.item.id),
                      "Запись удалена",
                    )
                  }
                >
                  {busy ? "Удаляем…" : "Удалить"}
                </button>
              </div>
            </>
          )}
        </ModalFrame>
      )}
    </div>
  );
}

function KindControl({
  kind,
  onChange,
}: {
  kind: Kind;
  onChange: (k: Kind) => void;
}) {
  return (
    <div className="kind-control">
      <button
        type="button"
        className="expense"
        aria-pressed={kind === "expense"}
        onClick={() => onChange("expense")}
      >
        <ArrowUpRight size={18} />
        Расход
      </button>
      <button
        type="button"
        className="income"
        aria-pressed={kind === "income"}
        onClick={() => onChange("income")}
      >
        <ArrowDownLeft size={18} />
        Доход
      </button>
    </div>
  );
}
function TransactionForm({
  item,
  kind: initialKind,
  busy,
  onSave,
}: {
  item?: TransactionDTO;
  kind?: Kind;
  busy: boolean;
  onSave: (data: unknown) => Promise<void>;
}) {
  const [kind, setKind] = useState<Kind>(
    item?.transaction_type || initialKind || "expense",
  );
  const [amount, setAmount] = useState(String(item?.amount || ""));
  const [category, setCategory] = useState(item?.category || "");
  const [description, setDescription] = useState(
    item?.description === "Ручной ввод" ? "" : item?.description || "",
  );
  const [date, setDate] = useState(
    item?.transaction_date.slice(0, 10) || today(),
  );
  return (
    <form
      className="entry-form"
      onSubmit={(e) => {
        e.preventDefault();
        void onSave({
          transaction_type: kind,
          amount,
          category: category.trim(),
          description: description.trim(),
          transaction_date: date + "T00:00:00Z",
        });
      }}
    >
      <KindControl kind={kind} onChange={setKind} />
      <label className="amount-field">
        Сумма, ₽
        <input
          aria-label="Сумма операции"
          type="number"
          min="0.01"
          max="9999999999.99"
          step="0.01"
          inputMode="decimal"
          placeholder="0"
          required
          autoFocus
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </label>
      <label>
        Категория
        <input
          list="categories"
          placeholder={
            kind === "income" ? "Например, зарплата" : "Например, продукты"
          }
          required
          maxLength={64}
          pattern=".*\S.*"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      </label>
      <datalist id="categories">
        {(kind === "income"
          ? ["Зарплата", "Подработка", "Подарки", "Другой доход"]
          : [
              "Продукты",
              "Транспорт",
              "Дом",
              "Подписки",
              "Здоровье",
              "Покупки",
              "Кафе",
              "Другие расходы",
            ]
        ).map((c) => (
          <option key={c}>{c}</option>
        ))}
      </datalist>
      <label>
        Дата
        <input
          type="date"
          required
          max={today()}
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
      </label>
      <label>
        Комментарий <span className="optional">необязательно</span>
        <input
          placeholder="Что это было?"
          maxLength={2000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <button className="button primary full" disabled={busy}>
        {busy ? "Сохраняем…" : "Сохранить операцию"}
        <ArrowRight size={18} />
      </button>
    </form>
  );
}
function ScheduleForm({
  item,
  kind: initialKind,
  busy,
  onSave,
  onDelete,
}: {
  item?: RecurringResponse;
  kind?: Kind;
  busy: boolean;
  onSave: (data: unknown) => Promise<void>;
  onDelete: () => void;
}) {
  const [kind, setKind] = useState<Kind>(
    item?.transaction_type || initialKind || "income",
  );
  const [name, setName] = useState(item?.title || "");
  const [amount, setAmount] = useState(String(item?.amount || ""));
  const [day, setDay] = useState(String(item?.billing_day || 10));
  const [date, setDate] = useState(
    item?.next_payment_date || nextOccurrence(Number(day)),
  );
  const [category, setCategory] = useState(item?.category || "");
  return (
    <form
      className="entry-form"
      onSubmit={(e) => {
        e.preventDefault();
        void onSave({
          title: name.trim(),
          amount,
          transaction_type: kind,
          category:
            category.trim() || (kind === "income" ? "Зарплата" : "Подписки"),
          billing_day: Number(day),
          next_payment_date: date,
        });
      }}
    >
      <KindControl kind={kind} onChange={setKind} />
      <label>
        Название
        <input
          autoFocus
          placeholder={
            kind === "income"
              ? "Зарплата или аванс"
              : "Интернет, аренда, подписка"
          }
          maxLength={128}
          required
          pattern=".*\S.*"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label>
        Сумма, ₽
        <input
          type="number"
          min="0.01"
          max="9999999999.99"
          step="0.01"
          inputMode="decimal"
          required
          placeholder="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </label>
      <div className="form-grid">
        <label>
          День месяца
          <input
            type="number"
            min="1"
            max="31"
            required
            value={day}
            onChange={(e) => {
              setDay(e.target.value);
              const n = Number(e.target.value);
              if (n >= 1 && n <= 31) setDate(nextOccurrence(n));
            }}
          />
        </label>
        <label>
          Ближайшая дата
          <input
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
      </div>
      <p className="field-hint">
        Если в месяце нет этого числа, событие попадёт на последний день месяца.
      </p>
      <label>
        Категория
        <input
          placeholder={kind === "income" ? "Зарплата" : "Подписки"}
          maxLength={64}
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
      </label>
      <button className="button primary full" disabled={busy}>
        {busy ? "Сохраняем…" : "Сохранить событие"}
        <Check size={18} />
      </button>
      {item && (
        <button
          type="button"
          className="text-button expense centered"
          disabled={busy}
          onClick={onDelete}
        >
          <Trash2 size={16} />
          Удалить событие
        </button>
      )}
    </form>
  );
}
function Profile({
  balance,
  onBalance,
  onPassword,
  onLogout,
}: {
  balance: string;
  onBalance: (v: string) => Promise<void>;
  onPassword: (c: string, n: string) => Promise<void>;
  onLogout: () => Promise<void>;
}) {
  const { account } = useAuth();
  const [opening, setOpening] = useState(balance);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const submit = async (
    e: FormEvent,
    section: string,
    action: () => Promise<void>,
  ) => {
    e.preventDefault();
    setError("");
    setBusy(section);
    try {
      await action();
    } catch (err) {
      setError(
        errorMessage(
          err,
          err instanceof Error ? err.message : "Не удалось сохранить настройки",
        ),
      );
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="profile-grid">
      <section className="panel profile-identity">
        <span className="profile-avatar">
          {account?.login.slice(0, 1).toUpperCase()}
        </span>
        <h2>{account?.login}</h2>
        <p>Ваш личный финансовый дневник</p>
        <span className="account-status">
          <span />
          Аккаунт подключён
        </span>
        <button
          className="button subtle"
          disabled={!!busy}
          onClick={() =>
            void submit(
              { preventDefault: () => {} } as FormEvent,
              "logout",
              onLogout,
            )
          }
        >
          <LogOut size={17} />
          Выйти из аккаунта
        </button>
      </section>
      <div className="profile-settings">
        {error && (
          <p className="alert" role="alert">
            {error}
          </p>
        )}
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Начальный остаток</h2>
              <p>Сколько денег было до первой записи</p>
            </div>
            <Wallet size={20} />
          </div>
          <form
            className="entry-form"
            onSubmit={(e) =>
              void submit(e, "balance", () => onBalance(opening))
            }
          >
            <label>
              Начальный остаток, ₽
              <input
                type="number"
                min="-9999999999.99"
                max="9999999999.99"
                step="0.01"
                required
                inputMode="decimal"
                value={opening}
                onChange={(e) => setOpening(e.target.value)}
              />
            </label>
            <p className="field-hint">
              К этой сумме прибавляются все внесённые доходы и вычитаются
              расходы. Сам остаток не считается доходом.
            </p>
            <button className="button primary" disabled={!!busy}>
              {busy === "balance" ? "Сохраняем…" : "Сохранить остаток"}
            </button>
          </form>
        </section>
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Пароль и безопасность</h2>
              <p>Для смены понадобится текущий пароль</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <form
            className="entry-form"
            onSubmit={(e) =>
              void submit(e, "password", async () => {
                if (next !== repeat) throw new Error("Пароли не совпадают");
                await onPassword(current, next);
                setCurrent("");
                setNext("");
                setRepeat("");
              })
            }
          >
            <label>
              Текущий пароль
              <input
                type="password"
                autoComplete="current-password"
                maxLength={128}
                required
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <label>
              Новый пароль
              <div className="password-input">
                <input
                  type={visible ? "text" : "password"}
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  placeholder="Не менее 8 символов"
                  required
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={visible ? "Скрыть пароль" : "Показать пароль"}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </label>
            <label>
              Повторите новый пароль
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                required
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
              />
            </label>
            <p className="field-hint">
              После смены пароля другие устройства выйдут из аккаунта. На этом
              устройстве вход сохранится.
            </p>
            <button className="button primary" disabled={!!busy}>
              {busy === "password" ? "Меняем пароль…" : "Изменить пароль"}
            </button>
          </form>
        </section>
        <RecoverySettings />
      </div>
    </div>
  );
}
