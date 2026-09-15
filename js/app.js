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
  smartByType: { 0: null, 1: null, 2: null, 3: null },
  modeSettings: { 0: {}, 1: {}, 2: {}, 3: {} },
  activeModeSettings: {},
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
  renderSmartTab();
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
      state.smartByType[state.lottoType] = null;
      renderDataTab();
      renderResultsTab();
      renderSmartTab();
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
const MODE_SETTING_SCHEMA = {
  common: ['selectCount','minStreak','minHits','cyclic','consec','tail','sum','fixedPos','alternate','alternateVip','staircase','stepAdvance','nonHit'],
  special: {
    7: ['intervalStep','weeklyMode'],
    12: ['pairMode','intervalStep'],
    18: ['intervalStep','weeklyMode'],
    9: ['pillarCounts'],
    10:['pillarCounts','weekdays','nPeriod'],
    11:['selectCount','minStreak','minHits'],
    13:['shapeIndex'],
    16:['pillarCounts','dateRoutePeriods'],
  }
};

function getCurrentModeSettings() {
  const id = state.selectedMode;
  const saved = (state.modeSettings[state.lottoType] && state.modeSettings[state.lottoType][id]) || {};
  return {
    selectCount: saved.selectCount ?? (id === 11 ? 6 : 2),
    minStreak: saved.minStreak ?? 7,
    minHits: Array.isArray(saved.minHits) ? saved.minHits : [1],
    cyclic: !!saved.cyclic, consec: !!saved.consec, tail: !!saved.tail, sum: !!saved.sum,
    fixedPos: saved.fixedPos !== false, alternate: !!saved.alternate, alternateVip: !!saved.alternateVip,
    staircase: !!saved.staircase, stepAdvance: !!saved.stepAdvance, nonHit: !!saved.nonHit,
    intervalStep: saved.intervalStep ?? 1,
    weeklyMode: saved.weeklyMode ?? 0,
    pairMode: saved.pairMode ?? 1,
    pillarCounts: Array.isArray(saved.pillarCounts) ? saved.pillarCounts : [3,3,3,0,0],
    weekdays: Array.isArray(saved.weekdays) ? saved.weekdays : [],
    nPeriod: saved.nPeriod ?? false,
    shapeIndex: saved.shapeIndex ?? 0,
    dateRoutePeriods: Array.isArray(saved.dateRoutePeriods) ? saved.dateRoutePeriods : ['0','0','0','0'],
  };
}

