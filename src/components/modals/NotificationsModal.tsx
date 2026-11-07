import React, { useState } from 'react';
import { ModalBackdrop } from './ModalBackdrop';
import { simulationStore, formatMoney, formatQty } from '../../services/mock/simulationStore';
import {
  Bell,
  CheckCircle,
  AlertTriangle,
  Clock,
  ArrowRight,
  Filter,
  CheckCheck,
  Check,
  CookingPot,
  Scale
} from 'lucide-react';

interface NotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenProcessBatch: (batchId: string) => void;
  onShowToast: (msg: string) => void;
}

export const NotificationsModal: React.FC<NotificationsModalProps> = ({
  isOpen,
  onClose,
  onOpenProcessBatch,
  onShowToast,
}) => {
  const [filter, setFilter] = useState<'ALL' | 'UNREAD' | 'EXPIRED' | 'SOON' | 'SHORTAGE'>('ALL');
  const [resolvingShortageId, setResolvingShortageId] = useState<string | null>(null);

  const notifications = simulationStore.getNotificationsList();
  const unreadCount = simulationStore.getUnreadNotificationsCount();

  const filteredList = notifications.filter((item) => {
    if (filter === 'UNREAD') return !item.read;
    if (filter === 'EXPIRED') return item.type === 'expired';
    if (filter === 'SOON') return item.type === 'soon';
    if (filter === 'SHORTAGE') return item.type === 'shortage';
    return true;
  });

  const handleMarkAllRead = () => {
    simulationStore.markAllNotificationsRead();
    onShowToast('Đã đánh dấu tất cả thông báo là đã đọc.');
  };

  const handleItemClick = (key: string) => {
    simulationStore.markNotificationRead(key);
  };

  const handleResolveOptionC = (
    shortageId: string,
    action: 'CONSUMED_FROM_STOCK' | 'WRITE_OFF_ESTIMATED' | 'WAIVED'
  ) => {
    try {
      const res = simulationStore.resolveShortage(shortageId, action);
      onShowToast(res.message);
      setResolvingShortageId(null);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      onShowToast(`Lỗi: ${errMsg}`);
    }
  };

  return (
    <ModalBackdrop
      isOpen={isOpen}
      onClose={onClose}
      title="Trung tâm thông báo"
      subtitle={`${unreadCount} cảnh báo chưa đọc cần chú ý trong kho`}
      icon={<Bell size={20} />}
      maxWidthClass="max-w-2xl"
    >
      <div className="space-y-4">
        {/* Filter Bar & Mark All Read */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] pb-3">
          <div className="flex flex-wrap items-center gap-1">
            <button
              type="button"
              onClick={() => setFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'ALL'
                  ? 'bg-[var(--ink)] text-[var(--bg)]'
                  : 'bg-[var(--chip)] text-[var(--muted)] hover:text-[var(--ink)]'
              }`}
            >
              Tất cả ({notifications.length})
            </button>
            <button
              type="button"
              onClick={() => setFilter('UNREAD')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'UNREAD'
                  ? 'bg-[var(--accent)] text-[var(--on-accent)]'
                  : 'bg-[var(--chip)] text-[var(--muted)] hover:text-[var(--ink)]'
              }`}
            >
              Chưa đọc ({unreadCount})
            </button>
            <button
              type="button"
              onClick={() => setFilter('EXPIRED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'EXPIRED'
                  ? 'bg-[var(--bad-fg)] text-white'
                  : 'bg-[var(--chip)] text-[var(--muted)] hover:text-[var(--ink)]'
              }`}
            >
              Đã hết hạn
            </button>
            <button
              type="button"
              onClick={() => setFilter('SOON')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'SOON'
                  ? 'bg-[var(--warn-fg)] text-white'
                  : 'bg-[var(--chip)] text-[var(--muted)] hover:text-[var(--ink)]'
              }`}
            >
              Sắp hết hạn
            </button>
            <button
              type="button"
              onClick={() => setFilter('SHORTAGE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === 'SHORTAGE'
                  ? 'bg-[var(--accent-text)] text-white'
                  : 'bg-[var(--chip)] text-[var(--muted)] hover:text-[var(--ink)]'
              }`}
            >
              Option C
            </button>
          </div>

          {unreadCount > 0 && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              className="text-xs font-semibold text-[var(--muted)] hover:text-[var(--accent-text)] flex items-center gap-1 transition-colors"
            >
              <CheckCheck size={14} /> Đánh dấu đã đọc
            </button>
          )}
        </div>

        {/* Notifications List */}
        <div className="space-y-2.5 max-h-[60vh] overflow-y-auto pr-1">
          {filteredList.length === 0 ? (
            <div className="py-12 text-center text-[var(--muted)] text-xs">
              <CheckCircle size={32} className="mx-auto mb-2 text-[var(--ok-fg)] opacity-70" />
              Không có thông báo nào trong mục này. Tồn kho và vận hành đang ổn định.
            </div>
          ) : (
            filteredList.map((notif) => (
              <div
                key={notif.id}
                onClick={() => handleItemClick(notif.key)}
                className={`p-3.5 rounded-xl border transition-all text-xs flex flex-col gap-2 ${
                  notif.read
                    ? 'bg-[var(--card)] border-[var(--line)] opacity-80'
                    : notif.severity === 'bad'
                    ? 'bg-[var(--bad-bg)]/30 border-[var(--bad-fg)]/40 shadow-xs'
                    : notif.severity === 'warn'
                    ? 'bg-[var(--warn-bg)]/30 border-[var(--warn-fg)]/40 shadow-xs'
                    : 'bg-[var(--ok-bg)]/30 border-[var(--ok-fg)]/40 shadow-xs'
                }`}
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-md font-bold text-[10px] uppercase tracking-wide ${
                        notif.severity === 'bad'
                          ? 'bg-[var(--bad-bg)] text-[var(--bad-fg)]'
                          : notif.severity === 'warn'
                          ? 'bg-[var(--warn-bg)] text-[var(--warn-fg)]'
                          : 'bg-[var(--ok-bg)] text-[var(--ok-fg)]'
                      }`}
                    >
                      {notif.type === 'expired'
                        ? 'Đã hết hạn'
                        : notif.type === 'soon'
                        ? 'Cận date'
                        : 'Option C'}
                    </span>
                    <span className="font-bold text-[var(--ink)] text-sm">{notif.title}</span>
                  </div>

                  <span className="text-[11px] text-[var(--muted)] whitespace-nowrap">
                    {notif.date}
                  </span>
                </div>

                {/* Message Body */}
                <p className="text-[var(--ink)] leading-relaxed text-xs">{notif.message}</p>

                {/* Quick Action Rows */}
                {notif.batchId && (
                  <div className="flex items-center justify-end gap-2 pt-1 border-t border-[var(--line)]/50 mt-1">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onClose();
                        onOpenProcessBatch(notif.batchId!);
                      }}
                      className="px-3 py-1.5 rounded-lg bg-[var(--accent)] hover:opacity-90 text-[var(--on-accent)] font-semibold text-xs flex items-center gap-1 transition-all"
                    >
                      <span>Xử lý lô hàng này</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                )}

                {/* Option C Resolution buttons for shortage */}
                {notif.shortageId && notif.severity === 'warn' && (
                  <div className="pt-2 border-t border-[var(--line)]/50 mt-1 space-y-2">
                    <span className="text-[11px] font-semibold text-[var(--muted)] block">
                      Giải quyết thiếu hụt Option C:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResolveOptionC(notif.shortageId!, 'CONSUMED_FROM_STOCK');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-[var(--card)] border border-[var(--ok-fg)] text-[var(--ok-fg)] hover:bg-[var(--ok-bg)] text-[11px] font-semibold transition-colors flex items-center gap-1"
                      >
                        <CookingPot size={13} />
                        <span>Trừ bù từ kho</span>
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResolveOptionC(notif.shortageId!, 'WRITE_OFF_ESTIMATED');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-[var(--card)] border border-[var(--accent-text)] text-[var(--accent-text)] hover:bg-[var(--warn-bg)] text-[11px] font-semibold transition-colors flex items-center gap-1"
                      >
                        <Scale size={13} />
                        <span>Ghi nhận chi phí ước tính</span>
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleResolveOptionC(notif.shortageId!, 'WAIVED');
                        }}
                        className="px-2.5 py-1 rounded-lg bg-[var(--card)] border border-[var(--line)] text-[var(--muted)] hover:text-[var(--ink)] text-[11px] font-semibold transition-colors flex items-center gap-1"
                      >
                        <Check size={13} />
                        <span>Miễn trừ chênh lệch</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </ModalBackdrop>
  );
};
