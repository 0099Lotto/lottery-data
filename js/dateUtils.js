/**
 * 星辰路引 - 日期工具
 * 對應原始程式的 _parse_lotto_date_cached / _next_draw_date_cached。
 * 統一以 UTC 計算,只在意「哪一天」,避免時區造成日期偏移一天的問題。
 */

function parseLottoDate(dateStr) {
  const s = (dateStr || '').trim();
  if (!s) throw new Error('空白日期');

  const sep = s.includes('/') ? '/' : '-';
  const parts = s.split(sep).map(p => p.trim());
  if (parts.length !== 3) throw new Error('日期格式錯誤: ' + s);

  const [y, m, d] = parts.map(p => parseInt(p, 10));
  if (![y, m, d].every(Number.isFinite)) throw new Error('日期格式錯誤: ' + s);

  const dt = new Date(Date.UTC(y, m - 1, d));
  const valid = dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
  if (!valid) throw new Error('無效日期: ' + s);
  return dt;
}

function addDays(date, days) {
  const dt = new Date(date.getTime());
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt;
}

function dateKey(date) {
  return date.toISOString().slice(0, 10);
}

function formatDate(date) {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, '0');
  const d = String(date.getUTCDate()).padStart(2, '0');
  return `${y}/${m}/${d}`;
}

const WEEKDAY_LABELS_JS = ['日', '一', '二', '三', '四', '五', '六'];

function formatDateWithWeekday(date) {
  return `${formatDate(date)}(${WEEKDAY_LABELS_JS[date.getUTCDay()]})`;
}

// 對應 _next_draw_date_cached:回傳指定日期之後的下一個開獎日
function nextDrawDate(lottoType, fromDate) {
  const cfg = getLottoConfig(lottoType);
  const allowed = new Set(cfg.drawDaysJS);
  let dt = new Date(fromDate.getTime());
  do {
    dt = addDays(dt, 1);
  } while (!allowed.has(dt.getUTCDay()));
  return dt;
}
