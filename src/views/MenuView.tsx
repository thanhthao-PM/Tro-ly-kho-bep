import React, { useState, useMemo } from 'react';
import {
  simulationStore,
  formatMoney,
  capitalize,
  DishRankItem,
} from '../services/mock/simulationStore';
import { Icon } from '../components/common/Icon';

interface MenuViewProps {
  onOpenDishDetail: (dishId: string) => void;
  onOpenNewDish: () => void;
  onShowToast: (msg: string) => void;
}

export const MenuView: React.FC<MenuViewProps> = ({
  onOpenDishDetail,
  onOpenNewDish,
  onShowToast,
}) => {
  const [, setRefreshKey] = useState(0);
  const dishRankList = useMemo(() => simulationStore.getDishRank(), []);

  const handlePriceChange = (dishId: string, valueStr: string) => {
    const val = parseFloat(valueStr);
    if (!isNaN(val) && val >= 0) {
      simulationStore.setDishPrice(dishId, val);
      setRefreshKey((k) => k + 1);
      onShowToast('Đã cập nhật giá bán món ăn.');
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="view-hd view-hdrow">
        <div>
          <small>Giá bán, giá vốn và lãi mỗi phần</small>
          <h1>Thực đơn</h1>
        </div>
        <button
          type="button"
          className="pill-btn"
          onClick={onOpenNewDish}
          aria-label="Thêm món mới vào thực đơn"
        >
          <Icon name="plus" size={16} />
          <span>Thêm món</span>
        </button>
      </div>

      {/* Info Banner */}
      <div
        className="ui-card"
        style={{
          background: 'var(--ok-bg)',
          color: 'var(--ok-fg)',
          border: 'none',
          marginTop: '14px',
        }}
      >
        <span style={{ fontSize: '13px', lineHeight: 1.5 }}>
          <b>Lãi gộp mỗi phần = Giá bán − Giá vốn.</b> Giá vốn tính theo định lượng của món và giá nhập thực tế của các đợt còn dùng được. Bấm Chi tiết để xem hoặc sửa định lượng.
        </span>
      </div>

      {/* Dishes List */}
      <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {dishRankList.length === 0 ? (
          <div style={{ marginTop: '28px', textAlign: 'center', color: 'var(--muted)', lineHeight: 1.5 }}>
            Thực đơn đang trống. Bấm Thêm món để tạo món đầu tiên.
          </div>
        ) : (
          dishRankList.map((item: DishRankItem) => {
            const statusText =
              item.maxPortions > 0
                ? `Làm được ${item.maxPortions} phần với kho hiện tại`
                : `Thiếu: ${item.missingIngredients.map(capitalize).join(', ')}`;

            const isProfitable = item.grossMargin >= 0;

            return (
              <div key={item.dish.id} className="ui-card">
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h3>{item.dish.name}</h3>
                    {item.usesExpiring && (
                      <span
                        className="status-tag tag-warn"
                        style={{ fontSize: '11px', padding: '3px 8px' }}
                      >
                        Ưu tiên: dùng lô cận date
                      </span>
                    )}
                  </div>
                  <span className="product-sub" style={{ marginTop: '2px' }}>
                    {statusText}
                  </span>
                </div>

                {/* Metrics */}
                <div className="metrics-grid">
                  <div>
                    <span>Giá bán</span>
                    <input
                      type="number"
                      min="0"
                      step="1000"
                      className="ui-input"
                      style={{ height: '34px', padding: '0 8px', fontWeight: 700 }}
                      defaultValue={item.price}
                      onBlur={(e) => handlePriceChange(item.dish.id, e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handlePriceChange(item.dish.id, (e.target as HTMLInputElement).value);
                          (e.target as HTMLInputElement).blur();
                        }
                      }}
                      aria-label={`Giá bán ${item.dish.name}`}
                    />
                  </div>

                  <div>
                    <span>Giá vốn</span>
                    <b style={{ lineHeight: '34px' }}>{formatMoney(item.cost)}</b>
                  </div>

                  <div>
                    <span>Lãi / phần</span>
                    <b
                      style={{
                        lineHeight: '34px',
                        color: isProfitable ? 'var(--ok-fg)' : 'var(--bad-fg)',
                      }}
                    >
                      {formatMoney(item.grossMargin)} ({item.marginPercent}%)
                    </b>
                  </div>
                </div>

                <button
                  type="button"
                  className="ui-btn outline"
                  onClick={() => onOpenDishDetail(item.dish.id)}
                >
                  Chi tiết định lượng
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="note" style={{ marginTop: '16px', fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5 }}>
        Số phần bán được ghi nhận khi bạn quét Báo cáo xuất ở nút Quét. Ở bước kiểm tra, bạn có thể sửa số phần hoặc thêm dòng.
      </div>
    </div>
  );
};
