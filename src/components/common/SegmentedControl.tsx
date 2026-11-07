import React from 'react';

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: Array<SegmentOption<T>>;
  activeValue: T;
  onChange: (value: T) => void;
  className?: string;
  ariaLabel?: string;
}

export function SegmentedControl<T extends string>({
  options,
  activeValue,
  onChange,
  className = '',
  ariaLabel = 'Tùy chọn phân đoạn',
}: SegmentedControlProps<T>) {
  return (
    <div className={`segmented-control ${className}`} role="tablist" aria-label={ariaLabel}>
      {options.map((opt) => {
        const isActive = opt.value === activeValue;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={isActive ? 'active' : ''}
            onClick={() => onChange(opt.value)}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
