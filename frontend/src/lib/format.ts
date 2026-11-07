export const vnd = (n: number | null | undefined) =>
  n === null || n === undefined ? "—" : `${Math.round(n).toLocaleString("vi-VN")} đ`;
export const dmy = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
};
export const num = (s: string | number) => Number(s).toLocaleString("vi-VN", { maximumFractionDigits: 3 });
export const today = () => new Date(Date.now() + 7 * 3600 * 1000).toISOString().slice(0, 10);
export const addDays = (iso: string, n: number) => {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};
export const STATUS_LABEL: Record<string, string> = {
  EXPIRED: "Đã hết hạn", EXPIRES_SOON: "Sắp hết hạn", OK: "Còn hạn", NO_EXPIRY: "Không hạn",
};
export const tone = (s: string) => (s === "EXPIRED" ? "bad" : s === "EXPIRES_SOON" ? "warn" : "ok");
