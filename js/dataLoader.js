/**
 * 星辰路引 - CSV 開獎資料解析
 * 對應原始程式 load_lotto_data() 的解析與驗證規則(下載/本機快取的部分
 * 改成使用者手動上傳檔案,其餘規則盡量保持一致):
 *  - 略過表頭第一列
 *  - 「天天樂」(lottoType 1)沿用原本「日期 +1 天」的校正
 *  - 每列需有:日期, 期別, N 個號碼[, 特別號],號碼需在合法範圍內
 *  - 同一天重複資料只保留一筆,最後依日期由舊到新排序
 */

function splitCsvLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i++; }
        else inQuotes = false;
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      out.push(cur);
      cur = '';
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

function isDigitsOnly(s) {
  return /^[0-9]+$/.test(s);
}

/**
 * @param {string} text 原始 CSV 文字內容
 * @param {number} lottoType 彩種 id(0~3)
 * @returns {{data: Array, skipped: number, total: number}}
 */
function parseLottoCsv(text, lottoType) {
  const cfg = getLottoConfig(lottoType);
  const { numCount: n, maxNum, hasSpecial } = cfg;

  const lines = text.split(/\r\n|\r|\n/).filter(l => l.trim().length > 0);
  const rows = lines.slice(1); // 略過表頭

  const seen = new Set();
  const data = [];
  let skipped = 0;

  for (const line of rows) {
    const row = splitCsvLine(line);
    if (row.length < n + 2) { skipped++; continue; }

    try {
      let date = parseLottoDate(row[0]);
      if (lottoType === 1) date = addDays(date, 1);

      const key = dateKey(date);
      if (seen.has(key)) { skipped++; continue; }

      const nums = [];
      for (let i = 2; i < 2 + n; i++) {
        const x = (row[i] || '').trim();
        if (isDigitsOnly(x)) nums.push(parseInt(x, 10));
      }
      if (nums.length !== n || !nums.every(v => v >= 1 && v <= maxNum)) {
        skipped++; continue;
      }
      nums.sort((a, b) => a - b);

      let special = null;
      if (hasSpecial && row.length > n + 2) {
        const sp = (row[n + 2] || '').trim();
        if (isDigitsOnly(sp)) {
          const val = parseInt(sp, 10);
          if (val >= 1 && val <= maxNum) special = val;
        }
      }

      data.push({ date, dateKey: key, numbers: nums, special });
      seen.add(key);
    } catch (e) {
      skipped++;
    }
  }

  data.sort((a, b) => a.date - b.date);
  return { data, skipped, total: data.length };
}
