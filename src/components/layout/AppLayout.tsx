import React from 'react';
import { Header } from './Header';
import { Navigation, MainTab } from './Navigation';
import { Toast } from '../common/Toast';

interface AppLayoutProps {
  currentTab: MainTab;
  onSelectTab: (tab: MainTab) => void;
  unreadNotificationsCount: number;
  toastMessage: string | null;
  onOpenScan: () => void;
  onOpenUploadFile: () => void;
  onOpenUploadImage: () => void;
  onOpenBell: () => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentTab,
  onSelectTab,
  unreadNotificationsCount,
  toastMessage,
  onOpenScan,
  onOpenUploadFile,
  onOpenUploadImage,
  onOpenBell,
  children,
}) => {
  return (
    <div className="app-stage">
      <div className="app-phone" id="app-shell">
        {/* Top Header */}
        <Header
          unreadCount={unreadNotificationsCount}
          onOpenScan={onOpenScan}
          onOpenUploadFile={onOpenUploadFile}
          onOpenUploadImage={onOpenUploadImage}
          onOpenBell={onOpenBell}
        />

        {/* Navigation: Responsive (Bottom on Mobile < 900px, Sidebar on Desktop >= 900px) */}
        <Navigation currentTab={currentTab} onSelectTab={onSelectTab} />

        {/* Main Content Area */}
        <main className="main-content" id="main-scroll">
          {children}
        </main>

        {/* Toast Notification */}
        <Toast message={toastMessage} />
      </div>
    </div>
  );
};
