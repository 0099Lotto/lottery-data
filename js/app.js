/**
 * 星辰路引 - 網頁版主程式(第一階段:骨架 + 資料匯入)
 */

const state = {
  lottoType: 0,
  activeTab: 'data',
  selectedMode: null,
  byType: {
    0: null, 1: null, 2: null, 3: null, // 每個彩種各自存 { data, skipped, fileName, uploadedAt }
  },
  resultsByType: { 0: null, 1: null, 2: null, 3: null }, // 每個彩種各自存上次的分析結果
  isAnalyzing: false,
};

const el = (sel, root = document) => root.querySelector(sel);
const els = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function showToast(msg) {
  const toast = el('#toast');
  toast.textContent = msg;
  toast.classList.add('is-visible');
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toast.classList.remove('is-visible'), 2600);
}

function ballHtml(num, kind = 'normal') {
  return `<span class="ball ball--${kind}">${String(num).padStart(2, '0')}</span>`;
}

function currentEntry() {
  return state.byType[state.lottoType];
}

function updateStatusBar() {
  const cfg = getLottoConfig(state.lottoType);
  const entry = currentEntry();
  const bar = el('#statusBar');
  bar.textContent = entry
    ? `${cfg.name} · 已載入 ${entry.data.length} 筆資料`
    : `${cfg.name} · 尚未匯入資料`;
}

// ---------- 彩種切換 ----------
function setLottoType(id) {
  state.lottoType = id;
  els('.lotto-picker__btn').forEach(btn => {
    btn.classList.toggle('is-active', Number(btn.dataset.lotto) === id);
  });
  renderDataTab();
  renderSettingsTab();
  renderResultsTab();
  updateStatusBar();
}

// ---------- 分頁切換 ----------
function setTab(tab) {
  state.activeTab = tab;
  els('.tabs__btn').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.tab === tab);
  });
  els('.tab-content').forEach(section => {
    section.hidden = section.dataset.tabContent !== tab;
  });
}

// ---------- 資料分頁 ----------
function renderDataTab() {
  const cfg = getLottoConfig(state.lottoType);
  const entry = currentEntry();
  const container = el('#tab-data');

  if (!entry) {
    const numLabels = Array.from({ length: cfg.numCount }, (_, i) => `號碼${i + 1}`).join(', ');
    container.innerHTML = `
      <div class="upload-card">
        <p class="upload-card__title">尚未載入「${cfg.name}」的開獎資料</p>
        <p class="upload-card__hint">
          CSV 欄位順序:開獎日期, 期別, ${numLabels}${cfg.hasSpecial ? ', 特別號' : ''}。
          第一列表頭會自動略過;若檔案沒有表頭,請自行加一行再上傳。
        </p>
        <label class="upload-btn" for="fileInput">選擇 CSV 檔案</label>
        <input type="file" id="fileInput" accept=".csv,text/csv" hidden>
      </div>
    `;
    wireFileInput();
    return;
  }

  const rows = entry.data.slice().reverse(); // 畫面上新到舊
  const earliest = entry.data[0];
  const latest = entry.data[entry.data.length - 1];
  const next = nextDrawDate(state.lottoType, latest.date);

  container.innerHTML = `
    <div class="stat-row">
      <div class="stat"><span class="stat__value">${entry.data.length}</span><span class="stat__label">筆資料</span></div>
      <div class="stat"><span class="stat__value">${formatDate(earliest.date)}</span><span class="stat__label">最早一筆</span></div>
      <div class="stat"><span class="stat__value">${formatDate(latest.date)}</span><span class="stat__label">最新一筆</span></div>
      <div class="stat"><span class="stat__value">${formatDateWithWeekday(next)}</span><span class="stat__label">下一次開獎</span></div>
    </div>
    ${entry.skipped > 0 ? `<p class="upload-card__hint">已略過 ${entry.skipped} 筆格式不符的資料列。</p>` : ''}
    <div class="draw-table">
      ${rows.map(r => `
        <div class="draw-row">
          <span class="draw-row__date">${formatDateWithWeekday(r.date)}</span>
          <span class="draw-row__balls">
            ${r.numbers.map(n => ballHtml(n)).join('')}
            ${r.special != null ? ballHtml(r.special, 'special') : ''}
          </span>
        </div>
      `).join('')}
    </div>
    <label class="upload-btn upload-btn--ghost" for="fileInput">重新上傳 CSV</label>
    <input type="file" id="fileInput" accept=".csv,text/csv" hidden>
  `;
  wireFileInput();
}

