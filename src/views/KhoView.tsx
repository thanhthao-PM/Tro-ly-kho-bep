import React, { useState, useMemo } from 'react';
import {
  simulationStore,
  formatQty,
  STORAGE_LOCATIONS,
  KhoProductGroup,
} from '../services/mock/simulationStore';
import { Icon } from '../components/common/Icon';
import { StatusTag } from '../components/common/StatusTag';

interface KhoViewProps {
  onNavigateToAI: () => void;
  onOpenEdit: () => void;
  onOpenDetail: (productName: string) => void;
}

export const KhoView: React.FC<KhoViewProps> = ({
  onNavigateToAI,
  onOpenEdit,
  onOpenDetail,
}) => {
  const [search, setSearch] = useState('');
  const [dateFilter, setDateFilter] = useState('all');
  const [sortBy, setSortBy] = useState('exp');
  const [locationFilter, setLocationFilter] = useState('all');

  const importDates = useMemo(() => simulationStore.getImportDates(), []);
  const expiring = useMemo(() => simulationStore.getExpiringSummary(), []);
  const products = useMemo(
    () => simulationStore.getKhoProducts(search, dateFilter, sortBy, locationFilter),
    [search, dateFilter, sortBy, locationFilter]
  );
  const allProducts = useMemo(() => simulationStore.getKhoProducts(), []);

  // Format header date
  const now = new Date();
  const dayNames = ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
  const dayString = `${dayNames[now.getDay()]}, ${now.getDate()}/${now.getMonth() + 1}`;

  const locationCounts = useMemo(() => {
    const counts = { all: allProducts.length, fridge: 0, pantry: 0, freezer: 0 };
    allProducts.forEach((p) => {
      if (p.location === 'FRIDGE') counts.fridge++;
      else if (p.location === 'FREEZER') counts.freezer++;
      else counts.pantry++;
    });
    return counts;
  }, [allProducts]);

  return (
    <div>
      {/* Header */}
      <div className="view-hd">
        <small>{dayString}</small>
        <h1>Kho bếp của tôi</h1>
      </div>

      {/* Hero Card */}
      {expiring.soon + expiring.expired > 0 ? (
        <div className="hero-card">
          <b>
            {expiring.soon > 0
              ? `${expiring.soon} đợt sắp hết hạn`
              : `${expiring.expired} đợt đã hết hạn`}
          </b>
          <span>
            {expiring.soon > 0
              ? `Xử lí trong 2 ngày tới để không bị lãng phí.${expiring.expired > 0 ? ` Có ${expiring.expired} đợt đã hết hạn cần bỏ.` : ''}`
              : 'Hãy kiểm tra và bỏ những đợt đã hỏng.'}
          </span>
          <button
            type="button"
            className="ui-btn light"
            onClick={onNavigateToAI}
          >
            <span>Xem cách xử lí từ AI</span>
            <Icon name="arrow" size={18} />
          </button>
        </div>
      ) : (
        <div className="hero-card">
          <b>Kho đang ổn</b>
          <span>Không có đợt nào sắp hết hạn trong 2 ngày tới.</span>
        </div>
      )}

      {/* Search Input */}
      <div style={{ marginTop: '14px' }}>
        <input
          type="search"
          className="ui-input"
          placeholder="Tìm món trong kho"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Tìm món trong kho"
          autoComplete="off"
        />
      </div>

      {/* Date & Sort Dropdowns */}
      <div className="grid-2" style={{ marginTop: '8px' }}>
        <select
          className="ui-input"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          aria-label="Lọc theo ngày hoặc đợt nhập"
        >
          <option value="all">Tất cả đợt nhập</option>
          <option value="today">Hôm nay</option>
          <option value="7">7 ngày gần đây</option>
          {importDates.map((date) => (
            <option key={date} value={date}>
              Đợt nhập {date.split('-').reverse().slice(0, 2).join('/')}
            </option>
          ))}
        </select>

        <select
          className="ui-input"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          aria-label="Sắp xếp danh sách kho"
        >
          <option value="exp">Hạn dùng gần nhất</option>
          <option value="imp">Nhập gần đây nhất</option>
          <option value="name">Tên A–Z</option>
        </select>
      </div>

      {/* Location Chips */}
      <div className="chips-bar">
        {[
          { key: 'all', label: `Tất cả · ${locationCounts.all}` },
          { key: 'fridge', label: `Tủ lạnh · ${locationCounts.fridge}` },
          { key: 'pantry', label: `Tủ bếp · ${locationCounts.pantry}` },
          { key: 'freezer', label: `Ngăn đông · ${locationCounts.freezer}` },
        ].map((item) => (
          <button
            key={item.key}
            type="button"
            className={`filter-chip ${locationFilter === item.key ? 'active' : ''}`}
            onClick={() => setLocationFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Product List */}
      <div style={{ marginTop: '12px' }}>
        {products.length === 0 ? (
          <div style={{ marginTop: '28px', textAlign: 'center', color: 'var(--muted)', lineHeight: 1.5 }}>
            Không tìm thấy món nào khớp bộ lọc. Thử đổi từ khóa hoặc chọn "Tất cả đợt nhập".
          </div>
        ) : (
          <div className="list-grid">
            {products.map((p) => {
              const multi = p.batches.length > 1;
              const avatarClass =
                p.tone === 'ok'
                  ? 'tag-ok'
                  : p.tone === 'warn'
                  ? 'tag-warn'
                  : 'tag-bad';

              return (
                <button
                  key={p.name}
                  type="button"
                  className="product-row"
                  onClick={() => onOpenDetail(p.name)}
                  aria-label={`Xem chi tiết ${p.name}`}
                >
                  <div
                    className={`avatar-badge ${avatarClass}`}
                    style={{ color: p.tone === 'ok' ? 'var(--ok-fg)' : p.tone === 'warn' ? 'var(--warn-fg)' : 'var(--bad-fg)' }}
                  >
                    {p.name.charAt(0).toUpperCase()}
                  </div>

                  <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
                    <span className="product-name">
                      {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
                    </span>
                    <span className="product-sub">
                      {formatQty(p.totalQty)} {p.unit} · {STORAGE_LOCATIONS[p.location]}
                      {multi ? ` · ${p.batches.length} đợt nhập` : ''}
                    </span>
                  </div>

                  <StatusTag tone={p.tone}>{p.statusLabel}</StatusTag>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="fab-space" />

      {/* Floating Action Button */}
      <button
        type="button"
        className="fab-btn"
        onClick={onOpenEdit}
        aria-label="Chỉnh sửa kho hàng"
      >
        <Icon name="pen" size={20} />
        <span>Chỉnh sửa</span>
      </button>
    </div>
  );
};
