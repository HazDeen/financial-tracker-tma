export type PeriodMode = "month" | "day" | "range";
export interface ReportPeriod {
  mode: PeriodMode;
  start: string;
  end: string;
}
export const MIN_DATE = "2000-01-01";
export const MAX_DATE = "2100-12-31";
export function todayISO() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
const iso = (date: Date) => date.toISOString().slice(0, 10);
export function monthPeriod(month: string): ReportPeriod {
  const [year, number] = month.split("-").map(Number);
  return {
    mode: "month",
    start: month + "-01",
    end: iso(new Date(Date.UTC(year, number, 0))),
  };
}
export function validPeriod(period: ReportPeriod) {
  const validDate = (s: string) =>
    /^\d{4}-\d{2}-\d{2}$/.test(s) &&
    !Number.isNaN(Date.parse(s)) &&
    iso(new Date(s)) === s;
  return (
    validDate(period.start) &&
    validDate(period.end) &&
    period.start >= MIN_DATE &&
    period.end <= MAX_DATE &&
    period.start <= period.end
  );
}
export function shiftPeriod(
  period: ReportPeriod,
  direction: number,
): ReportPeriod {
  let next: ReportPeriod;
  if (period.mode === "month") {
    const [year, month] = period.start.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1 + direction, 1));
    next = monthPeriod(iso(date).slice(0, 7));
  } else {
    const days =
      (Date.parse(period.end) - Date.parse(period.start)) / 86400000 + 1;
    next = {
      ...period,
      start: iso(
        new Date(Date.parse(period.start) + direction * days * 86400000),
      ),
      end: iso(new Date(Date.parse(period.end) + direction * days * 86400000)),
    };
  }
  return validPeriod(next) ? next : period;
}
export function periodLabel(period: ReportPeriod) {
  const format = (date: string, options: Intl.DateTimeFormatOptions) =>
    new Date(date + "T12:00:00")
      .toLocaleDateString("ru-RU", options)
      .replace(" г.", "");
  if (period.mode === "month")
    return format(period.start, { month: "long", year: "numeric" });
  if (period.start === period.end)
    return format(period.start, {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  if (period.start.slice(0, 7) === period.end.slice(0, 7)) {
    return `${Number(period.start.slice(8))}–${format(period.end, { day: "numeric", month: "long", year: "numeric" })}`;
  }
  return `${format(period.start, { day: "numeric", month: "short", ...(period.start.slice(0, 4) !== period.end.slice(0, 4) ? { year: "numeric" as const } : {}) })} — ${format(period.end, { day: "numeric", month: "short", year: "numeric" })}`;
}
