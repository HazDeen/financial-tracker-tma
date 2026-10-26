/** All monetary inputs are rubles. Calculations are estimates, rounded only for display. */
export const taxSource = 'https://www.nalog.gov.ru/nu/';
export const generalBrackets = [
  { cap: 2_400_000, rate: 0.13 }, { cap: 5_000_000, rate: 0.15 },
  { cap: 20_000_000, rate: 0.18 }, { cap: 50_000_000, rate: 0.20 },
  { cap: Infinity, rate: 0.22 },
];
export const investmentBrackets = [{ cap: 2_400_000, rate: 0.13 }, { cap: Infinity, rate: 0.15 }];
export function nonnegative(value: number, name = 'Сумма') {
  if (!Number.isFinite(value) || value < 0 || value > 1e15) throw new Error(`${name}: введите число от 0 до 1 000 трлн`);
  return value;
}
export function taxBreakdown(income: number, investment = false) {
  nonnegative(income);
  let floor = 0;
  return (investment ? investmentBrackets : generalBrackets).map(({ cap, rate }) => {
    const base = Math.max(0, Math.min(income, cap) - floor);
    floor = cap;
    return { base, rate, tax: base * rate };
  }).filter(row => row.base > 0);
}
export function incomeTax(income: number, investment = false) {
  return taxBreakdown(income, investment).reduce((sum, row) => sum + row.tax, 0);
}
export function deposit(principal: number, annualRate: number, months: number, compound: boolean) {
  nonnegative(principal); nonnegative(annualRate, 'Ставка');
  if (annualRate > 100 || !Number.isInteger(months) || months < 1 || months > 600) throw new Error('Ставка — до 100%, срок — от 1 до 600 целых месяцев');
  const monthly = principal * annualRate / 1200;
  const interest = compound ? principal * (Math.pow(1 + annualRate / 1200, months) - 1) : monthly * months;
  return { monthly, interest, total: principal + interest };
}
export function coupons(nominal: number, annualRate: number, quantity: number, payments: number, otherIncome: number) {
  [nominal, annualRate, quantity, otherIncome].forEach(n => nonnegative(n));
  if (annualRate > 100 || !Number.isInteger(quantity) || quantity < 1 || quantity > 1e9 || !Number.isInteger(payments) || payments < 1 || payments > 12) throw new Error('Проверьте ставку, число облигаций и выплат');
  const gross = nominal * annualRate / 100 * quantity;
  if (gross + otherIncome > 1e15) throw new Error('Суммарный доход слишком велик');
  const tax = incomeTax(gross + otherIncome, true) - incomeTax(otherIncome, true);
  return { gross, tax, net: gross - tax, perPayment: gross / payments };
}
export const figureKeys = ['marketCap', 'netIncome', 'revenue', 'equity', 'averageEquity', 'debt', 'cash', 'ebitda'] as const;
export type FigureKey = typeof figureKeys[number];
export type Figures = Record<FigureKey, string>;
export const emptyFigures = (): Figures => Object.fromEntries(figureKeys.map(k => [k, ''])) as Figures;
export function readNumber(value: string): number | null {
  if (!value.trim()) return null;
  const normalized = value.trim().replace(/\s/g, '').replace(',', '.');
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) return NaN;
  return Number(normalized);
}
export function figureValues(figures: Figures) {
  return Object.fromEntries(figureKeys.map(key => {
    const value = readNumber(figures[key]);
    if (value !== null && (!Number.isFinite(value) || Math.abs(value) > 1e15 || (['marketCap', 'revenue', 'debt', 'cash'].includes(key) && value < 0))) throw new Error('Проверьте показатели: только конечные числа; капитализация, выручка, долг и деньги не могут быть отрицательными');
    return [key, value];
  })) as Record<FigureKey, number | null>;
}
export function multiples(figures: Figures) {
  const v = figureValues(figures);
  const ratio = (a: number | null, b: number | null, positive = true) => a === null || b === null || b === 0 || (positive && b < 0) ? null : a / b;
  const ev = v.marketCap === null || v.debt === null || v.cash === null ? null : v.marketCap + v.debt - v.cash;
  const roe = ratio(v.netIncome, v.averageEquity);
  return { pe: ratio(v.marketCap, v.netIncome), ps: ratio(v.marketCap, v.revenue), pb: ratio(v.marketCap, v.equity), evEbitda: ratio(ev, v.ebitda), roe: roe === null ? null : roe * 100 };
}
