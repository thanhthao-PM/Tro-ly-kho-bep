import React from 'react';
import { Icon, IconName } from '../common/Icon';

export type MainTab = 'kho' | 'mon' | 'ai' | 'tk';

interface NavItem {
  id: MainTab;
  label: string;
  icon: IconName;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'kho', label: 'Kho', icon: 'box' },
  { id: 'mon', label: 'Thực đơn', icon: 'book' },
  { id: 'ai', label: 'Trợ lí AI', icon: 'spark' },
  { id: 'tk', label: 'Thống kê', icon: 'chart' },
];

interface NavigationProps {
  currentTab: MainTab;
  onSelectTab: (tab: MainTab) => void;
}

export const Navigation: React.FC<NavigationProps> = ({ currentTab, onSelectTab }) => {
  return (
    <nav className="nav-bottom" aria-label="Điều hướng chính">
      {NAV_ITEMS.map((item) => {
        const isActive = currentTab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={isActive ? 'active' : ''}
            onClick={() => onSelectTab(item.id)}
            aria-current={isActive ? 'page' : undefined}
          >
            <Icon name={item.icon} size={22} />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
};
