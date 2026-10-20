// frontend/src/App.tsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';
import { 
  Upload, ChevronLeft, ChevronRight, Wallet, Clock, Plus, CreditCard, 
  Sparkles, TrendingUp, TrendingDown, CheckCircle2, DollarSign, Calendar, 
  RefreshCw, Target, AlertCircle, ArrowLeft, FileUp, PiggyBank, X, 
  MoreVertical, Edit3, Trash2, PauseCircle, PlayCircle, ArrowDownRight, ArrowUpRight
} from 'lucide-react';

import { FinanceService, getCurrentUserId, errorMessage } from './api/client';
import { useAuth } from './context/AuthContext';
import { StatementImport } from './components/StatementImport';
import { useTelegram } from './context/TelegramContext';
import type { 
  MonthlyReportResponse, AIAdvisorResponse, SalarySummaryResponse, 
  RecurringResponse, CreditDebtResponse, GoalProgressBarWidget, 
  CategoryLimitWidget, ActionModalType, SavingsGoalResponse, TransactionDTO
} from './types';

/* ============================================================================
   0.1 ЭКРАН ЗАГРУЗКИ (SPLASH SCREEN)
============================================================================ */
const SplashScreen = ({ isFadingOut }: { isFadingOut: boolean }) => {
  return (
    <div className={`fixed inset-0 z-[999] bg-[#0A0D14] flex flex-col items-center justify-center transition-all duration-700 ease-out ${isFadingOut ? 'opacity-0 scale-105 pointer-events-none' : 'opacity-100 scale-100'}`}>
      <div className="relative flex flex-col items-center">
        {/* Анимированный глоу-фон */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-blue-500/10 blur-[60px] rounded-full pointer-events-none" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-emerald-500/10 blur-[50px] rounded-full pointer-events-none animate-pulse" />
        
        {/* Иконка */}
        <div className="w-20 h-20 bg-white/[0.03] border border-white/10 rounded-[2rem] flex items-center justify-center mb-6 shadow-2xl relative z-10 backdrop-blur-xl">
           <Sparkles className="w-10 h-10 text-emerald-400 animate-pulse" />
        </div>
        
        {/* Текст */}
        <h1 className="text-2xl font-extrabold text-white tracking-tight mb-3 relative z-10">Smart Finance</h1>
        
        <p className="font-mono text-[10px] text-white/40 uppercase tracking-[0.2em] relative z-10 flex items-center gap-2">
          <RefreshCw size={12} className="animate-spin text-blue-400" /> Сбор данных...
        </p>
      </div>
    </div>
  );
};

/* ============================================================================
   0. УНИВЕРСАЛЬНОЕ ВЫПАДАЮЩЕЕ МЕНЮ
============================================================================ */
interface ActionMenuProps {
  onEdit: () => void;
  onDelete: () => void;
  onPrimaryAction?: () => void;
  primaryLabel?: string;
  primaryIcon?: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
}

const ItemActionMenu: React.FC<ActionMenuProps> = ({ 
  onEdit, onDelete, onPrimaryAction, primaryLabel, primaryIcon, isOpen, onToggle, onClose
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const { haptic } = useTelegram();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  return (
    <div className={`relative inline-block text-left shrink-0 ${isOpen ? 'z-[100]' : 'z-10'}`} ref={menuRef}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); haptic.light(); onToggle(); }}
        className="p-2.5 rounded-xl bg-white/[0.07] hover:bg-white/20 border border-white/10 text-white transition-all active:scale-95"
      >
        <MoreVertical size={18} />
      </button>

      {isOpen && (
        <div 
          onClick={(e) => e.stopPropagation()} 
          className="absolute right-0 mt-2 w-52 rounded-2xl bg-[#0F1623] border border-white/20 shadow-[0_20px_50px_rgba(0,0,0,0.9)] z-[100] py-2 animate-in fade-in zoom-in-95 duration-150"
        >
          {onPrimaryAction && primaryLabel && (
            <button
              type="button"
              onClick={() => { haptic.medium(); onClose(); onPrimaryAction(); }}
              className="w-full px-4 py-3 text-left text-xs font-bold text-emerald-400 hover:bg-emerald-500/10 flex items-center gap-2.5 transition-colors"
            >
              {primaryIcon || <CheckCircle2 size={16} />}
              {primaryLabel}
            </button>
          )}
          <button
            type="button"
            onClick={() => { haptic.light(); onClose(); onEdit(); }}
            className="w-full px-4 py-3 text-left text-xs font-bold text-white hover:bg-white/10 flex items-center gap-2.5 transition-colors"
          >
            <Edit3 size={16} className="text-blue-400" />
            Изменить запись
          </button>
          <div className="h-[1px] bg-white/10 my-1 mx-2" />
          <button
            type="button"
            onClick={() => { haptic.heavy(); onClose(); onDelete(); }}
            className="w-full px-4 py-3 text-left text-xs font-bold text-rose-400 hover:bg-rose-500/10 flex items-center gap-2.5 transition-colors"
          >
            <Trash2 size={16} className="text-rose-400" />
            Удалить
          </button>
        </div>
      )}
    </div>
  );
};

/* ============================================================================
   0.5 ИНТЕРАКТИВНЫЙ ВЫБОР МЕСЯЦА (DROPDOWN)
============================================================================ */
const MONTH_NAMES = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];

