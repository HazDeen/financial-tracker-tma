// frontend/src/api/client.ts
import axios from 'axios';


import type { 
  MonthlyReportResponse, 
  AIAdvisorResponse, 
  SalarySummaryResponse,
  SavingsGoalResponse,
  RecurringResponse,
  CreditDebtResponse 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Account { id: number; login: string }
let currentAccount: Account | null = null;
export const setCurrentAccount = (account: Account | null) => { currentAccount = account; };
export const getCurrentUserId = (): number => currentAccount?.id ?? 0;
export const AuthService = {
  me: async (): Promise<Account> => (await api.get('/auth/me')).data,
  login: async (login: string, password: string): Promise<Account> => (await api.post('/auth/login', { login, password })).data,
  register: async (login: string, password: string): Promise<Account> => (await api.post('/auth/register', { login, password })).data,
  logout: async () => { await api.post('/auth/logout'); },
};
export const errorMessage = (error: unknown, fallback = 'Не удалось выполнить запрос') => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return 'Проверьте заполнение полей: логин от 3 символов, пароль от 8 символов, сумма больше нуля.';
    if (!error.response) return 'Нет связи с сервером. Проверьте подключение и повторите попытку.';
  }
  return fallback;
};
api.interceptors.request.use((config) => {
  // Пользователя определяет только серверная сессия.
  if (config.params) delete config.params.user_id;
  return config;
});
api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
    window.dispatchEvent(new Event('session-expired'));
  }
  return Promise.reject(error);
});

export const FinanceService = {
  previewStatement: async (file: File) => {
    const body = new FormData(); body.append('file', file);
    return (await api.post('/statements/preview', body, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  },
  updateTransaction: async (id: number, payload: unknown) => (await api.put(`/transactions/${id}`, payload)).data,
  deleteTransaction: async (id: number) => { await api.delete(`/transactions/${id}`); },
  getMonthlyReport: async (year: number, month: number, userId?: number): Promise<MonthlyReportResponse> => {
    const { data } = await api.get('/analytics/monthly', { params: { year, month, user_id: userId } });
    return data;
  },
  getRecurring: async (userId?: number): Promise<RecurringResponse[]> => {
    const { data } = await api.get('/recurring/', { params: { user_id: userId } });
    return data;
  },
  getDebts: async (userId?: number): Promise<CreditDebtResponse[]> => {
    const { data } = await api.get('/debts/', { params: { user_id: userId } });
    return data;
  },
  getSavingsGoals: async (_userId?: number): Promise<SavingsGoalResponse[]> => {
    return [];
  },
  getAIAdvice: async (year: number, month: number, userId?: number): Promise<AIAdvisorResponse> => {
    const { data } = await api.get('/ai-advisor/analyze', { params: { year, month, user_id: userId } });
    return data;
  },
  getSalarySummary: async (year: number, month: number, userId?: number): Promise<SalarySummaryResponse> => {
    const { data } = await api.get('/shifts/summary', { params: { year, month, user_id: userId } });
    return data;
  },
  uploadStatement: async (file: File, userId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    void userId;
    const { data } = await api.post(`/statements/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  createTransaction: async (payload: any, userId?: number) => {
    const { data } = await api.post('/transactions/', payload, { params: { user_id: userId } });
    return data;
  },

  // --- Создание и экшены ---
  createShift: async (payload: any, userId?: number) => {
    const { data } = await api.post('/shifts/', payload, { params: { user_id: userId } });
    return data;
  },
  createRecurring: async (payload: any, userId?: number) => {
    const { data } = await api.post('/recurring/', payload, { params: { user_id: userId } });
    return data;
  },
  createDebt: async (payload: any, userId?: number) => {
    const { data } = await api.post('/debts/', payload, { params: { user_id: userId } });
    return data;
  },
  createSavingsGoal: async (payload: any, userId?: number) => {
    const { data } = await api.post('/actions/savings/', payload, { params: { user_id: userId } });
    return data;
  },
  markShiftPaid: async (shiftId: number, userId?: number) => {
    const { data } = await api.post(`/actions/shifts/${shiftId}/pay`, null, { params: { user_id: userId } });
    return data;
  },
  payDebt: async (debtId: number, amount: number, userId?: number) => {
    const { data } = await api.post(`/actions/debts/${debtId}/pay`, { amount }, { params: { user_id: userId } });
    return data;
  },

  // --- Удаление записей ---
  deleteShift: async (id: number, userId?: number) => {
    await api.delete(`/shifts/${id}`, { params: { user_id: userId } });
  },
  deleteRecurring: async (id: number, userId?: number) => {
    await api.delete(`/recurring/${id}`, { params: { user_id: userId } });
  },
  deleteDebt: async (id: number, userId?: number) => {
    await api.delete(`/debts/${id}`, { params: { user_id: userId } });
  },
  deleteSavingsGoal: async (id: number, userId?: number) => {
    await api.delete(`/actions/savings/${id}`, { params: { user_id: userId } });
  },
  toggleRecurring: async (id: number, userId?: number) => {
    const { data } = await api.patch(`/recurring/${id}/toggle`, null, { params: { user_id: userId } });
    return data;
  },

};

