/**
 * 星辰路引 - Pyodide 橋接層
 *
 * 為什麼用 Pyodide,而不是把分析邏輯重新用 JS 手刻一遍:
 * 原始 execute_analysis_for_date 單一函式就近 5900 行,15 種模式的巢狀迴圈
 * 彼此共用、糾纏在一起,手動翻譯成另一種語言很容易在某個模式悄悄算錯而不
 * 自知。Pyodide 讓瀏覽器直接執行「幾乎原封不動」的原始 Python 邏輯(只拿掉
 * ui / photos / console 等 iOS 專屬套件),正確性風險低很多。
 *
 * 代價:第一次使用時需要下載 Pyodide 執行環境(數MB),之後瀏覽器會快取。
 */

const PYODIDE_CDN = 'https://cdn.jsdelivr.net/pyodide/v314.0.6/full/';

let pyodideReadyPromise = null;

function loadPyodideScriptOnce() {
  if (window.loadPyodide) return Promise.resolve();
  if (loadPyodideScriptOnce._p) return loadPyodideScriptOnce._p;
  loadPyodideScriptOnce._p = new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = PYODIDE_CDN + 'pyodide.js';
    s.onload = resolve;
    s.onerror = () => reject(new Error('Pyodide 主程式載入失敗,請檢查網路連線'));
    document.head.appendChild(s);
  });
  return loadPyodideScriptOnce._p;
}

async function getPyodideReady(onStatus) {
  if (!pyodideReadyPromise) {
    pyodideReadyPromise = (async () => {
      onStatus && onStatus('載入 Python 執行環境(第一次會慢一點)…');
      await loadPyodideScriptOnce();
      const pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

      onStatus && onStatus('載入版路分析引擎…');
      const resp = await fetch('py/lotto_engine.py');
      if (!resp.ok) {
        throw new Error('無法載入 py/lotto_engine.py(HTTP ' + resp.status + ')');
      }
      const code = await resp.text();
      await pyodide.runPythonAsync(code);
      return pyodide;
    })().catch(err => {
      pyodideReadyPromise = null; // 失敗時重置,讓使用者可以重試
      throw err;
    });
  }
  return pyodideReadyPromise;
}

/**
 * @param {object} payload
 *   lottoType, modeId, rows:[[dateISO,[nums],special|null]...],
 *   predRangeIndex, dataLimitIndex, limitDateISO, excludeToday, modeSettings
 * @param {(msg:string)=>void} [onStatus] 進度訊息callback
 * @returns {Promise<object>} { ok, results:[{text,predNums,streak}], nextResults, totalTop, totalNext } 或 { ok:false, error }
 */
async function runAnalysis(payload, onStatus) {
  const pyodide = await getPyodideReady(onStatus);
  onStatus && onStatus('計算中…');
  pyodide.globals.set('_payload_json', JSON.stringify(payload));
  const outJson = await pyodide.runPythonAsync('run_analysis_json(_payload_json)');
  return JSON.parse(outJson);
}
