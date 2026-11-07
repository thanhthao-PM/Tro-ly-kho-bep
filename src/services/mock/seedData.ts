/**
 * Dữ liệu mẫu chuẩn hoá của hệ thống Trợ lý kho bếp.
 * Khớp 100% với file demo HTML (demogiaodien.html) và Architecture Revision 6.3.
 * Dùng làm nguồn chân lý duy nhất cho cả Frontend Preview và Backend CLI Seeder.
 */

export interface MasterProduct {
  name: string;
  unit: string;
  shelf_life_days: number;
  location: 'FRIDGE' | 'FREEZER' | 'PANTRY';
  default_cost_vnd: number;
  usual_quantity: [number, number];
  storage_tip: string;
}

export const MASTER_PRODUCTS: Record<string, MasterProduct> = {
  'rau muống': {
    name: 'rau muống',
    unit: 'kg',
    shelf_life_days: 3,
    location: 'FRIDGE',
    default_cost_vnd: 20000,
    usual_quantity: [1, 2],
    storage_tip: 'Bọc giấy báo hoặc khăn khô, để ngăn rau, không rửa trước khi cất.',
  },
  'sữa tươi': {
    name: 'sữa tươi',
    unit: 'hộp',
    shelf_life_days: 7,
    location: 'FRIDGE',
    default_cost_vnd: 30000,
    usual_quantity: [2, 6],
    storage_tip: 'Đậy kín, để ngăn trong cùng của tủ, tránh cửa tủ. Mở hộp rồi nên dùng trong 3 ngày.',
  },
  'trứng gà': {
    name: 'trứng gà',
    unit: 'quả',
    shelf_life_days: 21,
    location: 'FRIDGE',
    default_cost_vnd: 3500,
    usual_quantity: [20, 40],
    storage_tip: 'Để đầu nhọn xuống, không rửa vỏ trước khi cất.',
  },
  'cà chua': {
    name: 'cà chua',
    unit: 'kg',
    shelf_life_days: 7,
    location: 'FRIDGE',
    default_cost_vnd: 35000,
    usual_quantity: [1, 3],
    storage_tip: 'Cà chua chín để ngăn mát, chưa chín để ngoài và tránh nắng.',
  },
  'hành lá': {
    name: 'hành lá',
    unit: 'bó',
    shelf_life_days: 5,
    location: 'FRIDGE',
    default_cost_vnd: 8000,
    usual_quantity: [2, 5],
    storage_tip: 'Bọc giấy ẩm hoặc cắm gốc vào cốc nước nông, để ngăn rau.',
  },
  'thịt ba rọi': {
    name: 'thịt ba rọi',
    unit: 'kg',
    shelf_life_days: 30,
    location: 'FREEZER',
    default_cost_vnd: 150000,
    usual_quantity: [1, 3],
    storage_tip: 'Chia từng phần, bọc kín rồi cấp đông. Rã đông ở ngăn mát, không rã đông rồi cấp đông lại.',
  },
  'ức gà': {
    name: 'ức gà',
    unit: 'kg',
    shelf_life_days: 3,
    location: 'FRIDGE',
    default_cost_vnd: 85000,
    usual_quantity: [1, 3],
    storage_tip: 'Đựng hộp kín ở ngăn dưới cùng để nước không nhỏ sang đồ ăn khác.',
  },
  'gạo': {
    name: 'gạo',
    unit: 'kg',
    shelf_life_days: 365,
    location: 'PANTRY',
    default_cost_vnd: 24000,
    usual_quantity: [5, 20],
    storage_tip: 'Đựng thùng kín, nơi khô mát, tránh ẩm và côn trùng.',
  },
  'hành tây': {
    name: 'hành tây',
    unit: 'kg',
    shelf_life_days: 21,
    location: 'PANTRY',
    default_cost_vnd: 30000,
    usual_quantity: [1, 3],
    storage_tip: 'Để nơi khô thoáng, tránh để gần khoai tây.',
  },
  'tỏi': {
    name: 'tỏi',
    unit: 'kg',
    shelf_life_days: 30,
    location: 'PANTRY',
    default_cost_vnd: 60000,
    usual_quantity: [0.3, 1],
    storage_tip: 'Để nơi khô thoáng, không đóng kín trong túi nylon.',
  },
  'đậu hũ': {
    name: 'đậu hũ',
    unit: 'bìa',
    shelf_life_days: 4,
    location: 'FRIDGE',
    default_cost_vnd: 6000,
    usual_quantity: [4, 10],
    storage_tip: 'Ngâm trong nước sạch, thay nước mỗi ngày và để tủ lạnh.',
  },
  'nấm': {
    name: 'nấm',
    unit: 'kg',
    shelf_life_days: 5,
    location: 'FRIDGE',
    default_cost_vnd: 90000,
    usual_quantity: [0.5, 2],
    storage_tip: 'Bọc giấy thấm, để hộp thoáng ở ngăn mát, không rửa trước khi cất.',
  },
  'dưa leo': {
    name: 'dưa leo',
    unit: 'kg',
    shelf_life_days: 7,
    location: 'FRIDGE',
    default_cost_vnd: 25000,
    usual_quantity: [1, 3],
    storage_tip: 'Lau khô, bọc giấy và để ngăn rau.',
  },
  'thịt bằm': {
    name: 'thịt bằm',
    unit: 'kg',
    shelf_life_days: 2,
    location: 'FRIDGE',
    default_cost_vnd: 120000,
    usual_quantity: [1, 2],
    storage_tip: 'Dùng trong 1–2 ngày hoặc chia nhỏ cấp đông ngay.',
  },
  'bột mì': {
    name: 'bột mì',
    unit: 'kg',
    shelf_life_days: 180,
    location: 'PANTRY',
    default_cost_vnd: 25000,
    usual_quantity: [1, 5],
    storage_tip: 'Đựng hộp kín, nơi khô mát.',
  },
};

