import React from 'react';

export interface ChipOption<T extends string> {
  value: T;
  label: string;
}

interface FilterChipsProps<T extends string> {
  options: Array<ChipOption<T>>;
  activeValue: T;
  onChange: (value: T) => void;
  className?: string;
  ariaLabel?: string;
}

export function FilterChips<T extends string>({
  options,
  activeValue,
  onChange,
  className = '',
  ariaLabel = 'Bộ lọc thẻ',
}: FilterChipsProps<T>) {
  return (
    <div className={`chips-bar ${className}`} role="group" aria-label={ariaLabel}>
      {options.map((opt) => {
        const isActive = opt.value === activeValue;
        return (
          <button
            key={opt.value}
            type="button"
            className={`filter-chip ${isActive ? 'active' : ''}`}
            onClick={() => onChange(opt.value)}
            aria-pressed={isActive}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