const MonthDropdown = ({ 
  currentYear, currentMonth, onChange 
}: { 
  currentYear: number; currentMonth: number; onChange: (y: number, m: number) => void 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tempYear, setTempYear] = useState(currentYear);
  const menuRef = useRef<HTMLDivElement>(null);
  const { haptic } = useTelegram();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setIsOpen(false);
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) setTempYear(currentYear);
  }, [isOpen, currentYear]);

  return (
    <div className="relative z-[100]" ref={menuRef}>
      <button
        onClick={() => { haptic.light(); setIsOpen(!isOpen); }}
        className="flex items-center gap-2 bg-white/[0.05] backdrop-blur-md px-4 py-2 rounded-2xl border border-white/10 shadow-inner hover:bg-white/10 transition-all active:scale-95"
      >
        <Calendar size={16} className="text-blue-400" />
        <span className="font-extrabold text-sm tracking-wider text-white font-mono">
          {currentMonth.toString().padStart(2, '0')} / {currentYear}
        </span>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-3 w-72 bg-[#0F1623]/95 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.9)] rounded-[2rem] p-5 animate-in fade-in zoom-in-95 duration-200 backdrop-blur-3xl">
          <div className="flex items-center justify-between mb-4 bg-white/[0.03] p-1.5 rounded-2xl border border-white/5">
            <button 
              onClick={() => { haptic.light(); setTempYear(prev => prev - 1); }}
              className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/[0.05] hover:bg-white/10 transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <span className="font-extrabold text-lg tracking-wider font-mono text-white">{tempYear}</span>
            <button 
              onClick={() => { haptic.light(); setTempYear(prev => prev + 1); }}
              className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/[0.05] hover:bg-white/10 transition-colors"
            >
              <ChevronRight size={20} />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {MONTH_NAMES.map((m, index) => {
              const monthNum = index + 1;
              const isSelected = currentMonth === monthNum && currentYear === tempYear;
              
              return (
                <button
                  key={monthNum}
                  onClick={() => {
                    haptic.medium();
                    onChange(tempYear, monthNum);
                    setIsOpen(false);
                  }}
                  className={`py-2.5 rounded-xl font-bold text-xs transition-all flex items-center justify-center ${
                    isSelected 
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30' 
                      : 'bg-white/[0.03] text-white/60 hover:bg-white/10 hover:text-white border border-transparent'
                  }`}
                >
                  {m.substring(0, 3)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

/* ============================================================================
   1. КОМПОНЕНТ ДАШБОРДА (С КРУГОВЫМИ ДИАГРАММАМИ RECHARTS)
============================================================================ */
const INCOME_COLORS = ['#10B981', '#34D399', '#06B6D4', '#38BDF8', '#6EE7B7'];
const EXPENSE_COLORS = ['#F43F5E', '#FB7185', '#F97316', '#FBBF24', '#FB923C'];

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0A0D14]/95 backdrop-blur-xl border border-white/15 px-3 py-2 rounded-xl shadow-2xl font-mono text-xs">
        <p className="font-bold text-white mb-0.5">{payload[0].name}</p>
        <p className="text-emerald-400 font-extrabold">{Number(payload[0].value).toLocaleString('ru-RU')} ₽</p>
      </div>
    );
  }
  return null;
};

const GlassDashboard = ({ report, onShowAll }: { report: MonthlyReportResponse | null; onShowAll: () => void }) => {
  const netProfit = report ? Number(report.net_profit) : 0;
  const totalIncome = report ? Number(report.total_income) : 0;
  const totalExpense = report ? Number(report.total_expense) : 0;

  const incomeData = report?.income_by_category.map(c => ({ name: c.category, value: Number(c.amount) })) || [];
  const expenseData = report?.expense_by_category.map(c => ({ name: c.category, value: Number(c.amount) })) || [];

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Стеклянная карточка баланса */}
      <div className="bg-gradient-to-br from-white/[0.08] via-white/[0.03] to-transparent p-6 rounded-[2.5rem] border border-white/10 relative overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.6)] backdrop-blur-2xl">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-emerald-500/15 rounded-full blur-[60px] pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-blue-500/15 rounded-full blur-[60px] pointer-events-none" />
        
        <p className="text-white/60 text-xs font-medium uppercase tracking-wider mb-1">Чистый денежный поток</p>
        <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-baseline gap-2 font-mono">
          {netProfit.toLocaleString('ru-RU')} <span className="text-2xl text-emerald-400 font-normal">₽</span>
        </h1>
        
        <div className="grid grid-cols-2 gap-3 mt-6 relative z-10">
          <div className="bg-black/40 backdrop-blur-md p-4 rounded-2xl border border-white/5 flex flex-col justify-between">
            <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold mb-1">
              <TrendingUp size={16} /> Доходы
            </div>
            <div className="text-white font-bold text-lg font-mono">+{totalIncome.toLocaleString()} ₽</div>
          </div>
          <div className="bg-black/40 backdrop-blur-md p-4 rounded-2xl border border-white/5 flex flex-col justify-between">
            <div className="flex items-center gap-1.5 text-rose-400 text-xs font-semibold mb-1">
              <TrendingDown size={16} /> Расходы
            </div>
            <div className="text-white font-bold text-lg font-mono">-{totalExpense.toLocaleString()} ₽</div>
          </div>
        </div>
      </div>

      {/* КРУГОВЫЕ ГРАФИКИ (RECHARTS) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* График расходов */}
        <div className="bg-white/[0.03] backdrop-blur-xl p-5 rounded-[2rem] border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
              <ArrowDownRight size={16} /> Расходы
            </span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-white/50">{totalExpense.toLocaleString()} ₽</span>
              <button onClick={onShowAll} className="bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold px-2 py-1 rounded-lg transition-colors">ВСЕ</button>
            </div>
          </div>

          {expenseData.length > 0 ? (
            <div className="h-52 w-full relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={expenseData} cx="50%" cy="50%" innerRadius={45} outerRadius={68} paddingAngle={4} dataKey="value" stroke="none">
                    {expenseData.map((_, index) => <Cell key={`cell-${index}`} fill={EXPENSE_COLORS[index % EXPENSE_COLORS.length]} />)}
                  </Pie>
                  <RechartsTooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] text-white/40 uppercase font-mono">Траты</span>
                <span className="text-sm font-extrabold text-white font-mono">{expenseData.length} кат.</span>
              </div>
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center text-white/30 text-xs font-mono">Нет данных о списаниях</div>
          )}

          <div className="space-y-1.5 mt-2 border-t border-white/5 pt-3 max-h-28 overflow-y-auto pr-1">
            {expenseData.slice(0, 4).map((item, idx) => (
              <div key={item.name} className="flex justify-between items-center text-xs">
                <div className="flex items-center gap-2 truncate pr-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: EXPENSE_COLORS[idx % EXPENSE_COLORS.length] }} />
                  <span className="text-white/80 truncate">{item.name}</span>
                </div>
                <span className="font-mono font-bold text-white shrink-0">{item.value.toLocaleString()} ₽</span>
              </div>
            ))}
          </div>
        </div>

        {/* График доходов */}
        <div className="bg-white/[0.03] backdrop-blur-xl p-5 rounded-[2rem] border border-white/10 shadow-lg flex flex-col justify-between">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
              <ArrowDownRight size={16} /> Доходы
            </span>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-white/50">{totalIncome.toLocaleString()} ₽</span>
              <button onClick={onShowAll} className="bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold px-2 py-1 rounded-lg transition-colors">ВСЕ</button>
            </div>
          </div>

          {incomeData.length > 0 ? (
            <div className="h-52 w-full relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={incomeData} cx="50%" cy="50%" innerRadius={45} outerRadius={68} paddingAngle={4} dataKey="value" stroke="none">
                    {incomeData.map((_, index) => <Cell key={`cell-${index}`} fill={INCOME_COLORS[index % INCOME_COLORS.length]} />)}
                  </Pie>
                  <RechartsTooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-[10px] text-white/40 uppercase font-mono">Доход</span>
                <span className="text-sm font-extrabold text-white font-mono">{incomeData.length} кат.</span>
              </div>
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center text-white/30 text-xs font-mono">Нет данных о поступлениях</div>
          )}

          <div className="space-y-1.5 mt-2 border-t border-white/5 pt-3 max-h-28 overflow-y-auto pr-1">
            {incomeData.slice(0, 4).map((item, idx) => (
              <div key={item.name} className="flex justify-between items-center text-xs">
                <div className="flex items-center gap-2 truncate pr-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: INCOME_COLORS[idx % INCOME_COLORS.length] }} />
                  <span className="text-white/80 truncate">{item.name}</span>
                </div>
                <span className="font-mono font-bold text-white shrink-0">{item.value.toLocaleString()} ₽</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

/* ============================================================================
   2. КОМПОНЕНТ СМЕН (ФИКС ВЕРСТКИ СУММЫ И ПРОЗРАЧНОСТЬ ОПЛАЧЕННЫХ)
============================================================================ */
const GlassShifts = ({ 
  summary, onMarkPaid, onEditShift, onDeleteShift 
}: { 
  summary: SalarySummaryResponse | null; 
  onMarkPaid: (id: number) => void;
  onEditShift: (shift: any) => void;
  onDeleteShift: (id: number) => void;
}) => {
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);

  if (!summary) {
    return (
      <div className="bg-white/[0.03] backdrop-blur-xl p-8 rounded-[2rem] border border-white/10 text-center text-white/50 text-sm">
        <Clock className="w-10 h-10 mx-auto mb-3 text-white/20 animate-pulse" />
        Нет данных по сменам за выбранный месяц
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div className="bg-gradient-to-br from-blue-600/20 via-indigo-600/10 to-transparent p-6 rounded-[2.5rem] border border-blue-500/20 relative overflow-hidden shadow-[0_10px_40px_rgba(0,0,0,0.5)] backdrop-blur-2xl">
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-blue-500/20 rounded-full blur-[50px]" />
        
        <div className="flex items-center gap-2 text-blue-300 text-xs font-medium mb-1">
          <Calendar size={14} /> Период: {summary.month}/{summary.year}
        </div>
        <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-baseline gap-2 font-mono">
          {Number(summary.total_earned).toLocaleString()} <span className="text-2xl text-blue-400 font-normal">₽</span>
        </h1>
        
        <div className="grid grid-cols-3 gap-2.5 mt-6">
          <div className="bg-black/40 backdrop-blur-md p-3 rounded-2xl border border-white/5 text-center flex flex-col justify-center">
            <span className="text-[10px] text-white/50 block uppercase tracking-wider mb-0.5">Смен</span>
            <span className="text-sm font-bold text-white flex items-center justify-center gap-1 font-mono">
              <Clock size={13} className="text-blue-400" /> {summary.total_shifts}
            </span>
          </div>
          <div className="bg-black/40 backdrop-blur-md p-3 rounded-2xl border border-white/5 text-center flex flex-col justify-center">
            <span className="text-[10px] text-white/50 block uppercase tracking-wider mb-0.5">Часов</span>
            <span className="text-sm font-bold text-white font-mono">{Number(summary.total_hours)} ч</span>
          </div>
          <div className="bg-gradient-to-br from-amber-500/20 to-orange-500/10 backdrop-blur-md p-3 rounded-2xl border border-amber-500/30 text-center shadow-lg shadow-amber-500/5 flex flex-col justify-center">
            <span className="text-[9px] text-amber-300/80 block uppercase tracking-wider mb-0.5">К выплате</span>
            <span className="text-sm font-extrabold text-amber-400 font-mono whitespace-nowrap flex items-center justify-center gap-0.5">
              {Number(summary.unpaid_balance).toLocaleString()} <span className="text-xs">₽</span>
            </span>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-white font-bold text-base mb-3 px-2 flex items-center gap-2">
          <TrendingUp size={18} className="text-blue-400" /> История дежурств
        </h3>
        
        <div className="space-y-3">
          {summary.shifts.map((shift) => {
            const isMenuOpen = openMenuId === shift.id;
            
            return (
              <div 
                key={shift.id} 
                className={`p-4 rounded-3xl border transition-all duration-300 flex items-center justify-between relative ${
                  isMenuOpen ? 'z-[50] bg-white/[0.08] border-white/30' : 'z-10 bg-white/[0.05] border-white/10 hover:border-white/20'
                } ${
                  shift.is_paid ? 'opacity-40 hover:opacity-70 grayscale-[30%]' : 'opacity-100'
                }`}
              >
                <div className="flex items-center gap-3.5 min-w-0 flex-1">
                  <div className={`w-11 h-11 rounded-2xl flex items-center justify-center font-bold text-sm shrink-0 border ${
                    shift.is_paid 
                      ? 'bg-emerald-500/10 text-emerald-500/60 border-emerald-500/10' 
                      : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                  }`}>
                    <Clock size={20} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white text-sm whitespace-nowrap">{shift.shift_date}</h4>
                      {shift.is_paid && (
                        <span className="shrink-0 inline-flex items-center gap-1 text-[10px] text-emerald-400/80 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-medium">
                          <CheckCircle2 size={11} />
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-white/50 font-mono mt-0.5 block truncate whitespace-nowrap">
                      {Number(shift.hours_worked)} ч × {Number(shift.hourly_rate)} ₽/ч
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 shrink-0 ml-2">
                  <span className={`font-bold text-base font-mono whitespace-nowrap ${shift.is_paid ? 'text-white/60' : 'text-white'}`}>
                    +{Number(shift.total_earned).toLocaleString()} ₽
                  </span>
                  
                  <ItemActionMenu
                    isOpen={isMenuOpen}
                    onToggle={() => setOpenMenuId(isMenuOpen ? null : shift.id)}
                    onClose={() => setOpenMenuId(null)}
                    onEdit={() => onEditShift(shift)}
                    onDelete={() => onDeleteShift(shift.id)}
                    onPrimaryAction={!shift.is_paid ? () => onMarkPaid(shift.id) : undefined}
                    primaryLabel="Отметить выплату"
                    primaryIcon={<DollarSign size={16} />}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   3. КОМПОНЕНТ ПЛАНОВ
============================================================================ */
const GlassObligations = ({ 
  recurring, debts, savingsGoals, onToggleRecurring,
  onEditItem, onDeleteItem, onOpenPayment
}: {
  recurring: RecurringResponse[]; debts: CreditDebtResponse[]; savingsGoals: SavingsGoalResponse[];
  onToggleRecurring: (id: number) => void; onPayDebt: (id: number, amount: number) => void;
  onEditItem: (type: 'recurring' | 'debt' | 'savings', item: any) => void;
  onDeleteItem: (type: 'recurring' | 'debt' | 'savings', id: number) => void;
  onOpenPayment: (debt: CreditDebtResponse) => void;
}) => {
  const { haptic } = useTelegram();
  const [subTab, setSubTab] = useState<'expenses' | 'replenish' | 'debts'>('expenses');
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const expenseSubscriptions = recurring.filter(r => r.transaction_type === 'expense');
  const incomeReplenishments = recurring.filter(r => r.transaction_type === 'income');

  const totalExpenseSub = expenseSubscriptions
    .filter(r => r.is_active)
    .reduce((acc, curr) => acc + Number(curr.amount), 0);

  const totalIncomeRep = incomeReplenishments
    .filter(r => r.is_active)
    .reduce((acc, curr) => acc + Number(curr.amount), 0);

  const totalDebts = debts
    .filter(d => !d.is_closed)
    .reduce((acc, curr) => acc + Number(curr.current_balance), 0);

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div className="flex bg-white/[0.04] p-1.5 rounded-2xl border border-white/10 backdrop-blur-xl gap-1">
        <button
          type="button"
          onClick={() => { haptic.light(); setSubTab('expenses'); }}
          className={`flex-1 py-2.5 rounded-xl font-bold text-[11px] transition-all flex items-center justify-center gap-1.5 ${
            subTab === 'expenses' ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white shadow-lg shadow-purple-500/20' : 'text-white/60 hover:text-white'
          }`}
        >
          <RefreshCw size={13} /> Списания ({expenseSubscriptions.length})
        </button>
        <button
          type="button"
          onClick={() => { haptic.light(); setSubTab('replenish'); }}
          className={`flex-1 py-2.5 rounded-xl font-bold text-[11px] transition-all flex items-center justify-center gap-1.5 ${
            subTab === 'replenish' ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/20' : 'text-white/60 hover:text-white'
          }`}
        >
          <PiggyBank size={13} /> Пополнения ({incomeReplenishments.length + savingsGoals.length})
        </button>
        <button
          type="button"
          onClick={() => { haptic.light(); setSubTab('debts'); }}
          className={`flex-1 py-2.5 rounded-xl font-bold text-[11px] transition-all flex items-center justify-center gap-1.5 ${
            subTab === 'debts' ? 'bg-gradient-to-r from-rose-500 to-pink-600 text-white shadow-lg shadow-rose-500/20' : 'text-white/60 hover:text-white'
          }`}
        >
          <CreditCard size={13} /> Кредиты ({debts.length})
        </button>
      </div>

      {subTab === 'expenses' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-purple-600/20 via-indigo-600/10 to-transparent p-6 rounded-[2.5rem] border border-purple-500/20 backdrop-blur-2xl">
            <span className="text-xs text-purple-200/60 font-medium block mb-1">Регулярные расходы в месяц</span>
            <span className="text-3xl font-extrabold text-white font-mono">-{totalExpenseSub.toLocaleString('ru-RU')} ₽</span>
          </div>

          <div className="space-y-3">
            {expenseSubscriptions.map((item) => {
              const menuKey = `exp-${item.id}`;
              const isMenuOpen = openMenuId === menuKey;

              return (
                <div 
                  key={item.id} 
                  className={`p-4 rounded-3xl border transition-all flex items-center justify-between relative ${
                    isMenuOpen ? 'z-[50] bg-white/[0.08] border-white/30 shadow-2xl' : 'z-10 bg-white/[0.04] border-white/10 shadow-lg'
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white text-sm">{item.title}</h4>
                      {!item.is_active && <span className="text-[10px] bg-white/10 text-white/50 px-2 py-0.5 rounded-full">Пауза</span>}
                    </div>
                    <span className="text-xs text-white/50">Списание: {item.billing_day}-го числа</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-rose-400 text-sm font-mono">-{Number(item.amount).toLocaleString()} ₽</span>
                    <ItemActionMenu
                      isOpen={isMenuOpen}
                      onToggle={() => setOpenMenuId(isMenuOpen ? null : menuKey)}
                      onClose={() => setOpenMenuId(null)}
                      onEdit={() => onEditItem('recurring', item)}
                      onDelete={() => onDeleteItem('recurring', item.id)}
                      onPrimaryAction={() => onToggleRecurring(item.id)}
                      primaryLabel={item.is_active ? "Приостановить" : "Включить"}
                      primaryIcon={item.is_active ? <PauseCircle size={15} /> : <PlayCircle size={15} />}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {subTab === 'replenish' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-emerald-600/20 via-teal-600/10 to-transparent p-6 rounded-[2.5rem] border border-emerald-500/20 backdrop-blur-2xl">
            <span className="text-xs text-emerald-200/60 font-medium block mb-1">Поступления и вклады в месяц</span>
            <span className="text-3xl font-extrabold text-emerald-400 font-mono">+{totalIncomeRep.toLocaleString('ru-RU')} ₽</span>
          </div>

          <div className="space-y-3">
            {incomeReplenishments.map((item) => {
              const menuKey = `rep-${item.id}`;
              const isMenuOpen = openMenuId === menuKey;

              return (
                <div 
                  key={item.id} 
                  className={`p-4 rounded-3xl border transition-all flex items-center justify-between relative ${
                    isMenuOpen ? 'z-[50] bg-white/[0.08] border-white/30 shadow-2xl' : 'z-10 bg-white/[0.04] border-emerald-500/20 shadow-lg'
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white text-sm">{item.title}</h4>
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">Регулярное</span>
                    </div>
                    <span className="text-xs text-white/50">Пополнение: {item.billing_day}-го числа</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-emerald-400 text-sm font-mono">+{Number(item.amount).toLocaleString()} ₽</span>
                    <ItemActionMenu
                      isOpen={isMenuOpen}
                      onToggle={() => setOpenMenuId(isMenuOpen ? null : menuKey)}
                      onClose={() => setOpenMenuId(null)}
                      onEdit={() => onEditItem('recurring', item)}
                      onDelete={() => onDeleteItem('recurring', item.id)}
                      onPrimaryAction={() => onToggleRecurring(item.id)}
                      primaryLabel={item.is_active ? "Приостановить" : "Включить"}
                      primaryIcon={item.is_active ? <PauseCircle size={15} /> : <PlayCircle size={15} />}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {subTab === 'debts' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-rose-600/20 via-pink-600/10 to-transparent p-6 rounded-[2.5rem] border border-rose-500/20 backdrop-blur-2xl">
            <span className="text-xs text-rose-200/60 font-medium block mb-1">Общий долг к погашению</span>
            <span className="text-3xl font-extrabold text-rose-400 font-mono">{totalDebts.toLocaleString('ru-RU')} ₽</span>
          </div>

          <div className="space-y-3">
            {debts.map((debt) => {
              const menuKey = `debt-${debt.id}`;
              const isMenuOpen = openMenuId === menuKey;
              const total = Number(debt.total_amount);
              const current = Number(debt.current_balance);
              const paidPercent = total > 0 ? Math.round(((total - current) / total) * 100) : 0;

              return (
                <div 
                  key={debt.id} 
                  className={`p-5 rounded-3xl border transition-all space-y-3 relative ${
                    isMenuOpen ? 'z-[50] bg-white/[0.08] border-white/30 shadow-2xl' : 'z-10 bg-white/[0.04] border-white/10 shadow-lg'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-white text-base">{debt.title}</h4>
                      {debt.interest_rate && <span className="text-xs text-white/50">Ставка: {debt.interest_rate}% годовых</span>}
                    </div>
                    <div className="flex items-center gap-3">
                      {debt.is_closed ? (
                        <span className="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-1">
                          <CheckCircle2 size={14} /> Закрыт
                        </span>
                      ) : (
                        <span className="font-extrabold text-rose-400 text-base font-mono">{current.toLocaleString()} ₽</span>
                      )}
                      <ItemActionMenu
                        isOpen={isMenuOpen}
                        onToggle={() => setOpenMenuId(isMenuOpen ? null : menuKey)}
                        onClose={() => setOpenMenuId(null)}
                        onEdit={() => onEditItem('debt', debt)}
                        onDelete={() => onDeleteItem('debt', debt.id)}
                        onPrimaryAction={!debt.is_closed ? () => onOpenPayment(debt) : undefined} // ИЗМЕНЕНО
                        primaryLabel="Внести сумму" // ИЗМЕНЕНО
                        primaryIcon={<DollarSign size={15} />}
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-white/60 font-medium">
                      <span>Погашено: {paidPercent}%</span>
                      <span className="font-mono">Изначально: {total.toLocaleString()} ₽</span>
                    </div>
                    <div className="w-full bg-black/50 rounded-full h-2.5 overflow-hidden border border-white/5">
                      <div className="bg-gradient-to-r from-rose-500 to-pink-500 h-full rounded-full transition-all duration-1000 shadow-[0_0_10px_rgba(244,63,94,0.5)]" style={{ width: `${Math.min(paidPercent, 100)}%` }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

/* ============================================================================
   4. КОМПОНЕНТ ИИ АНАЛИТИКА (GLASS AI ADVISOR)
============================================================================ */
const GlassAiAdvisor = ({ data, loading }: { data: AIAdvisorResponse | null; loading: boolean }) => {
  if (loading) {
    return (
      <div className="bg-white/[0.03] backdrop-blur-xl p-12 rounded-[2.5rem] border border-white/10 text-center space-y-3">
        <Sparkles className="w-10 h-10 text-purple-400 animate-spin mx-auto opacity-80" />
        <p className="text-sm font-bold text-white/80">Gemini 2.5 генерирует финансовый отчет...</p>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-gradient-to-br from-purple-900/30 via-indigo-900/20 to-transparent p-6 rounded-[2.5rem] border border-purple-500/30 relative shadow-2xl overflow-hidden backdrop-blur-2xl">
        <Sparkles className="absolute top-6 right-6 text-purple-400/10" size={80} />
        <h2 className="text-xl font-extrabold text-white mb-4 relative z-10 flex items-center gap-2">
          <Sparkles className="text-amber-400 animate-pulse" size={22} /> ИИ Финансовый Инспектор ({data.month}/{data.year})
        </h2>
        <div className="prose prose-invert max-w-none text-xs text-white/80 leading-relaxed relative z-10 space-y-2 font-sans">
          <ReactMarkdown>{data.markdown_insights}</ReactMarkdown>
        </div>
      </div>

      {data.widgets && data.widgets.length > 0 && (
        <div>
          <h3 className="text-white font-bold text-base mb-3 px-2 flex items-center gap-2">
            <Target size={18} className="text-purple-400" /> Рассчитанные цели и лимиты
          </h3>
          {data.widgets.map((w, idx) => {
            if (w.type === 'goal_progress') {
              const goal = w as GoalProgressBarWidget;
              const percent = Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100));
              return (
                <div key={idx} className="bg-white/[0.04] backdrop-blur-xl p-5 rounded-3xl border border-white/10 mb-3.5 shadow-lg">
                  <div className="flex justify-between items-center mb-3">
                    <span className="font-bold text-white text-sm">{goal.title}</span>
                    <span className="text-xs font-extrabold text-emerald-400 font-mono">{percent}%</span>
                  </div>
                  <div className="w-full bg-black/50 rounded-full h-3 mb-3 overflow-hidden border border-white/5">
                    <div className="bg-gradient-to-r from-emerald-400 to-teal-500 h-full rounded-full transition-all duration-1000 shadow-[0_0_12px_rgba(52,211,153,0.5)]" style={{ width: `${percent}%` }} />
                  </div>
                  <div className="flex justify-between text-xs font-mono text-white/70">
                    <span>{goal.current_amount.toLocaleString()} ₽</span>
                    <span>{goal.target_amount.toLocaleString()} ₽</span>
                  </div>
                  <p className="mt-3 text-xs text-white/60 border-t border-white/5 pt-2">{goal.recommendation}</p>
                </div>
              );
            }
            if (w.type === 'category_limit') {
              const limit = w as CategoryLimitWidget;
              const percent = Math.round((limit.spent_amount / limit.recommended_limit) * 100);
              const isWarn = limit.severity !== 'normal';
              return (
                <div key={idx} className="bg-white/[0.04] backdrop-blur-xl p-5 rounded-3xl border border-white/10 mb-3.5 shadow-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle size={18} className={isWarn ? "text-rose-400" : "text-emerald-400"} />
                      <span className="font-bold text-white text-sm">Лимит: {limit.category}</span>
                    </div>
                    <span className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full ${isWarn ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300'}`}>
                      {limit.severity}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-1.5 mb-3 font-mono">
                    <span className="text-2xl font-bold text-white">{limit.spent_amount.toLocaleString()} ₽</span>
                    <span className="text-xs text-white/50">/ {limit.recommended_limit.toLocaleString()} ₽</span>
                  </div>
                  <div className="w-full bg-black/50 rounded-full h-2.5 overflow-hidden border border-white/5">
                    <div className={`h-full rounded-full transition-all duration-1000 ${isWarn ? 'bg-gradient-to-r from-rose-500 to-red-600 shadow-[0_0_10px_rgba(244,63,94,0.5)]' : 'bg-gradient-to-r from-blue-500 to-indigo-500'}`} style={{ width: `${Math.min(100, percent)}%` }} />
                  </div>
                </div>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
};

/* ============================================================================
   5. МОДАЛЬНОЕ ОКНО СОЗДАНИЯ И РЕДАКТИРОВАНИЯ (GLASS ACTION MODAL)
============================================================================ */
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onActionSuccess: () => void;
  editData?: { type: string; item: any } | null;
}

const GlassActionModal: React.FC<ModalProps> = ({ isOpen, onClose, onActionSuccess, editData }) => {
  const { haptic } = useTelegram();
  const [selectedType, setSelectedType] = useState<ActionModalType>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  


  const [formData, setFormData] = useState({
    title: '', amount: '', target_amount: '', monthly_contribution: '',
    date: new Date().toISOString().split('T')[0], hours: '8', rate: '1500',
    description: '', interest: '18', billing_day: '15', type: 'expense' as 'expense' | 'income'
  });

  useEffect(() => {
    if (editData && isOpen) {
      if (editData.type === 'transaction') {
        setSelectedType('transaction');
        setFormData(prev => ({ ...prev, title: editData.item.category, amount: str(editData.item.amount), type: editData.item.transaction_type, description: editData.item.description || '', date: editData.item.transaction_date.slice(0, 10) }));
      } else if (editData.type === 'shift') {
        setSelectedType('shift');
        setFormData(prev => ({ ...prev, date: editData.item.shift_date, hours: str(editData.item.hours_worked), rate: str(editData.item.hourly_rate) }));
      } else if (editData.type === 'recurring') {
        setSelectedType(editData.item.transaction_type === 'income' ? 'savings' : 'recurring');
        setFormData(prev => ({ ...prev, title: editData.item.title, amount: str(editData.item.amount), billing_day: str(editData.item.billing_day), type: editData.item.transaction_type }));
      } else if (editData.type === 'debt') {
        setSelectedType('debt');
        setFormData(prev => ({ ...prev, title: editData.item.title, amount: str(editData.item.total_amount), interest: str(editData.item.interest_rate || '') }));
      } else if (editData.type === 'savings') {
        setSelectedType('savings');
        setFormData(prev => ({ ...prev, title: editData.item.title, target_amount: str(editData.item.target_amount), monthly_contribution: str(editData.item.monthly_contribution) }));
      }
    } else if (!isOpen) {
      setSelectedType(null);
      setError(null);

    }
  }, [editData, isOpen]);

  const str = (val: any) => val ? String(val) : '';

  if (!isOpen) return null;

  const handleSelect = (type: ActionModalType) => { haptic.light(); setError(null); setSelectedType(type); };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); haptic.medium(); setLoading(true); setError(null);
    const userId = getCurrentUserId();

    try {
      // ФИКС БАГА: Имитация PUT-запроса (удаляем старую запись перед созданием новой)
      if (editData) {
        if (editData.type === 'shift') await FinanceService.deleteShift(editData.item.id, userId);
        else if (editData.type === 'recurring') await FinanceService.deleteRecurring(editData.item.id, userId);
        else if (editData.type === 'savings') await FinanceService.deleteSavingsGoal(editData.item.id, userId);
        else if (editData.type === 'debt') await FinanceService.deleteDebt(editData.item.id, userId);
      }

      // Стандартная логика создания
      if (selectedType === 'shift') {
        await FinanceService.createShift({ shift_date: formData.date, hours_worked: Number(formData.hours), hourly_rate: Number(formData.rate) }, userId);
      } else if (selectedType === 'recurring') {
        await FinanceService.createRecurring({ title: formData.title, amount: Number(formData.amount), transaction_type: 'expense', category: 'Подписки', billing_day: Number(formData.billing_day), next_payment_date: formData.date }, userId);
      } else if (selectedType === 'savings') {
        await FinanceService.createRecurring({ title: formData.title, amount: Number(formData.amount || formData.monthly_contribution), transaction_type: 'income', category: 'Пополнение', billing_day: Number(formData.billing_day), next_payment_date: formData.date }, userId);
      } else if (selectedType === 'debt') {
        await FinanceService.createDebt({ title: formData.title, total_amount: Number(formData.amount), current_balance: Number(formData.amount), interest_rate: formData.interest ? Number(formData.interest) : null }, userId);
      } else if (selectedType === 'transaction') {
        const save = editData?.type === 'transaction' ? (payload: unknown) => FinanceService.updateTransaction(editData.item.id, payload) : (payload: unknown) => FinanceService.createTransaction(payload, userId);
        await save({
          amount: Number(formData.amount),
          transaction_type: formData.type,
          category: formData.title.trim(),
          description: formData.description || 'Ручной ввод',
          transaction_date: new Date(formData.date).toISOString()
        });
      }
      haptic.success(); onActionSuccess(); setSelectedType(null); onClose();
    } catch (err: any) {
      haptic.error(); setError(errorMessage(err) || 'Ошибка сохранения. Проверьте данные.');
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-end sm:items-center justify-center p-3 sm:p-4 animate-in fade-in duration-300">
      <div className="bg-[#101622]/95 backdrop-blur-2xl w-full max-w-md rounded-[2.5rem] p-6 border border-white/15 shadow-[0_20px_60px_rgba(0,0,0,0.8)] mb-safe max-h-[90vh] overflow-y-auto relative">
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-purple-500/20 rounded-full blur-[60px] pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-emerald-500/15 rounded-full blur-[60px] pointer-events-none" />

        <div className="flex justify-between items-center mb-6 relative z-10">
          <div className="flex items-center gap-2.5">
            {selectedType && !editData && (
              <button aria-label="Назад" onClick={() => setSelectedType(null)} className="p-2 rounded-full bg-white/5 hover:bg-white/10 text-white/80 transition-colors">
                <ArrowLeft size={18} />
              </button>
            )}
            <h3 className="font-bold text-lg text-white flex items-center gap-2">
              <Sparkles className="text-purple-400 w-5 h-5 animate-pulse" />
              {editData ? 'Редактирование записи' : !selectedType ? 'Создать запись' : 
                selectedType === 'statement' ? 'Импорт выписки' :
                selectedType === 'transaction' ? 'Доход или расход' :
                selectedType === 'shift' ? 'Рабочая смена' :
                selectedType === 'recurring' ? 'Новое списание (Подписка)' :
                selectedType === 'debt' ? 'Кредит / Долг' : 'Регулярное пополнение'}
            </h3>
          </div>
          <button aria-label="Закрыть" onClick={() => { setSelectedType(null); onClose(); }} className="p-2 rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>

        {error && <div className="mb-4 p-3 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2 relative z-10"><AlertCircle size={16} className="shrink-0" /><span>{error}</span></div>}

        {/* Выбор из 5 типов операций */}
        {!selectedType && (
          <div className="grid grid-cols-2 gap-3 pb-2 relative z-10">
            <button onClick={() => handleSelect('statement')} className="col-span-2 bg-gradient-to-r from-emerald-500/20 to-teal-500/10 p-4 rounded-3xl border border-emerald-500/30 flex items-center gap-4 hover:border-emerald-400 transition-all text-left group active:scale-[0.98] shadow-lg shadow-emerald-500/5">
              <div className="w-12 h-12 rounded-2xl bg-emerald-400 text-black flex items-center justify-center shrink-0 font-bold group-hover:scale-110 transition-transform shadow-[0_0_20px_rgba(52,211,153,0.4)]"><FileUp size={24} /></div>
              <div><h4 className="font-bold text-white text-sm">Выписка из банка</h4><p className="text-xs text-emerald-200/70">Умный импорт PDF / CSV</p></div>
            </button>

            <button onClick={() => handleSelect('recurring')} className="bg-white/[0.04] p-4 rounded-3xl border border-white/10 flex flex-col gap-3 hover:border-purple-400/50 hover:bg-purple-500/10 transition-all text-left group active:scale-[0.96]">
              <div className="w-10 h-10 rounded-2xl bg-purple-500/20 text-purple-400 flex items-center justify-center group-hover:scale-110 transition-transform"><RefreshCw size={20} /></div>
              <div><h4 className="font-bold text-white text-sm">Списание</h4><p className="text-[10px] text-white/50">Подписка, аренда (-)</p></div>
            </button>

            <button onClick={() => handleSelect('savings')} className="bg-white/[0.04] p-4 rounded-3xl border border-white/10 flex flex-col gap-3 hover:border-emerald-400/50 hover:bg-emerald-500/10 transition-all text-left group active:scale-[0.96]">
              <div className="w-10 h-10 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center group-hover:scale-110 transition-transform"><PiggyBank size={20} /></div>
              <div><h4 className="font-bold text-white text-sm">Пополнение</h4><p className="text-[10px] text-white/50">Инвестиции, копилка (+)</p></div>
            </button>

            <button onClick={() => handleSelect('shift')} className="bg-white/[0.04] p-4 rounded-3xl border border-white/10 flex flex-col gap-3 hover:border-blue-400/50 hover:bg-blue-500/10 transition-all text-left group active:scale-[0.96]">
              <div className="w-10 h-10 rounded-2xl bg-blue-500/20 text-blue-400 flex items-center justify-center group-hover:scale-110 transition-transform"><Clock size={20} /></div>
              <div><h4 className="font-bold text-white text-sm">Рабочая смена</h4><p className="text-[10px] text-white/50">Учет часов и ставки</p></div>
            </button>

            <button onClick={() => handleSelect('debt')} className="bg-white/[0.04] p-4 rounded-3xl border border-white/10 flex flex-col gap-3 hover:border-rose-400/50 hover:bg-rose-500/10 transition-all text-left group active:scale-[0.96]">
              <div className="w-10 h-10 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center group-hover:scale-110 transition-transform"><CreditCard size={20} /></div>
              <div><h4 className="font-bold text-white text-sm">Кредит / Долг</h4><p className="text-[10px] text-white/50">Учет обязательств</p></div>
            </button>

            <button onClick={() => handleSelect('transaction')} className="col-span-2 bg-gradient-to-r from-amber-500/20 to-orange-500/10 p-4 rounded-3xl border border-amber-500/30 flex items-center gap-4 hover:border-amber-400 transition-all text-left group active:scale-[0.98] shadow-lg shadow-amber-500/5">
              <div className="w-12 h-12 rounded-2xl bg-amber-400 text-black flex items-center justify-center shrink-0 font-bold group-hover:scale-110 transition-transform shadow-[0_0_20px_rgba(251,191,36,0.4)]"><DollarSign size={24} /></div>
              <div><h4 className="font-bold text-white text-sm">Ручная транзакция</h4><p className="text-xs text-amber-200/70">Внести доход или расход</p></div>
            </button>
          </div>
        )}

        {selectedType && (
          <form onSubmit={handleSubmit} className="space-y-4 relative z-10">
            {selectedType === 'shift' && (
              <>
                <div><label className="text-xs text-white/60 block mb-1">Дата смены</label><input type="date" required value={formData.date} onChange={e => setFormData({...formData, date: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-400 transition-colors" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-xs text-white/60 block mb-1">Отдежурено (часов)</label><input type="number" step="0.5" required value={formData.hours} onChange={e => setFormData({...formData, hours: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-blue-400" /></div>
                  <div><label className="text-xs text-white/60 block mb-1">Ставка (₽/час)</label><input type="number" required value={formData.rate} onChange={e => setFormData({...formData, rate: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-blue-400" /></div>
                </div>
                <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-200 text-xs flex justify-between items-center"><span>Итого к начислению:</span><span className="font-bold font-mono text-base text-blue-400">{(Number(formData.hours) * Number(formData.rate)).toLocaleString()} ₽</span></div>
              </>
            )}

            {(selectedType === 'recurring' || selectedType === 'savings' || selectedType === 'debt') && (
              <>
                <div><label className="text-xs text-white/60 block mb-1">Название</label><input type="text" required placeholder={selectedType === 'recurring' ? 'Netflix, Аренда' : selectedType === 'savings' ? 'Пополнение брокерского счета, Копилка' : 'Ипотека, Кредитная карта'} value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-400" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label htmlFor="tx-amount" className="text-xs text-white/60 block mb-1">Сумма (₽)</label><input id="tx-amount" type="number" min="0.01" step="0.01" required placeholder="0" font-mono="true" value={formData.amount || formData.monthly_contribution} onChange={e => setFormData({...formData, amount: e.target.value, monthly_contribution: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-purple-400" /></div>
                  {(selectedType === 'recurring' || selectedType === 'savings') ? (
                    <div><label className="text-xs text-white/60 block mb-1">День выполнения</label><input type="number" min="1" max="31" required value={formData.billing_day} onChange={e => setFormData({...formData, billing_day: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none" /></div>
                  ) : (
                    <div><label className="text-xs text-white/60 block mb-1">Процент (%)</label><input type="number" placeholder="18" value={formData.interest} onChange={e => setFormData({...formData, interest: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none" /></div>
                  )}
                </div>
              </>
            )}

            {selectedType === 'transaction' && (
              <>
                <div className="flex gap-2 p-1 bg-black/40 rounded-2xl border border-white/15 mb-3">
                  <button type="button" onClick={() => setFormData({...formData, type: 'expense'})} className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${formData.type === 'expense' ? 'bg-rose-500 text-white shadow-lg shadow-rose-500/30' : 'text-white/50 hover:text-white'}`}>Расход (-)</button>
                  <button type="button" onClick={() => setFormData({...formData, type: 'income'})} className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${formData.type === 'income' ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30' : 'text-white/50 hover:text-white'}`}>Доход (+)</button>
                </div>
                <div>
                  <label htmlFor="tx-category" className="text-xs text-white/60 block mb-1">Категория</label>
                  <input id="tx-category" type="text" required placeholder="Продукты, Переводы, Зарплата..." maxLength={64} value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white focus:outline-none focus:border-amber-400" />
                </div>
                <div><label htmlFor="tx-description" className="text-xs text-white/60 block mb-1">Комментарий (необязательно)</label><input id="tx-description" value={formData.description} maxLength={2000} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label htmlFor="tx-amount" className="text-xs text-white/60 block mb-1">Сумма (₽)</label><input id="tx-amount" type="number" min="0.01" step="0.01" required placeholder="0" value={formData.amount} onChange={e => setFormData({...formData, amount: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-amber-400" /></div>
                  <div><label htmlFor="tx-date" className="text-xs text-white/60 block mb-1">Дата</label><input id="tx-date" type="date" required value={formData.date} onChange={e => setFormData({...formData, date: e.target.value})} className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-sm text-white font-mono focus:outline-none" /></div>
                </div>
              </>
            )}

            {selectedType === 'statement' && <StatementImport onSuccess={onActionSuccess} />}

            {selectedType !== 'statement' && (
              <button type="submit" disabled={loading} className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-bold py-4 rounded-2xl shadow-[0_0_25px_rgba(99,102,241,0.4)] hover:shadow-[0_0_35px_rgba(99,102,241,0.6)] active:scale-[0.98] transition-all flex items-center justify-center gap-2 mt-6">
                {loading ? 'Сохранение...' : <><CheckCircle2 size={18} /> {editData ? 'Сохранить изменения' : 'Создать запись'}</>}
              </button>
            )}
          </form>
        )}
      </div>
    </div>
  );
};

/* ============================================================================
   5.5 МОДАЛЬНОЕ ОКНО ОПЛАТЫ ДОЛГА
============================================================================ */
const GlassPaymentModal = ({ 
  isOpen, onClose, debt, onPaySuccess 
}: { 
  isOpen: boolean; onClose: () => void; debt: CreditDebtResponse | null; onPaySuccess: (id: number, amount: number) => void 
}) => {
  const { haptic } = useTelegram();
  const [amount, setAmount] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (isOpen) setAmount(''); }, [isOpen]);

  if (!isOpen || !debt) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payAmount = Number(amount);
    if (payAmount <= 0) return;
    
    haptic.medium();
    setLoading(true);
    try {
      await onPaySuccess(debt.id, payAmount);
      haptic.success();
      onClose();
    } catch (err) {
      haptic.error();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[120] bg-black/70 backdrop-blur-md flex items-end sm:items-center justify-center p-3 sm:p-4 animate-in fade-in duration-300">
      <div className="bg-[#101622]/95 backdrop-blur-2xl w-full max-w-md rounded-[2.5rem] p-6 border border-white/15 shadow-[0_20px_60px_rgba(0,0,0,0.8)] mb-safe relative">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-lg text-white flex items-center gap-2">
            <DollarSign className="text-emerald-400" />
            Внести платеж
          </h3>
          <button onClick={() => { haptic.light(); onClose(); }} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-white/60 hover:text-white transition-colors"><X size={18} /></button>
        </div>
        
        <div className="mb-4 bg-white/5 p-4 rounded-2xl border border-white/10">
          <p className="text-xs text-white/50 mb-1">Текущий долг:</p>
          <p className="text-xl font-mono font-bold text-rose-400">{Number(debt.current_balance).toLocaleString()} ₽</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-white/60 block mb-1">Сумма к внесению (₽)</label>
            <input 
              type="number" required autoFocus 
              placeholder="0" 
              max={Number(debt.current_balance)} 
              value={amount} 
              onChange={e => setAmount(e.target.value)} 
              className="w-full bg-black/40 border border-white/15 rounded-2xl px-4 py-3 text-lg text-white font-mono focus:outline-none focus:border-emerald-400 transition-colors" 
            />
          </div>
          <button type="submit" disabled={loading || !amount} className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-black font-extrabold py-4 rounded-2xl shadow-lg active:scale-95 transition-all">
            {loading ? 'Обработка...' : 'Подтвердить платеж'}
          </button>
        </form>
      </div>
    </div>
  );
};

/* ============================================================================
   6. ПЛАВАЮЩАЯ НАВИГАЦИЯ (GLASS FLOATING NAV)
============================================================================ */
const GlassNav = ({ activeTab, onSelectTab, onOpenUpload }: { activeTab: string; onSelectTab: (tab: string) => void; onOpenUpload: () => void }) => {
  const { haptic } = useTelegram();
  const handleTabClick = (id: string) => { if (activeTab !== id) { haptic.light(); onSelectTab(id); } };

  return (
    <div className="fixed bottom-0 left-0 w-full pb-safe pt-4 px-4 bg-gradient-to-t from-[#0A0D14] via-[#0A0D14]/90 to-transparent flex justify-center z-50 pointer-events-none">
      <div className="bg-white/[0.06] backdrop-blur-2xl px-2 py-2 rounded-[2.5rem] border border-white/15 flex items-center justify-between w-full max-w-[400px] relative pointer-events-auto shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
        
        <div className="flex items-center justify-around w-[40%]">
          <button aria-label="Обзор" onClick={() => handleTabClick('dashboard')} className={`flex items-center gap-1.5 px-3 py-2.5 rounded-full transition-all duration-300 ${activeTab === 'dashboard' ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold' : 'text-white/60 hover:bg-white/10'}`}><Wallet size={18} />{activeTab === 'dashboard' && <span className="text-xs">Обзор</span>}</button>
          <button aria-label="Смены" onClick={() => handleTabClick('shifts')} className={`flex items-center gap-1.5 px-3 py-2.5 rounded-full transition-all duration-300 ${activeTab === 'shifts' ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold' : 'text-white/60 hover:bg-white/10'}`}><Clock size={18} />{activeTab === 'shifts' && <span className="text-xs">Смены</span>}</button>
        </div>

        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
          <button aria-label="Добавить операцию" onClick={() => { haptic.medium(); onOpenUpload(); }} className="w-[52px] h-[52px] rounded-full bg-gradient-to-tr from-emerald-400 via-teal-400 to-blue-500 flex items-center justify-center shadow-[0_0_25px_rgba(52,211,153,0.5)] transform transition hover:scale-110 active:scale-95 shrink-0">
            <Plus size={28} className="text-black stroke-[3]" />
          </button>
        </div>

        <div className="flex items-center justify-around w-[40%]">
          <button aria-label="Планы" onClick={() => handleTabClick('obligations')} className={`flex items-center gap-1.5 px-3 py-2.5 rounded-full transition-all duration-300 ${activeTab === 'obligations' ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold' : 'text-white/60 hover:bg-white/10'}`}><CreditCard size={18} />{activeTab === 'obligations' && <span className="text-xs">Планы</span>}</button>
          <button aria-label="Аналитик" onClick={() => handleTabClick('ai')} className={`flex items-center gap-1.5 px-3 py-2.5 rounded-full transition-all duration-300 ${activeTab === 'ai' ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold' : 'text-white/60 hover:bg-white/10'}`}><Sparkles size={18} />{activeTab === 'ai' && <span className="text-xs">AI</span>}</button>
        </div>

      </div>
    </div>
  );
};

/* ============================================================================
   6.5 ПОЛНОЭКРАННАЯ СВОДКА ВСЕХ КАТЕГОРИЙ И ТРАНЗАКЦИЙ
============================================================================ */
const GlassAllTransactionsModal = ({ isOpen, onClose, report, onEdit, onDelete }: { isOpen: boolean; onClose: () => void; report: MonthlyReportResponse | null; onEdit: (tx: TransactionDTO) => void; onDelete: (id: number) => Promise<void> }) => {
  const { haptic } = useTelegram();
  const [tab, setTab] = useState<'expenses' | 'income'>('expenses');

  if (!isOpen || !report) return null;

  const sortedExpenses = [...report.expense_by_category].sort((a,b) => Number(a.amount) - Number(b.amount));
  const sortedIncomes = [...report.income_by_category].sort((a,b) => Number(a.amount) - Number(b.amount));

  const activeData = tab === 'expenses' ? sortedExpenses : sortedIncomes;
  const color = tab === 'expenses' ? 'text-rose-400' : 'text-emerald-400';

  return (
    <div className="fixed inset-0 z-[110] bg-[#0A0D14] flex flex-col animate-in slide-in-from-bottom-full duration-300">
      <div className="pt-safe px-4 pb-3 flex items-center justify-between border-b border-white/10 bg-[#0F1623]">
        <h2 className="text-lg font-bold text-white flex items-center gap-2"><ArrowUpRight size={20} className="text-blue-400"/> Сводка за месяц</h2>
        <button onClick={() => { haptic.light(); onClose(); }} className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"><X size={18} /></button>
      </div>

      <div className="flex p-4 gap-2 bg-[#0A0D14]">
        <button onClick={() => setTab('expenses')} className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${tab === 'expenses' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' : 'bg-white/5 text-white/50'}`}>Расходы</button>
        <button onClick={() => setTab('income')} className={`flex-1 py-2.5 rounded-xl text-sm font-bold transition-all ${tab === 'income' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-white/5 text-white/50'}`}>Доходы</button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-safe space-y-4">
        <div className="bg-white/5 rounded-[2rem] p-5 border border-white/10 shadow-lg">
          <h3 className="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-4">Сортировка: По возрастанию</h3>
          <div className="space-y-1">
            {activeData.map((item, idx) => (
              <div key={idx} className="flex justify-between items-center py-2.5 border-b border-white/5 last:border-0">
                <span className="text-sm font-medium text-white">{item.category}</span>
                <span className={`text-sm font-bold font-mono ${color}`}>{Number(item.amount).toLocaleString()} ₽</span>
              </div>
            ))}
            {activeData.length === 0 && <div className="text-center text-xs text-white/30 py-4 font-mono">Нет данных</div>}
          </div>
        </div>

        <div className="bg-white/5 rounded-[2rem] p-5 border border-white/10 shadow-lg mb-4">
          <h3 className="text-[10px] text-white/40 font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
            <Clock size={14} /> Последние операции
          </h3>
          <div className="space-y-3">
            {report.transactions && report.transactions.length > 0 ? (
              report.transactions.filter(tx => tx.transaction_type === (tab === 'expenses' ? 'expense' : 'income')).map((tx) => {
                const isIncome = tx.transaction_type === 'income';
                return (
                  <div key={tx.id} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                    <div className="flex-1 min-w-0 pr-3">
                      <h4 className="text-sm font-bold text-white truncate">{tx.category}</h4>
                      <p className="text-[10px] text-white/50 truncate">
                        {new Date(tx.transaction_date).toLocaleDateString('ru-RU')} • {tx.description || 'Ручной ввод'}
                      </p>
                    </div>
                    <span className={`text-sm font-bold font-mono whitespace-nowrap ${isIncome ? 'text-emerald-400' : 'text-white'}`}>
                      {isIncome ? '+' : '-'}{Number(tx.amount).toLocaleString()} ₽
                    </span>
                    <button type="button" aria-label={`Изменить операцию ${tx.category}`} className="p-2 ml-2 text-blue-300" onClick={() => { onClose(); onEdit(tx); }}><Edit3 size={16} /></button>
                    <button type="button" aria-label={`Удалить операцию ${tx.category}`} className="p-2 text-rose-300" onClick={() => void onDelete(tx.id)}><Trash2 size={16} /></button>
                  </div>
                );
              })
            ) : (
              <div className="text-center text-xs text-white/30 py-4 font-mono">
                Нет транзакций за этот месяц
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================================
   7. ГЛАВНЫЙ КОНТЕЙНЕР ПРИЛОЖЕНИЯ
============================================================================ */
export default function App() {
  const today = new Date();
  const [year, setYear] = useState<number>(today.getFullYear());
  const [month, setMonth] = useState<number>(today.getMonth() + 1);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [editingData, setEditingData] = useState<{ type: string; item: any } | null>(null);
  const [showAllModal, setShowAllModal] = useState(false);
  const [paymentDebt, setPaymentDebt] = useState<CreditDebtResponse | null>(null);

  // Стейты для Splash Screen
  const [isSplashVisible, setIsSplashVisible] = useState(true);
  const [isSplashFading, setIsSplashFading] = useState(false);


  const [report, setReport] = useState<MonthlyReportResponse | null>(null);
  const [aiData, setAiData] = useState<AIAdvisorResponse | null>(null);
  const [salary, setSalary] = useState<SalarySummaryResponse | null>(null);
  const [recurring, setRecurring] = useState<RecurringResponse[]>([]);
  const [debts, setDebts] = useState<CreditDebtResponse[]>([]);
  const [savingsGoals, setSavingsGoals] = useState<SavingsGoalResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { account, logout } = useAuth();
  const [loadError, setLoadError] = useState('');

  const fetchAllData = useCallback(async (targetYear: number, targetMonth: number) => {
    setIsLoading(true);
    setLoadError('');
    const userId = getCurrentUserId();
    try {
      const [repData, salData, recData, debtsData] = await Promise.all([
        FinanceService.getMonthlyReport(targetYear, targetMonth, userId),
        FinanceService.getSalarySummary(targetYear, targetMonth, userId),
        FinanceService.getRecurring(userId),
        FinanceService.getDebts(userId)
      ]);
      
      setReport(repData);
      setSalary(salData);
      setRecurring(recData);
      setDebts(debtsData);
      setSavingsGoals([]);

    } catch (e) { 
      setLoadError(errorMessage(e));
    } finally { 
      setIsLoading(false); 
    }
  }, []);

  useEffect(() => {
    void fetchAllData(year, month).finally(() => { setIsSplashFading(true); setIsSplashVisible(false); });
  }, [year, month, fetchAllData]);
      
  useEffect(() => {
    if (activeTab === 'ai') {
      FinanceService.getAIAdvice(year, month).then(setAiData).catch(() => setAiData(null));
    }
  }, [activeTab, year, month]);

  const handleEdit = (type: string, item: any) => {
    setEditingData({ type, item });
    setShowModal(true);
  };

  const handleDelete = async (type: string, id: number) => {
    const userId = getCurrentUserId();
    if (type === 'shift') {
      setSalary(prev => prev ? { ...prev, shifts: prev.shifts.filter(s => s.id !== id) } : null);
      try { await FinanceService.deleteShift(id, userId); } catch (e) { fetchAllData(year, month); }
    } else if (type === 'recurring') {
      setRecurring(prev => prev.filter(r => r.id !== id));
      try { await FinanceService.deleteRecurring(id, userId); } catch (e) { fetchAllData(year, month); }
    } else if (type === 'debt') {
      setDebts(prev => prev.filter(d => d.id !== id));
      try { await FinanceService.deleteDebt(id, userId); } catch (e) { fetchAllData(year, month); }
    } else if (type === 'savings') {
      setSavingsGoals(prev => prev.filter(g => g.id !== id));
      try { await FinanceService.deleteSavingsGoal(id, userId); } catch (e) { fetchAllData(year, month); }
    }
  };

  const handleToggleRecurring = async (id: number) => {
    setRecurring(prev => prev.map(r => r.id === id ? { ...r, is_active: !r.is_active } : r));
    try { await FinanceService.toggleRecurring(id, getCurrentUserId()); } catch (e) { fetchAllData(year, month); }
  };

  const handleMarkShiftPaid = async (id: number) => {
    if (!salary) return;
    const targetShift = salary.shifts.find(s => s.id === id);
    if (!targetShift || targetShift.is_paid) return;
    const earned = Number(targetShift.total_earned);
    setSalary({
      ...salary,
      shifts: salary.shifts.map(s => s.id === id ? { ...s, is_paid: true } : s),
      total_paid: Number(salary.total_paid) + earned,
      unpaid_balance: Number(salary.unpaid_balance) - earned
    });
    if (report) setReport({ ...report, total_income: Number(report.total_income) + earned, net_profit: Number(report.net_profit) + earned });
    try { await FinanceService.markShiftPaid(id, getCurrentUserId()); } catch (e) { fetchAllData(year, month); }
  };

  const handlePayDebt = async (id: number, amount: number) => {
    setDebts(prev => prev.map(d => d.id === id ? { ...d, current_balance: Number(d.current_balance) - amount, is_closed: (Number(d.current_balance) - amount) <= 0 } : d));
    try { await FinanceService.payDebt(id, amount, getCurrentUserId()); } catch (e) { fetchAllData(year, month); }
  };

  return (
    <div className="w-full min-h-screen text-[#F3F4F6] font-sans overflow-x-hidden flex flex-col relative selection:bg-blue-500/30">
      
      {/* РЕНДЕР ЭКРАНА ЗАГРУЗКИ ПОВЕРХ ВСЕГО */}
      {isSplashVisible && <SplashScreen isFadingOut={isSplashFading} />}

      <div className="web-account-bar">
        <span><strong>Smart Finance</strong><span className="account-login">{account?.login}</span></span>
        <button type="button" onClick={logout}>Выйти</button>
      </div>

      <header className="web-toolbar shrink-0 pt-4 pb-3 px-4 z-40 bg-[#0A0D14]/80 backdrop-blur-xl border-b border-white/5 flex justify-between items-center">
        <MonthDropdown currentYear={year} currentMonth={month} onChange={(y, m) => { setYear(y); setMonth(m); }} />
        <button aria-label="Добавить операцию или выписку" onClick={() => { setEditingData(null); setShowModal(true); }} className="w-10 h-10 rounded-2xl bg-white/[0.05] backdrop-blur-md flex items-center justify-center border border-white/10 shadow-lg hover:bg-white/10 active:scale-95 transition-all">
          <Upload size={18} className="text-emerald-400" />
        </button>
      </header>

      <main className="web-main flex-1 overflow-y-auto p-4 pb-[120px] [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
        {loadError && <div role="alert" className="mb-4 p-4 rounded-xl bg-rose-500/10 text-rose-200">{loadError} <button onClick={() => fetchAllData(year, month)} className="underline">Повторить</button></div>}
        {activeTab === 'dashboard' && <GlassDashboard report={report} onShowAll={() => setShowAllModal(true)} />}
        
        {activeTab === 'shifts' && (
          <GlassShifts 
            summary={salary} 
            onMarkPaid={handleMarkShiftPaid} 
            onEditShift={(shift) => handleEdit('shift', shift)}
            onDeleteShift={(id) => handleDelete('shift', id)}
          />
        )}
        {activeTab === 'obligations' && (
          <GlassObligations 
            recurring={recurring} debts={debts} savingsGoals={savingsGoals}
            onToggleRecurring={handleToggleRecurring} onPayDebt={handlePayDebt}
            onEditItem={handleEdit} onDeleteItem={handleDelete}
            onOpenPayment={(debt) => setPaymentDebt(debt)} // ДОБАВЛЕНО
          />
        )}
        {activeTab === 'ai' && <GlassAiAdvisor data={aiData} loading={isLoading && !aiData} />}
      </main>

      <GlassNav activeTab={activeTab} onSelectTab={setActiveTab} onOpenUpload={() => { setEditingData(null); setShowModal(true); }} />
      <GlassAllTransactionsModal isOpen={showAllModal} onClose={() => setShowAllModal(false)} report={report} onEdit={tx => handleEdit('transaction', tx)} onDelete={async id => {
        try { await FinanceService.deleteTransaction(id); await fetchAllData(year, month); }
        catch (err) { setLoadError(errorMessage(err)); }
      }} />
      <GlassActionModal isOpen={showModal} onClose={() => { setShowModal(false); setEditingData(null); }} onActionSuccess={() => fetchAllData(year, month)} editData={editingData} />
      <GlassPaymentModal 
        isOpen={!!paymentDebt} 
        onClose={() => setPaymentDebt(null)} 
        debt={paymentDebt} 
        onPaySuccess={handlePayDebt} 
      />
    </div>
  );
}