function renderModeSpecificSettings(container) {
  const mode = state.selectedMode;
  if (mode == null) return;
  const s = getCurrentModeSettings();
  const special = (MODE_SETTING_SCHEMA.special[mode] || []);
  const toggle = (key,label,checked) => `<label class="setting-switch"><input type="checkbox" data-k="${key}" ${checked?'checked':''}><span>${label}</span></label>`;
  const starBtns = [1,2,3,4].map(n => `<button type="button" class="mini-choice ${s.minHits.includes(n)?'is-active':''}" data-star="${n}">${n}星</button>`).join('');
  const weekBtns = ['一','二','三','四','五','六','日'].map((x,i)=>`<button type="button" class="mini-choice ${s.weekdays.includes(i)?'is-active':''}" data-week="${i}">${x}</button>`).join('');
  let html = `<div class="mode-settings-card" id="modeSettingsCard">
    <div class="mode-settings-card__title">${MODE_CONFIGS.find(m=>m.id===mode)?.name||''} 專屬參數設定</div>
    <div class="setting-grid">
      <label>選號數量<input type="number" min="1" max="10" id="setSelectCount" value="${s.selectCount}"></label>
      <label>連續命中過濾<input type="number" min="0" max="100" id="setMinStreak" value="${s.minStreak}"></label>
    </div>
    <div class="setting-block"><div class="setting-label">目標開出最少命中星數</div><div class="mini-choice-row" id="setStars">${starBtns}</div></div>
    <div class="setting-block"><div class="setting-label">常用條件</div><div class="setting-switches">
      ${toggle('cyclic','循環',s.cyclic)}${toggle('consec','連續',s.consec)}${toggle('tail','尾數',s.tail)}${toggle('sum','合數',s.sum)}
      ${toggle('fixedPos','固定位置',s.fixedPos)}${toggle('alternate','輪流',s.alternate)}${toggle('alternateVip','嚴格輪流',s.alternateVip)}${toggle('staircase','階梯',s.staircase)}${toggle('stepAdvance','階梯提前',s.stepAdvance)}${toggle('nonHit','不出號碼模式',s.nonHit)}
    </div></div>`;
  if (special.includes('intervalStep')) html += `<label class="setting-line">間隔期數<input type="number" min="1" max="20" id="setInterval" value="${s.intervalStep}"></label>`;
  if (special.includes('pairMode')) html += `<div class="setting-block"><div class="setting-label">同期雙邊類型</div><div class="mini-choice-row" id="setPair"><button type="button" class="mini-choice ${s.pairMode===0?'is-active':''}" data-pair="0">左右各1號</button><button type="button" class="mini-choice ${s.pairMode===1?'is-active':''}" data-pair="1">左右各2號</button><button type="button" class="mini-choice ${s.pairMode===2?'is-active':''}" data-pair="2">同棟2號</button></div></div>`;
  if (special.includes('weeklyMode')) html += `<div class="setting-block"><div class="setting-label">週牌模式</div><select id="setWeeklyMode"><option value="0" ${s.weeklyMode===0?'selected':''}>一般</option><option value="1" ${s.weeklyMode===1?'selected':''}>粉紅→藍</option><option value="2" ${s.weeklyMode===2?'selected':''}>藍→粉紅</option></select></div>`;
  if (special.includes('pillarCounts')) html += `<div class="setting-block"><div class="setting-label">各柱號碼數量</div><div class="pillar-row">${s.pillarCounts.map((v,i)=>`<input type="number" min="0" max="20" data-pillar="${i}" value="${v}" placeholder="柱${i+1}">`).join('')}</div></div>`;
  if (special.includes('weekdays')) html += `<div class="setting-block"><div class="setting-label">星期篩選</div><div class="mini-choice-row" id="setWeekdays">${weekBtns}</div></div>`;
  if (special.includes('nPeriod')) html += `${toggle('nPeriod','3期中一次',s.nPeriod)}`;
  if (special.includes('shapeIndex')) html += `<div class="setting-block"><div class="setting-label">圖形</div><select id="setShape"><option value="0" ${s.shapeIndex===0?'selected':''}>菱形</option><option value="1" ${s.shapeIndex===1?'selected':''}>星辰圖</option><option value="2" ${s.shapeIndex===2?'selected':''}>倒三角</option><option value="3" ${s.shapeIndex===3?'selected':''}>三角形</option><option value="4" ${s.shapeIndex===4?'selected':''}>圓形</option><option value="5" ${s.shapeIndex===5?'selected':''}>六芒星</option><option value="6" ${s.shapeIndex===6?'selected':''}>全部圖形</option></select></div>`;
  if (special.includes('dateRoutePeriods')) html += `<div class="setting-block"><div class="setting-label">指定第幾期（0=不使用）</div><div class="pillar-row">${s.dateRoutePeriods.map((v,i)=>`<input type="text" data-period="${i}" value="${v}">`).join('')}</div></div>`;
  html += `<button type="button" class="setting-done-btn" id="modeSettingsDone">設定完成</button></div>`;
  container.innerHTML = html;

  els('[data-star]',container).forEach(b=>b.addEventListener('click',()=>b.classList.toggle('is-active')));
  els('[data-pair]',container).forEach(b=>b.addEventListener('click',()=>{els('[data-pair]',container).forEach(x=>x.classList.remove('is-active'));b.classList.add('is-active')}));
  els('[data-week]',container).forEach(b=>b.addEventListener('click',()=>b.classList.toggle('is-active')));
  const done=el('#modeSettingsDone',container);
  done.addEventListener('click',()=>{
    const getBool=k=>!!el(`[data-k="${k}"]`,container)?.checked;
    const minHits=els('[data-star].is-active',container).map(x=>Number(x.dataset.star));
    const saved={
      selectCount:Number(el('#setSelectCount',container)?.value||2), minStreak:Number(el('#setMinStreak',container)?.value||0), minHits:minHits.length?minHits:[1],
      cyclic:getBool('cyclic'),consec:getBool('consec'),tail:getBool('tail'),sum:getBool('sum'),fixedPos:getBool('fixedPos'),alternate:getBool('alternate'),alternateVip:getBool('alternateVip'),staircase:getBool('staircase'),stepAdvance:getBool('stepAdvance'),nonHit:getBool('nonHit'),
      intervalStep:Number(el('#setInterval',container)?.value||1), pairMode:Number(el('[data-pair].is-active',container)?.dataset.pair||1), weeklyMode:Number(el('#setWeeklyMode',container)?.value||0),
      pillarCounts:els('[data-pillar]',container).map(x=>Number(x.value||0)), weekdays:els('[data-week].is-active',container).map(x=>Number(x.dataset.week)), nPeriod:getBool('nPeriod'), shapeIndex:Number(el('#setShape',container)?.value||0), dateRoutePeriods:els('[data-period]',container).map(x=>x.value||'0')
    };
    if(!state.modeSettings[state.lottoType]) state.modeSettings[state.lottoType]={};
    state.modeSettings[state.lottoType][mode]=saved;
    showToast('版路專屬參數已保存');
  });
}

