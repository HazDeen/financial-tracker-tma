import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { Check, ChevronDown } from 'lucide-react';
import './Dropdown.css';

interface Option<T> { value: T; label: string }
interface DropdownProps<T> {
  label: string;
  hint?: string;
  value: T;
  options: readonly Option<T>[];
  onChange: (value: T) => void;
  disabled?: boolean;
  className?: string;
}

/** Select-only combobox: focus stays on the trigger while arrows navigate the list. */
export function Dropdown<T extends string | number>({ label, hint, value, options, onChange, disabled = false, className = '' }: DropdownProps<T>) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const search = useRef({ text: '', time: 0 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [position, setPosition] = useState({ left: 0, top: 0, width: 0, maxHeight: 256, above: false });
  const selected = Math.max(0, options.findIndex(option => option.value === value));
  const expanded = open && !disabled && options.length > 0;

  useLayoutEffect(() => {
    if (!expanded) return;
    function place() {
      const rect = trigger.current?.getBoundingClientRect();
      if (!rect) return;
      const viewport = window.visualViewport;
      const viewportTop = viewport?.offsetTop ?? 0;
      const viewportLeft = viewport?.offsetLeft ?? 0;
      const viewportHeight = viewport?.height ?? window.innerHeight;
      const viewportWidth = viewport?.width ?? window.innerWidth;
      const desired = Math.min(options.length * 48 + 12, 256);
      const below = viewportTop + viewportHeight - rect.bottom - 16;
      const aboveSpace = rect.top - viewportTop - 16;
      const above = below < desired && aboveSpace > below;
      const maxHeight = Math.max(48, Math.min(desired, above ? aboveSpace : below));
      const width = Math.min(rect.width, viewportWidth - 24);
      setPosition({ width, maxHeight, above,
        left: Math.max(viewportLeft + 12, Math.min(rect.left, viewportLeft + viewportWidth - width - 12)),
        top: above ? rect.top - maxHeight - 8 : rect.bottom + 8 });
    }
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    window.visualViewport?.addEventListener('resize', place);
    window.visualViewport?.addEventListener('scroll', place);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
      window.visualViewport?.removeEventListener('resize', place);
      window.visualViewport?.removeEventListener('scroll', place);
    };
  }, [expanded, options.length]);

  useEffect(() => {
    if (!expanded) return;
    const dismiss = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!trigger.current?.contains(target) && !list.current?.contains(target)) setOpen(false);
    };
    document.addEventListener('pointerdown', dismiss);
    return () => document.removeEventListener('pointerdown', dismiss);
  }, [expanded]);

  useLayoutEffect(() => {
    if (!expanded) return;
    const option = list.current?.children[active] as HTMLElement | undefined;
    if (option && list.current) {
      const top = option.offsetTop;
      const bottom = top + option.offsetHeight;
      if (top < list.current.scrollTop) list.current.scrollTop = top;
      else if (bottom > list.current.scrollTop + list.current.clientHeight) list.current.scrollTop = bottom - list.current.clientHeight;
    }
  }, [expanded, active]);

  function show(index = selected) {
    search.current = { text: '', time: 0 };
    setActive(index); setOpen(true);
  }
  function choose(index: number) {
    const option = options[index];
    if (option) onChange(option.value);
    setOpen(false); trigger.current?.focus();
  }
  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (disabled || !options.length) return;
    const last = options.length - 1;
    if (event.key === 'Tab') { setOpen(false); return; }
    if (event.key === 'Escape') {
      if (expanded) { event.preventDefault(); event.stopPropagation(); setOpen(false); }
      return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault(); if (expanded) choose(active); else show(); return;
    }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      if (event.altKey && event.key === 'ArrowUp') { setOpen(false); return; }
      if (!expanded) show(event.key === 'Home' ? 0 : event.key === 'End' ? last : selected);
      else setActive(previous => event.key === 'Home' ? 0 : event.key === 'End' ? last : Math.max(0, Math.min(last, previous + (event.key === 'ArrowDown' ? 1 : -1))));
      return;
    }
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      const now = Date.now();
      const text = (now - search.current.time < 700 ? search.current.text : '') + event.key.toLocaleLowerCase('ru');
      search.current = { text, time: now };
      const index = options.findIndex(option => option.label.toLocaleLowerCase('ru').startsWith(text));
      if (index >= 0) { setActive(index); setOpen(true); }
    }
  }

  return <div className={`dropdown-field ${className}`}>
    <label className="dropdown-label" id={`${id}-label`} htmlFor={`${id}-trigger`}>{label}</label>
    <button ref={trigger} id={`${id}-trigger`} type="button" role="combobox" className="dropdown-trigger"
      aria-labelledby={`${id}-label`} aria-describedby={hint ? `${id}-hint` : undefined}
      aria-haspopup="listbox" aria-expanded={expanded} aria-controls={expanded ? `${id}-list` : undefined}
      aria-activedescendant={expanded ? `${id}-option-${active}` : undefined}
      disabled={disabled || !options.length} onKeyDown={onKeyDown} onBlur={() => setOpen(false)}
      onClick={() => { if (expanded) setOpen(false); else show(); }}>
      <span>{options[selected]?.label ?? 'Выберите значение'}</span><ChevronDown size={18} aria-hidden="true" />
    </button>
    {hint && <small id={`${id}-hint`} className="dropdown-hint">{hint}</small>}
    {expanded && createPortal(<div ref={list} id={`${id}-list`} role="listbox" aria-labelledby={`${id}-label`}
      className="dropdown-menu" data-above={position.above || undefined}
      style={{ left: position.left, top: position.top, width: position.width, maxHeight: position.maxHeight }}
      onPointerDown={event => event.preventDefault()}>
      {options.map((option, index) => <div key={option.value} id={`${id}-option-${index}`} role="option"
        aria-selected={option.value === value} className="dropdown-option" data-active={active === index || undefined}
        onPointerMove={event => { if (event.pointerType === 'mouse') setActive(index); }}
        onClick={() => choose(index)}>
        <span>{option.label}</span>{option.value === value && <Check size={18} aria-hidden="true" />}
      </div>)}
    </div>, document.body)}
  </div>;
}
