import { api } from './client';
import type { FigureKey } from '../lib/finance-tools';
export interface CompanyReport {
  id: number; company: string; period: string; filename: string; size: number;
  metrics: Record<FigureKey, string | null>; created_at: string;
}
export const CompanyReports = {
  extract: async (file: File, valueColumn = 0): Promise<{ metrics: Partial<Record<FigureKey, string>>; warnings: string[]; scale: string }> => {
    const data = new FormData(); data.append('file', file); data.append('value_column', String(valueColumn));
    return (await api.post('/company-reports/extract', data, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  },
  list: async (): Promise<CompanyReport[]> => (await api.get('/company-reports')).data,
  upload: async (company: string, period: string, file: File, metrics: Record<FigureKey, number | null>): Promise<CompanyReport> => {
    const data = new FormData();
    data.append('company', company); data.append('period', period); data.append('file', file); data.append('metrics', JSON.stringify(metrics));
    return (await api.post('/company-reports', data, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  },
  remove: async (id: number) => { await api.delete(`/company-reports/${id}`); },
  download: async (report: CompanyReport) => {
    const response = await api.get(`/company-reports/${report.id}/file`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a'); link.href = url; link.download = report.filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
