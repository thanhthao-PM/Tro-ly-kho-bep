/**
 * Danh mục URL endpoints chuẩn theo docs/API_SPEC.md.
 */

export const ENDPOINTS = {
  HEALTH: '/health',
  ME: '/me',
  SETTINGS: '/settings',

  // Catalog
  UNITS: '/units',
  INGREDIENTS: '/ingredients',
  INGREDIENT_DETAIL: (id: string) => `/ingredients/${id}`,

  // Inventory
  INVENTORY_INGREDIENTS: '/inventory/ingredients',
  INVENTORY_BATCHES: (ingredientId: string) => `/inventory/ingredients/${ingredientId}/batches`,
  BATCH_DETAIL: (id: string) => `/batches/${id}`,
  BATCH_CREATE: '/batches',
  BATCH_ADJUST: (id: string) => `/batches/${id}/adjustments`,
  INVENTORY_SUMMARY: '/inventory/summary',
  STOCK_MOVEMENTS: '/stock-movements',

  // Documents
  DOCUMENTS: '/documents',
  DOCUMENT_DETAIL: (id: string) => `/documents/${id}`,
  DOCUMENT_LINES: (docId: string) => `/documents/${docId}/lines`,
  DOCUMENT_LINE_DETAIL: (docId: string, lineId: string) => `/documents/${docId}/lines/${lineId}`,
  DOCUMENT_CONFIRM: (id: string) => `/documents/${id}/confirm`,
  DOCUMENT_CANCEL: (id: string) => `/documents/${id}/cancel`,

  // Menu & Sales
  DISHES: '/dishes',
  DISH_DETAIL: (id: string) => `/dishes/${id}`,
  SALES: '/sales',
  SALE_DETAIL: (id: string) => `/sales/${id}`,
  SHORTAGES: '/shortages',
  SHORTAGE_RESOLVE: (id: string) => `/shortages/${id}/resolve`,

  // Disposals
  EXPIRING_BATCHES: '/expiring-batches',
  DISPOSALS: (batchId: string) => `/batches/${batchId}/disposals`,
  COOK_BATCH: (batchId: string) => `/batches/${batchId}/cook`,

  // Notifications
  NOTIFICATIONS: '/notifications',
  NOTIFICATIONS_READ: '/notifications/read',

  // Reports
  REPORT_SUMMARY: '/reports/summary',
  REPORT_WASTE: '/reports/waste',
  REPORT_DISHES: '/reports/dishes',
  REPLENISHMENT_SUGGESTIONS: '/replenishment-suggestions',

  // Assistant
  ASSISTANT_MESSAGES: '/assistant/messages',
};