function wireFileInput() {
  const input = el('#fileInput');
  if (!input) return;
  input.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) handleFile(file);
  });

  const card = el('.upload-card');
  if (!card) return;
  ['dragover', 'dragenter'].forEach(evt =>
    card.addEventListener(evt, (e) => { e.preventDefault(); card.classList.add('is-dragging'); })
  );
  ['dragleave', 'drop'].forEach(evt =>
    card.addEventListener(evt, (e) => { e.preventDefault(); card.classList.remove('is-dragging'); })
  );
  card.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
}

function handleFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const { data, skipped, total } = parseLottoCsv(String(reader.result), state.lottoType);
      if (total === 0) {
        showToast('沒有解析到有效資料列,請確認 CSV 欄位順序');
        return;
      }
      state.byType[state.lottoType] = { data, skipped, fileName: file.name, uploadedAt: new Date() };
      state.resultsByType[state.lottoType] = null; // 資料變了,舊的分析結果不再有意義
      renderDataTab();
      renderResultsTab();
      updateStatusBar();
      showToast(`已匯入 ${total} 筆資料`);
    } catch (err) {
      showToast('讀取失敗:' + err.message);
    }
  };
  reader.onerror = () => showToast('讀取檔案失敗');
  reader.readAsText(file, 'utf-8');
}

// ---------- 參數設定分頁 ----------
function renderSettingsTab() {
  const container = el('#tab-settings');
  const entry = currentEntry();

  container.innerHTML = `
    ${!entry ? `<p class="empty-note">尚未匯入開獎資料,你仍可以先選版路模式,匯入資料後就能開始比對。</p>` : ''}
    <p class="section-label">選擇分析版路</p>
    <div class="mode-grid">
      ${MODE_CONFIGS.map(m => `<button class="mode-btn" data-mode="${m.id}">${m.name}</button>`).join('')}
    </div>

    <p class="section-label">預測範圍(期數)</p>
    <div class="segmented" data-group="predRange">
      ${PRED_RANGE_OPTIONS.map((label, i) => `<button class="segmented__btn${i === 0 ? ' is-active' : ''}">${label}</button>`).join('')}
    </div>

    <p class="section-label">分析資料量</p>
    <div class="segmented" data-group="dataLimit">
      ${DATA_LIMIT_OPTIONS.map((label, i) => `<button class="segmented__btn${i === 2 ? ' is-active' : ''}">${label}</button>`).join('')}
    </div>

    <p class="section-label">截止日期(留空 = 用最新一筆資料當基準)</p>
    <input type="date" class="date-input" id="deadlineInput">

    <button class="run-btn" id="runAnalysisBtn" ${entry ? '' : 'disabled'}>
      ${state.selectedMode == null ? '先選一個版路模式' : '執行分析'}
    </button>
    <p class="run-status" id="runStatus"></p>
  `;

  els('.mode-btn', container).forEach(btn => {
    btn.classList.toggle('is-active', Number(btn.dataset.mode) === state.selectedMode);
    btn.addEventListener('click', () => {
      els('.mode-btn', container).forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      const mode = MODE_CONFIGS.find(m => String(m.id) === btn.dataset.mode);
      state.selectedMode = mode.id;
      const runBtn = el('#runAnalysisBtn', container);
      if (runBtn) runBtn.textContent = '執行分析';
    });
  });

  els('.segmented', container).forEach(group => {
    els('.segmented__btn', group).forEach(btn => {
      btn.addEventListener('click', () => {
        els('.segmented__btn', group).forEach(b => b.classList.remove('is-active'));
        btn.classList.add('is-active');
      });
    });
  });

  const runBtn = el('#runAnalysisBtn', container);
  if (runBtn) runBtn.addEventListener('click', runAnalysisFlow);
}

function getSegmentedIndex(groupName) {
  const group = el(`.segmented[data-group="${groupName}"]`);
  if (!group) return 0;
  const btns = els('.segmented__btn', group);
  const activeIdx = btns.findIndex(b => b.classList.contains('is-active'));
  return activeIdx >= 0 ? activeIdx : 0;
}

