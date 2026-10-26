import { useState } from "react";
import { ArrowRight } from "lucide-react";
import {
  MAX_DATE,
  MIN_DATE,
  monthPeriod,
  shiftPeriod,
  todayISO,
  validPeriod,
} from "../lib/period";
import type { ReportPeriod, PeriodMode } from "../lib/period";

export function PeriodForm({
  value,
  onApply,
}: {
  value: ReportPeriod;
  onApply: (value: ReportPeriod) => void;
}) {
  const [mode, setMode] = useState<PeriodMode>(value.mode);
  const [month, setMonth] = useState(value.start.slice(0, 7));
  const [day, setDay] = useState(
    value.mode === "day" ? value.start : todayISO(),
  );
  const [start, setStart] = useState(value.start);
  const [end, setEnd] = useState(value.end);
  const [error, setError] = useState("");
  const now = todayISO();
  const dayPeriod: ReportPeriod = { mode: "day", start: now, end: now };
  return (
    <form
      className="entry-form period-form"
      onSubmit={(event) => {
        event.preventDefault();
        const candidate =
          mode === "month"
            ? monthPeriod(month)
            : mode === "day"
              ? { mode, start: day, end: day }
              : { mode, start, end };
        if (!validPeriod(candidate)) {
          setError(
            "Проверьте даты: окончание периода должно быть не раньше его начала.",
          );
          return;
        }
        onApply(candidate);
      }}
    >
      <div className="segmented period-modes" aria-label="Вид периода">
        {(
          [
            ["month", "Месяц"],
            ["day", "День"],
            ["range", "Диапазон"],
          ] as const
        ).map(([id, label]) => (
          <button
            type="button"
            key={id}
            aria-pressed={mode === id}
            onClick={() => {
              setMode(id);
              setError("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {mode === "month" && (
        <label>
          Месяц отчёта
          <input
            type="month"
            min="2000-01"
            max="2100-12"
            required
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          />
        </label>
      )}
      {mode === "day" && (
        <label>
          День отчёта
          <input
            type="date"
            min={MIN_DATE}
            max={MAX_DATE}
            required
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </label>
      )}
      {mode === "range" && (
        <div className="period-dates">
          <label>
            Дата начала
            <input
              type="date"
              min={MIN_DATE}
              max={MAX_DATE}
              required
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            Дата окончания (включительно)
            <input
              type="date"
              min={MIN_DATE}
              max={MAX_DATE}
              required
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
        </div>
      )}
      <p className="field-hint">
        В статистику и историю попадут все операции за выбранные дни, включая
        день окончания. Для сравнения используйте стрелки рядом с датами: они переключают на соседний период той же длительности.
      </p>
      <div className="period-presets" aria-label="Быстрый выбор периода">
        <button type="button" onClick={() => onApply(dayPeriod)}>
          Сегодня
        </button>
        <button
          type="button"
          onClick={() => onApply(shiftPeriod(dayPeriod, -1))}
        >
          Вчера
        </button>
        <button
          type="button"
          onClick={() => {
            const beginning = new Date(now + "T00:00:00Z");
            beginning.setUTCDate(beginning.getUTCDate() - 6);
            onApply({
              mode: "range",
              start: beginning.toISOString().slice(0, 10),
              end: now,
            });
          }}
        >
          7 дней
        </button>
        <button
          type="button"
          onClick={() => onApply(monthPeriod(now.slice(0, 7)))}
        >
          Этот месяц
        </button>
      </div>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <button className="button primary full">
        Показать операции
        <ArrowRight size={18} />
      </button>
    </form>
  );
}
