// frontend/src/api/client.ts
import axios from 'axios';
import WebApp from '@twa-dev/sdk';

import type { 
  MonthlyReportResponse, 
  AIAdvisorResponse, 
  SalarySummaryResponse,
  SavingsGoalResponse,
  RecurringResponse,
  CreditDebtResponse 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getTelegramUserId = (): number => {
  if (typeof window !== 'undefined' && WebApp?.initDataUnsafe?.user?.id) {
    return WebApp.initDataUnsafe.user.id;
  }
  return 1; 
};

api.interceptors.request.use((config) => {
  const userId = getTelegramUserId();
  if (!config.params) config.params = {};
  if (!config.params.user_id) config.params.user_id = userId;
  return config;
});

export const FinanceService = {
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
    const targetId = userId || getTelegramUserId();
    const { data } = await api.post(`/statements/upload?user_id=${targetId}`, formData, {
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
  syncUser: async (userData: any) => {
    const { data } = await api.post('/users/sync', {
      id: userData.id,
      username: userData.username,
      first_name: userData.first_name
    });
    return data;
  },
};