function renderSettingsTab() {
  const container = el('#tab-settings');
  const entry = currentEntry();
  container.innerHTML = `
    ${!entry ? `<p class="empty-note">尚未匯入開獎資料,你仍可以先選版路模式；匯入資料後就能開始比對。</p>` : ''}
    <p class="section-label">選擇分析版路 <span class="setting-hint">（點擊後設定專用參數）</span></p>
    <div class="mode-grid">
      ${MODE_CONFIGS.map(m => `<button class="mode-btn" data-mode="${m.id}">${m.name}</button>`).join('')}
    </div>
    <div id="modeSettingsHost"></div>
    <p class="section-label">預測範圍(期數)</p>
    <div class="segmented" data-group="predRange">${PRED_RANGE_OPTIONS.map((label, i) => `<button class="segmented__btn${i === 0 ? ' is-active' : ''}">${label}</button>`).join('')}</div>
    <p class="section-label">分析資料量</p>
    <div class="segmented" data-group="dataLimit">${DATA_LIMIT_OPTIONS.map((label, i) => `<button class="segmented__btn${i === 2 ? ' is-active' : ''}">${label}</button>`).join('')}</div>
    <p class="section-label">截止日期（留空 = 最新一筆資料）</p>
    <input type="date" class="date-input" id="deadlineInput">
    <button class="run-btn" id="runAnalysisBtn" ${entry && state.selectedMode != null ? '' : 'disabled'}>${state.selectedMode == null ? '先選一個版路模式' : '執行分析'}</button>
    <p class="run-status" id="runStatus"></p>
  `;
  const host=el('#modeSettingsHost',container);
  els('.mode-btn',container).forEach(btn=>{
    btn.classList.toggle('is-active', Number(btn.dataset.mode) === state.selectedMode);
    btn.addEventListener('click',()=>{
      els('.mode-btn',container).forEach(b=>b.classList.remove('is-active')); btn.classList.add('is-active');
      state.selectedMode=Number(btn.dataset.mode);
      renderModeSpecificSettings(host);
      const runBtn=el('#runAnalysisBtn',container); if(runBtn) { runBtn.disabled=!entry; runBtn.textContent='執行分析'; }
    });
  });
  els('.segmented',container).forEach(group=>els('.segmented__btn',group).forEach(btn=>btn.addEventListener('click',()=>{els('.segmented__btn',group).forEach(b=>b.classList.remove('is-active'));btn.classList.add('is-active');})));
  const runBtn=el('#runAnalysisBtn',container); if(runBtn) runBtn.addEventListener('click',runAnalysisFlow);
  if(state.selectedMode!=null) renderModeSpecificSettings(host);
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
    smartEnabled: true,
    smartLookback: 5,
    smartTargetCount: 5,
    modeSettings: (() => {
      const s = (state.modeSettings[state.lottoType] && state.modeSettings[state.lottoType][state.selectedMode]) || {};
      return {
        select_count: String(s.selectCount ?? 2), min_streak: String(s.minStreak ?? 7), min_hit_list: s.minHits || [1],
        is_cyclic: !!s.cyclic, is_consec: !!s.consec, is_tail: !!s.tail, is_sum: !!s.sum, is_fixed_pos: s.fixedPos !== false,
        is_alternate: !!s.alternate, is_alternate_vip: !!s.alternateVip, is_staircase: !!s.staircase, is_step_advance: !!s.stepAdvance,
        is_non_hit: !!s.nonHit, interval_step: Number(s.intervalStep || 1), same_period_pair_mode: Number(s.pairMode ?? 1),
        is_weekly_n_add_sub: Number(s.weeklyMode || 0) > 0, weekly_blue_pos: 0, pillar_counts: s.pillarCounts || [3,3,3,0,0],
        weekdays: s.weekdays || [], n_period_enable: !!s.nPeriod, shape_index: Number(s.shapeIndex || 0), date_route_periods: s.dateRoutePeriods || ['0','0','0','0']
      };
    })(),
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
    state.smartByType[state.lottoType] = result.smart || null;
    renderResultsTab();
    renderSmartTab();
    setTab('results');
    const smartCount = result.smart && result.smart.recommendations ? result.smart.recommendations.length : 0;
    showToast(`分析完成 · ${result.totalTop} 條版路 · 智能彩引嚴選 ${smartCount} 條`);
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


function smartBallHtml(nums, kind = 'normal') {
  return (nums || []).map(n => ballHtml(n, kind)).join('');
}

function renderSmartTab() {
  const container = el('#tab-smart');
  if (!container) return;
  const cfg = getLottoConfig(state.lottoType);
  const analysis = state.resultsByType[state.lottoType];
  const smart = state.smartByType[state.lottoType];

  if (!analysis || !smart) {
    container.innerHTML = `
      <div class="smart-hero">
        <div class="smart-hero__icon">✦</div>
        <div><div class="smart-hero__title">智能彩引</div>
        <div class="smart-hero__sub">先執行版路分析，系統會自動以歷史回測評分並嚴選下期推薦。</div></div>
      </div>
      <p class="empty-note">智能彩引會依目前選擇的版路，回測最近 5 個分析基準期，計算命中率、平均週期、連漏穩定度與反彈壓力，再產生最多 5 組下期推薦。</p>
    `;
    return;
  }

  if (smart.ok === false) {
    container.innerHTML = `<p class="empty-note">智能彩引運算失敗：${escapeHtml(smart.error || '未知錯誤')}</p>`;
    return;
  }

  const recs = smart.recommendations || [];
  const verMap = new Map((smart.verification || []).map(v => [v.routeIndex, v]));
  const verifyBadge = (routeIndex) => {
    const v = verMap.get(routeIndex);
    if (!v) return '<span class="smart-badge">待驗證</span>';
    if (v.status === 'hit') return `<span class="smart-badge smart-badge--hit">🎉 命中${v.hitNums && v.hitNums.length ? ' ' + v.hitNums.map(n => String(n).padStart(2,'0')).join(' ') : ''}</span>`;
    if (v.status === 'pending') return '<span class="smart-badge smart-badge--pending">⏳ 尚未開獎</span>';
    return '<span class="smart-badge smart-badge--miss">💔 未命中</span>';
  };

  const recHtml = recs.length ? recs.map((r, idx) => `
    <article class="smart-card">
      <div class="smart-card__top">
        <div class="smart-rank">${idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : '🎖️'} 第${idx + 1}選</div>
        <div class="smart-score">${r.score.toFixed(1)} 分</div>
      </div>
      <div class="smart-card__nums">${smartBallHtml(r.predNums, r.isNonHit ? 'normal' : 'normal')}</div>
      <div class="smart-card__meta">原第 ${r.routeIndex} 條 · 命中率 ${r.hitRatePct.toFixed(1)}% · 平均 ${r.avgInterval.toFixed(1)} 期開 1 次</div>
      <div class="smart-card__meta">目前連漏 ${r.currentMiss} 期 · 歷史最多 ${r.maxMiss} 期</div>
      <div class="smart-card__reason">${escapeHtml(r.reason)}</div>
      <div class="smart-card__verify">${verifyBadge(r.routeIndex)}</div>
    </article>
  `).join('') : '<p class="empty-note">目前回測樣本不足，尚無法形成智能推薦。</p>';

  container.innerHTML = `
    <div class="smart-hero">
      <div class="smart-hero__icon">✦</div>
      <div><div class="smart-hero__title">智能彩引</div>
      <div class="smart-hero__sub">${cfg.name} · ${analysis.modeName} · 歷史回測 ${smart.lookback} 期</div></div>
    </div>
    <div class="smart-summary">
      <div class="smart-summary__item"><span>${recs.length}</span><small>嚴選推薦</small></div>
      <div class="smart-summary__item"><span>${(smart.champions || []).length}</span><small>冠軍候選</small></div>
      <div class="smart-summary__item"><span>${(smart.nextDraws || []).length}</span><small>可驗證期數</small></div>
    </div>
    <p class="section-label">🎯 AI 智能下期嚴選推薦</p>
    <div class="smart-list">${recHtml}</div>
    <p class="section-label">🏆 冠軍分析（沿用目前版路順序）</p>
    <div class="result-list">
      ${(smart.champions || []).map((r, i) => `<div class="result-card result-card--compact"><div><strong>第 ${i+1} 條</strong> · 原第 ${r.routeIndex} 條 · ${r.score.toFixed(1)} 分</div><div class="result-card__balls">${smartBallHtml(r.predNums)}</div><div class="smart-card__meta">命中率 ${r.hitRatePct.toFixed(1)}% · 目前連漏 ${r.currentMiss} 期</div></div>`).join('') || '<p class="empty-note">尚無冠軍候選。</p>'}
    </div>
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
  renderSmartTab();
  updateStatusBar();
}

document.addEventListener('DOMContentLoaded', init);