// ---------- 執行分析(呼叫 Pyodide 引擎) ----------
async function runAnalysisFlow() {
  const entry = currentEntry();
  if (!entry) { showToast('請先在「資料」分頁匯入開獎資料'); return; }
  if (state.selectedMode == null) { showToast('請先選一個版路模式'); return; }
  if (state.isAnalyzing) return;

  const deadlineInput = el('#deadlineInput');
  const latest = entry.data[entry.data.length - 1];
  const limitDateISO = (deadlineInput && deadlineInput.value) ? deadlineInput.value : latest.dateKey;

  const payload = {
    lottoType: state.lottoType,
    modeId: state.selectedMode,
    rows: entry.data.map(r => [r.dateKey, r.numbers, r.special]),
    predRangeIndex: getSegmentedIndex('predRange'),
    dataLimitIndex: getSegmentedIndex('dataLimit'),
    limitDateISO,
    excludeToday: false,
  };

  state.isAnalyzing = true;
  const runBtn = el('#runAnalysisBtn');
  const runStatus = el('#runStatus');
  if (runBtn) { runBtn.disabled = true; runBtn.textContent = '運算中…'; }

  try {
    const result = await runAnalysis(payload, (msg) => {
      if (runStatus) runStatus.textContent = msg;
    });
    if (!result.ok) {
      showToast('分析失敗:' + result.error);
      if (runStatus) runStatus.textContent = '上次執行失敗,可以再試一次。';
      return;
    }
    state.resultsByType[state.lottoType] = {
      modeId: state.selectedMode,
      modeName: (MODE_CONFIGS.find(m => m.id === state.selectedMode) || {}).name || '',
      ...result,
      ranAt: new Date(),
    };
    renderResultsTab();
    setTab('results');
    showToast(`分析完成,找到 ${result.totalTop} 條版路`);
  } catch (err) {
    showToast('發生錯誤:' + err.message);
    if (runStatus) runStatus.textContent = '發生錯誤:' + err.message;
  } finally {
    state.isAnalyzing = false;
    if (runBtn) { runBtn.disabled = false; runBtn.textContent = '執行分析'; }
  }
}

// ---------- 分析結果分頁 ----------
function renderResultsTab() {
  const container = el('#tab-results');
  const cfg = getLottoConfig(state.lottoType);
  const analysis = state.resultsByType[state.lottoType];

  if (!analysis) {
    container.innerHTML = `
      <p class="empty-note">
        分析結果會顯示在這裡。在「參數設定」選好版路模式、按下「執行分析」後,
        這裡會列出目前找得到的版路與最新預測號碼。
      </p>
    `;
    return;
  }

  const renderList = (list, title) => {
    if (!list || list.length === 0) return '';
    return `
      <p class="section-label">${title}(共 ${list.length} 條,顯示前 ${Math.min(list.length, 30)} 條)</p>
      <div class="result-list">
        ${list.map(r => `
          <div class="result-card">
            <pre class="result-card__text">${escapeHtml(r.text.trim())}</pre>
            ${r.predNums && r.predNums.length ? `
              <div class="result-card__balls">
                ${r.predNums.map(n => ballHtml(n)).join('')}
              </div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  };

  container.innerHTML = `
    <p class="section-label">${cfg.name} · ${analysis.modeName}</p>
    ${renderList(analysis.results, '目前版路(以最新截止日為準)')}
    ${renderList(analysis.nextResults, '下一期預告')}
    ${(!analysis.results || analysis.results.length === 0) ? '<p class="empty-note">這個模式在目前的設定與資料下沒有找到符合條件的版路,可以試試看調整資料量或截止日期。</p>' : ''}
  `;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ---------- 初始化 ----------
function init() {
  els('.lotto-picker__btn').forEach(btn => {
    btn.addEventListener('click', () => setLottoType(Number(btn.dataset.lotto)));
  });
  els('.tabs__btn').forEach(btn => {
    btn.addEventListener('click', () => setTab(btn.dataset.tab));
  });

  renderDataTab();
  renderSettingsTab();
  renderResultsTab();
  updateStatusBar();
}

document.addEventListener('DOMContentLoaded', init);
