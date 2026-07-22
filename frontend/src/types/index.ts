// frontend/src/types/index.ts

export interface CategorySummary {
  category: string;
  amount: number | string;
  percentage: number;
}

export interface TopCategory {
  category: string;
  amount: number | string;
}

export interface TransactionDTO {
  id: number;
  amount: number | string;
  currency: string;
  transaction_type: 'income' | 'expense';
  category: string;
  description?: string;
  transaction_date: string;
}

export interface MonthlyReportResponse {
  year: number;
  month: number;
  total_income: number | string;
  total_expense: number | string;
  net_profit: number | string;
  top_expense_categories: TopCategory[];
  income_by_category: CategorySummary[];
  expense_by_category: CategorySummary[];
  transactions: TransactionDTO[];
}

export interface GoalProgressBarWidget {
  type: 'goal_progress';
  title: string;
  current_amount: number;
  target_amount: number;
  recommendation: string;
}

export interface CategoryLimitWidget {
  type: 'category_limit';
  category: string;
  spent_amount: number;
  recommended_limit: number;
  severity: 'normal' | 'warning' | 'critical';
}

export type AIWidget = GoalProgressBarWidget | CategoryLimitWidget;

export interface AIAdvisorResponse {
  year: number;
  month: number;
  markdown_insights: string;
  widgets: AIWidget[];
}

export interface WorkShiftResponse {
  id: number;
  user_id: number;
  shift_date: string;
  hours_worked: number | string;
  hourly_rate: number | string;
  total_earned: number | string;
  is_paid: boolean;
}

export interface SalarySummaryResponse {
  year: number;
  month: number;
  total_shifts: number;
  total_hours: number | string;
  total_earned: number | string;
  total_paid: number | string;
  unpaid_balance: number | string;
  shifts: WorkShiftResponse[];
}

export interface SavingsGoalResponse {
  id: number;
  user_id: number;
  title: string;
  target_amount: number | string;
  monthly_contribution: number | string;
  current_amount: number | string;
  is_completed: boolean;
}

export interface RecurringResponse {
  id: number;
  user_id: number;
  title: string;
  amount: number | string;
  billing_day: number;
  transaction_type: 'expense' | 'income';
  is_active: boolean;
}

export interface CreditDebtResponse {
  id: number;
  user_id: number;
  title: string;
  total_amount: number | string;
  current_balance: number | string;
  interest_rate?: number | null;
  is_closed: boolean;
}

export type ActionModalType = 'statement' | 'shift' | 'recurring' | 'debt' | 'savings' | 'transaction' | null;