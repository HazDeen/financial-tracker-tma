import { api } from './client';
export interface SavedDeposit {
  id: number; title: string; principal: string; annual_rate: string; months: number;
  opened_on: string; is_active: boolean; monthly_income: string; accrued_income: string;
  next_payment_date: string | null; ends_on: string;
}
export interface DepositInput { title: string; principal: number; annual_rate: number; months: number; opened_on: string }
export const Deposits = {
  list: async (): Promise<SavedDeposit[]> => (await api.get('/deposits')).data,
  create: async (input: DepositInput): Promise<SavedDeposit> => (await api.post('/deposits', input)).data,
  close: async (id: number): Promise<SavedDeposit> => (await api.post(`/deposits/${id}/close`)).data,
};
