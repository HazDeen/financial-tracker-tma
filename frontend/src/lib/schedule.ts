import type { RecurringResponse } from "../types";

/** Include every pending monthly occurrence through the next income, even after a long absence. */
export function plannedExpenses(
  items: RecurringResponse[],
  until: string | undefined,
  currentDate: string,
): number {
  const expenses = items.filter(
    (item) => item.is_active && item.transaction_type === "expense",
  );
  if (!until)
    return expenses.reduce((sum, item) => sum + Number(item.amount), 0);
  const horizon = until > currentDate ? until : currentDate;
  return expenses.reduce((sum, item) => {
    let date = item.next_payment_date;
    // Supported report years are 2000–2100; this bound also protects malformed dates.
    for (
      let occurrence = 0;
      date <= horizon && occurrence < 1212;
      occurrence++
    ) {
      sum += Number(item.amount);
      const [year, month] = date.split("-").map(Number);
      const next = new Date(
        year,
        month,
        Math.min(item.billing_day, new Date(year, month + 1, 0).getDate()),
        12,
      );
      date = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
    }
    return sum;
  }, 0);
}