export const INITIAL_DISHES = [
  {
    name: 'Trứng chiên cà chua',
    price_vnd: 35000,
    ingredients: [
      { name: 'cà chua', quantity: '0.1' },
      { name: 'trứng gà', quantity: '2' },
      { name: 'hành lá', quantity: '0.1' },
    ],
  },
  {
    name: 'Canh cà chua trứng',
    price_vnd: 30000,
    ingredients: [
      { name: 'cà chua', quantity: '0.1' },
      { name: 'trứng gà', quantity: '1' },
      { name: 'hành lá', quantity: '0.1' },
    ],
  },
  {
    name: 'Bánh pancake sữa',
    price_vnd: 40000,
    ingredients: [
      { name: 'sữa tươi', quantity: '0.2' },
      { name: 'trứng gà', quantity: '1' },
      { name: 'bột mì', quantity: '0.1' },
    ],
  },
  {
    name: 'Rau muống xào tỏi',
    price_vnd: 30000,
    ingredients: [
      { name: 'rau muống', quantity: '0.2' },
      { name: 'tỏi', quantity: '0.02' },
    ],
  },
  {
    name: 'Thịt kho trứng',
    price_vnd: 65000,
    ingredients: [
      { name: 'thịt ba rọi', quantity: '0.15' },
      { name: 'trứng gà', quantity: '2' },
      { name: 'hành tây', quantity: '0.05' },
    ],
  },
  {
    name: 'Gà xào nấm',
    price_vnd: 60000,
    ingredients: [
      { name: 'ức gà', quantity: '0.15' },
      { name: 'nấm', quantity: '0.1' },
      { name: 'hành tây', quantity: '0.05' },
      { name: 'tỏi', quantity: '0.01' },
    ],
  },
  {
    name: 'Đậu hũ sốt cà chua',
    price_vnd: 35000,
    ingredients: [
      { name: 'đậu hũ', quantity: '1' },
      { name: 'cà chua', quantity: '0.1' },
      { name: 'hành lá', quantity: '0.1' },
    ],
  },
  {
    name: 'Cơm chiên trứng',
    price_vnd: 40000,
    ingredients: [
      { name: 'gạo', quantity: '0.15' },
      { name: 'trứng gà', quantity: '2' },
      { name: 'hành lá', quantity: '0.1' },
    ],
  },
  {
    name: 'Canh dưa leo thịt bằm',
    price_vnd: 35000,
    ingredients: [
      { name: 'dưa leo', quantity: '0.15' },
      { name: 'thịt bằm', quantity: '0.05' },
      { name: 'hành lá', quantity: '0.1' },
    ],
  },
];
