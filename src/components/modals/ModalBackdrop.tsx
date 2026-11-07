import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalBackdropProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  maxWidthClass?: string;
}

export const ModalBackdrop: React.FC<ModalBackdropProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  icon,
  children,
  maxWidthClass = 'max-w-xl',
}) => {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-xs transition-opacity duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={`w-full ${maxWidthClass} max-h-[92vh] bg-[var(--card)] text-[var(--ink)] rounded-2xl border border-[var(--line)] shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--line)] bg-[var(--bg)]/50 shrink-0">
          <div className="flex items-center gap-3">
            {icon && (
              <div className="w-9 h-9 rounded-xl bg-[var(--chip)] text-[var(--accent-text)] flex items-center justify-center shrink-0">
                {icon}
              </div>
            )}
            <div>
              <h2 className="text-base font-bold text-[var(--ink)] leading-snug">{title}</h2>
              {subtitle && <p className="text-xs text-[var(--muted)] mt-0.5">{subtitle}</p>}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--ink)] hover:bg-[var(--chip)] transition-colors"
            title="Đóng (Esc)"
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 text-[14px]">
          {children}
        </div>
      </div>
    </div>
  );
};
