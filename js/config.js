/**
 * 星辰路引 - 全域設定與常數
 * 對應原始 Pythonista App 中的彩種參數與版路模式清單。
 */

// 四種彩種設定:號碼數 / 號碼上限 / 是否有特別號 / 開獎星期
// drawDaysJS 採 JS 慣例:週日=0, 週一=1 ... 週六=6
const LOTTO_TYPES = [
  { id: 0, name: '台灣539', numCount: 5, maxNum: 39, hasSpecial: false, drawDaysJS: [1, 2, 3, 4, 5, 6] },
  { id: 1, name: '天天樂',   numCount: 5, maxNum: 39, hasSpecial: false, drawDaysJS: [0, 1, 2, 3, 4, 5, 6] },
  { id: 2, name: '大樂透',   numCount: 6, maxNum: 49, hasSpecial: true,  drawDaysJS: [2, 5] },
  { id: 3, name: '六合彩',   numCount: 6, maxNum: 49, hasSpecial: true,  drawDaysJS: [2, 4, 6] },
];

function getLottoConfig(id) {
  return LOTTO_TYPES.find(t => t.id === id) || LOTTO_TYPES[0];
}

// 對應原本「參數設定」畫面的版路模式清單。
// 第二階段更新:15個模式中,14個已經接上第二階段的真實運算引擎(見 py/lotto_engine.py,
// 直接沿用原始 App 的 Python 分析邏輯,透過 Pyodide 在瀏覽器內執行,不是重新用 JS 手刻)。
// 「幾連拖」原本是開子選單選 2/3/4連拖,這裡直接展開成三顆按鈕。
// 「整體版路圖」(mode 99,彙整多種模式的整體視圖)排在第三/四階段,先不放進來。
const MODE_CONFIGS = [
  { id: 0,  name: '定位合數加減' },
  { id: 7,  name: '週牌合數加減' },
  { id: 18, name: '號碼相互加減' },
  { id: 12, name: '同期雙邊' },
  { id: 1,  name: '熱門拖牌' },
  { id: 5,  name: '雙碼拖牌' },
  { id: 8,  name: '定點定位拖牌' },
  { id: 2,  name: '2連拖' },
  { id: 3,  name: '3連拖' },
  { id: 4,  name: '4連拖' },
  { id: 13, name: '圖形版路' },
  { id: 9,  name: '立柱熱門' },
  { id: 10, name: '每月週牌' },
  { id: 11, name: 'N次週牌' },
  { id: 15, name: '星期加減合數' },
  { id: 16, name: '日期版路' },
];

const PRED_RANGE_OPTIONS = ['1期', '2期', '3期', '2期到期', '3期到期'];
const DATA_LIMIT_OPTIONS = ['20筆', '51筆', '231筆', '全部'];
