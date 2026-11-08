import React, { useState, useEffect, useCallback } from 'react';
import { simulationStore } from './services/mock/simulationStore';
import { AppLayout } from './components/layout/AppLayout';
import { MainTab } from './components/layout/Navigation';
import { KhoView } from './views/KhoView';
import { MenuView } from './views/MenuView';
import { AssistantView } from './views/AssistantView';
import { ReportsView } from './views/ReportsView';

// Modals
import { ScanModal } from './components/modals/ScanModal';
import { NotificationsModal } from './components/modals/NotificationsModal';
import { ItemDetailModal } from './components/modals/ItemDetailModal';
import { ProcessBatchModal } from './components/modals/ProcessBatchModal';
import { RecipeModal } from './components/modals/RecipeModal';
import { InventoryEditModal } from './components/modals/InventoryEditModal';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<MainTab>('kho');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [storeVersion, setStoreVersion] = useState<number>(0);
  const [invoiceRefreshKey, setInvoiceRefreshKey] = useState(0);
  const [scanBusinessDate, setScanBusinessDate] = useState<string | undefined>();

  // Modals Visibility States
  const [isScanOpen, setIsScanOpen] = useState(false);
  const [isBellOpen, setIsBellOpen] = useState(false);
  const [selectedProductForDetail, setSelectedProductForDetail] = useState<string | null>(null);
  const [selectedBatchForProcess, setSelectedBatchForProcess] = useState<string | null>(null);
  const [selectedBatchForEdit, setSelectedBatchForEdit] = useState<string | null>(null);
  const [isInventoryEditOpen, setIsInventoryEditOpen] = useState(false);
  const [recipeModalState, setRecipeModalState] = useState<{ isOpen: boolean; dishId: string | null }>({
    isOpen: false,
    dishId: null,
  });

  // Subscribe to simulationStore updates
  useEffect(() => {
    const updateUnread = () => {
      setUnreadCount(simulationStore.getUnreadNotificationsCount());
      setStoreVersion((v) => v + 1);
    };

    updateUnread();
    const unsubscribe = simulationStore.subscribe(updateUnread);
    return () => unsubscribe();
  }, []);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((cur) => (cur === msg ? null : cur));
    }, 2800);
  }, []);

  const handleTabChange = (tab: MainTab) => {
    setCurrentTab(tab);
    const mainEl = document.getElementById('main-scroll');
    if (mainEl) mainEl.scrollTop = 0;
  };

  // Modal Triggers
  const handleOpenScan = (businessDate?: string) => {
    setScanBusinessDate(businessDate);
    setIsScanOpen(true);
  };

  const handleOpenBell = () => {
    setIsBellOpen(true);
  };

  const handleOpenEdit = () => {
    setSelectedBatchForEdit(null);
    setIsInventoryEditOpen(true);
  };

  const handleOpenDetail = (productName: string) => {
    setSelectedProductForDetail(productName);
  };

  const handleOpenDishDetail = (dishId: string) => {
    setRecipeModalState({ isOpen: true, dishId });
  };

  const handleOpenNewDish = () => {
    setRecipeModalState({ isOpen: true, dishId: null });
  };

  const handleProcessBatch = (batchId: string) => {
    setSelectedBatchForProcess(batchId);
  };

  const handleOpenEditSpecificBatch = (batchId: string) => {
    setSelectedBatchForEdit(batchId);
    setIsInventoryEditOpen(true);
  };

  return (
    <>
      <AppLayout
        currentTab={currentTab}
        onSelectTab={handleTabChange}
        unreadNotificationsCount={unreadCount}
        toastMessage={toastMessage}
        onOpenScan={handleOpenScan}
        onOpenBell={handleOpenBell}
      >
        {currentTab === 'kho' && (
          <KhoView
            key={`kho-${storeVersion}`}
            onNavigateToAI={() => handleTabChange('ai')}
            onOpenEdit={handleOpenEdit}
            onOpenDetail={handleOpenDetail}
          />
        )}

        {currentTab === 'mon' && (
          <MenuView
            key={`mon-${storeVersion}`}
            onOpenDishDetail={handleOpenDishDetail}
            onOpenNewDish={handleOpenNewDish}
            onShowToast={showToast}
          />
        )}

        {currentTab === 'ai' && (
          <AssistantView
            key={`ai-${storeVersion}`}
            onProcessBatch={handleProcessBatch}
            onOpenScan={handleOpenScan}
            onOpenBell={handleOpenBell}
            onOpenDish={(dishId) => dishId && handleOpenDishDetail(dishId)}
            onShowToast={showToast}
          />
        )}

        {currentTab === 'tk' && (
          <ReportsView
            key={`tk-${storeVersion}`}
            onNavigateToAI={() => handleTabChange('ai')}
            onShowToast={showToast}
            onOpenScan={(businessDate) => handleOpenScan(businessDate)}
            invoiceRefreshKey={invoiceRefreshKey}
          />
        )}
      </AppLayout>

      {/* 1. Modal Quét chứng từ (Scan Modal) */}
      <ScanModal
        isOpen={isScanOpen}
        onClose={() => setIsScanOpen(false)}
        onShowToast={showToast}
        initialBusinessDate={scanBusinessDate}
        onReceiptSaved={() => setInvoiceRefreshKey((key) => key + 1)}
      />

      {/* 2. Modal Trung tâm thông báo (Notifications Modal) */}
      <NotificationsModal
        isOpen={isBellOpen}
        onClose={() => setIsBellOpen(false)}
        onOpenProcessBatch={(bId) => {
          setSelectedBatchForProcess(bId);
        }}
        onShowToast={showToast}
      />

      {/* 3. Modal Chi tiết nguyên liệu & các đợt nhập (Item Detail Modal) */}
      <ItemDetailModal
        isOpen={!!selectedProductForDetail}
        onClose={() => setSelectedProductForDetail(null)}
        productName={selectedProductForDetail}
        onOpenProcessBatch={(bId) => {
          setSelectedBatchForProcess(bId);
        }}
        onOpenEditBatch={(bId) => {
          handleOpenEditSpecificBatch(bId);
        }}
      />

      {/* 4. Modal Xử lý lô hàng (Process Batch Modal) */}
      <ProcessBatchModal
        isOpen={!!selectedBatchForProcess}
        onClose={() => setSelectedBatchForProcess(null)}
        batchId={selectedBatchForProcess}
        onShowToast={showToast}
      />

      {/* 5. Modal Công thức món ăn & Thêm món (Recipe Modal) */}
      <RecipeModal
        isOpen={recipeModalState.isOpen}
        onClose={() => setRecipeModalState({ isOpen: false, dishId: null })}
        dishId={recipeModalState.dishId}
        onShowToast={showToast}
      />

      {/* 6. Modal Quản lý & Chỉnh sửa kho (Inventory Edit Modal) */}
      <InventoryEditModal
        isOpen={isInventoryEditOpen}
        onClose={() => {
          setIsInventoryEditOpen(false);
          setSelectedBatchForEdit(null);
        }}
        initialBatchId={selectedBatchForEdit}
        onShowToast={showToast}
      />
    </>
  );
};

export default App;
