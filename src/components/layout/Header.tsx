import React from 'react';
import { Icon } from '../common/Icon';

interface HeaderProps {
  unreadCount: number;
  onOpenScan?: () => void;
  onOpenBell?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  unreadCount,
  onOpenScan,
  onOpenBell,
}) => {
  return (
    <header className="top-bar">
      <div className="brand-badge">
        <i>
          <Icon name="leaf" size={16} />
        </i>
        <span>Trợ lý kho bếp</span>
      </div>

      <div className="top-bar-actions">
        <button
          type="button"
          className="top-btn"
          data-act="openScan"
          onClick={onOpenScan}
          aria-label="Quét chứng từ nhập xuất"
        >
          <Icon name="scan" size={20} />
          <span>Quét</span>
        </button>

        <button
          type="button"
          className="top-btn"
          data-act="openBell"
          onClick={onOpenBell}
          aria-label={`Thông báo${unreadCount > 0 ? `, ${unreadCount} chưa đọc` : ''}`}
        >
          <Icon name="bell" size={20} />
          {unreadCount > 0 && (
            <span className="notif-badge">{unreadCount}</span>
          )}
        </button>
      </div>
    </header>
  );
};
