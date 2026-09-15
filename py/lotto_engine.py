import csv
import random
from datetime import datetime, timedelta
from bisect import bisect_left, bisect_right
from functools import lru_cache
from collections import Counter
import os
import time
import math
from itertools import product, combinations, islice

UI_TOP_SPACING = 15
UI_TAB_HEIGHT = 50
UI_MODE_BTN_HEIGHT = 50

UI_FONT_SIZE_NORMAL = 14
UI_FONT_SIZE_NOTE = 14
UI_FONT_SIZE_TITLE = 18
UI_FONT_SIZE_LABEL = 15
UI_PADDING_X = 20
UI_ITEM_SPACING = 40
DATA_READ_LIMIT = 231
ANALYSIS_DATA_LIMIT_OPTIONS = {
    0: 20,
    1: 51,
    2: DATA_READ_LIMIT,
    3: None,
}
CHART_ROWS = 60
CHART_COLS = 4
CHART_DISPLAY_LIMIT = 231
TOTAL_CELLS = CHART_ROWS * CHART_COLS

CHART_NUM_FONT_SIZE = 27
CHART_TITLE_FONT_SIZE = 28
CHART_FOOTER_TEXT_FONT_SIZE = 25
CHART_MONTH_FONT_SIZE = 28
CHART_DAY_FONT_SIZE = 25
CHART_WEEKDAY_FONT_SIZE = 25

MODE12_CENTER_RED_FONT_SIZE = 12
MODE12_CENTER_GREEN_FONT_SIZE = 10
MODE12_GREEN_TAG_FONT_SIZE = 14
MODE12_GREEN_TAG_WIDTH = 24
MODE12_GREEN_TAG_HEIGHT = 16
MODE12_GREEN_TAG_X_OFFSET = 12
MODE12_GREEN_TAG_Y_OFFSET = 10
CHART_OUTER_MARGIN = 2
CHART_BLACK_BORDER_WIDTH = 3

CHART_DRAW_STYLE = {
    'arrow_path_width': 3,
    'circle_border_width': 1,
    'm12_arrow_path_width': 3,
    'chart_border_width': 3,
    'arrow_head_len': 14,
    'arrow_head_angle': 0.6,
    'arrow_end_offset': 0,
    'm12_arrow_end_offset': 15,
}

CHART_ARROW_PATH_WIDTH = CHART_DRAW_STYLE['arrow_path_width']
CHART_CIRCLE_BORDER_WIDTH = CHART_DRAW_STYLE['circle_border_width']
CHART_M12_ARROW_PATH_WIDTH = CHART_DRAW_STYLE['m12_arrow_path_width']
CHART_BORDER_WIDTH = CHART_DRAW_STYLE['chart_border_width']
CHART_ARROW_HEAD_LEN = CHART_DRAW_STYLE['arrow_head_len']
CHART_ARROW_HEAD_ANGLE = CHART_DRAW_STYLE['arrow_head_angle']
CHART_ARROW_END_OFFSET = CHART_DRAW_STYLE['arrow_end_offset']
CHART_M12_ARROW_END_OFFSET = CHART_DRAW_STYLE['m12_arrow_end_offset']

# 命中圖表表頭名稱:依序對應第1組、第2組...想改名字直接改這裡的文字即可。
# 沒填名字或組數超出這個清單長度時,會自動退回顯示「第X組」。
HIT_CHART_GROUP_NAMES = ['第1組', '第2組', '第3組', '第4組', '第5組']

@lru_cache(maxsize=4096)
def _parse_lotto_date_cached(date_str):
    s = (date_str or '').strip()
    if not s:
        raise ValueError('empty date')
    try:
        if '/' in s:
            y, m, d = s.split('/')
        else:
            y, m, d = s.split('-')
        return datetime(int(y), int(m), int(d)).date()
    except Exception:
        if '/' in s:
            return datetime.strptime(s, '%Y/%m/%d').date()
        return datetime.strptime(s, '%Y-%m-%d').date()

@lru_cache(maxsize=256)
def _next_draw_date_cached(lotto_type, year, month, day):
    draw_days = {0:(0, 1, 2, 3, 4, 5), 1:(0, 1, 2, 3, 4, 5, 6), 2:(1, 4), 3:(1, 3, 5)}
    dt = datetime(year, month, day)
    allowed = set(draw_days.get(lotto_type, draw_days[0]))
    while True:
        dt += timedelta(days=1)
        if dt.weekday() in allowed:
            return dt.date()

@lru_cache(maxsize=8192)
def _check_alt_any_cached(hist_key, p1, p2):
    if len(hist_key) < 4:
        return False
    def check_4(h, a, b):
        return (a in h[0] and b in h[1] and a in h[2] and b in h[3])
    newest_4 = hist_key[:4]
    oldest_4 = hist_key[-4:]
    return (check_4(newest_4, p1, p2) or check_4(newest_4, p2, p1) or
            check_4(oldest_4, p1, p2) or check_4(oldest_4, p2, p1))

@lru_cache(maxsize=8192)
def _check_alt_vip_cached(hist_key, p1, p2):
    if len(hist_key) < 4:
        return False
    match1 = True
    match2 = True
    for i, h in enumerate(hist_key):
        if i % 2 == 0:
            if p1 not in h:
                match1 = False
            if p2 not in h:
                match2 = False
        else:
            if p2 not in h:
                match1 = False
            if p1 not in h:
                match2 = False
        if not match1 and not match2:
            return False
    return True


@lru_cache(maxsize=8192)
def _cached_pred_nums_tuple(R, c_tuple, max_val, sum_mode, cyclic, is_tail_match, is_tail_drag):
    preds = []
    if is_tail_drag:
        c = c_tuple[0]
        heads = c_tuple[1:]
        if sum_mode:
            tail = (c - R) % 10
        else:
            tail = (R + c) % 10
        for h in heads:
            p = h * 10 + tail
            if 1 <= p <= max_val:
                preds.append(p)
        return tuple(sorted(set(preds)))

    for c in c_tuple:
        if sum_mode:
            p = c - R
        else:
            p = R + c

        if is_tail_match:
            preds.append(p)
        elif cyclic:
            p = (p - 1) % max_val + 1
            preds.append(p)
        else:
            if 1 <= p <= max_val:
                preds.append(p)
    return tuple(sorted(set(preds)))

def check_alt_any(hist, p1, p2):
    hist_key = tuple(tuple(h) if not isinstance(h, set) else tuple(sorted(h)) for h in hist)
    return _check_alt_any_cached(hist_key, p1, p2)

def check_alt_vip(hist, p1, p2):
    hist_key = tuple(tuple(h) if not isinstance(h, set) else tuple(sorted(h)) for h in hist)
    return _check_alt_vip_cached(hist_key, p1, p2)

def get_method_string(mode, c_list, sum_mode, is_tail_drag, is_nurture=False):
    if mode in[0, 7, 8, 12, 13, 14, 15, 18]:
        if mode == 8:
            pos_strs = ",".join(str(c+1) for c in sorted(c_list))
            return f"拖牌位置:第{pos_strs}支"
        elif is_tail_drag:
            # 一般取尾配頭:C_list = (尾差, 頭1, 頭2...)。
            # 星期加減合數取尾配頭:C_list = ((尾差1, 頭1), (尾差2, 頭2)...),每個固定位置各自配頭。
            try:
                if c_list and isinstance(c_list[0], (tuple, list)):
                    items = []
                    for ent in c_list:
                        if not isinstance(ent, (tuple, list)) or len(ent) < 2:
                            continue
                        c, h = int(ent[0]), int(ent[1])
                        c_txt = f"合{c}" if sum_mode else (f"+{c}" if c >= 0 else f"{c}")
                        items.append(f"{c_txt}({h}頭)")
                    return ("合數:" if sum_mode else "加減:") + ".".join(items)
            except Exception:
                pass
            c = c_list[0]
            heads = c_list[1:]
            heads_str = ".".join(str(h) for h in sorted(heads))
            if sum_mode:
                return f"合數:{c}({heads_str}頭)"
            else:
                return f"加減:{'+' if c >= 0 else ''}{c}({heads_str}頭)"
        elif sum_mode:
            return "合數:合" + ".".join(str(c) for c in sorted(c_list))
        else:
            return "加減:" + "".join((f"+{c}" if c >= 0 else f"{c}") for c in sorted(c_list))
    elif mode == 1:
        return "熱門拖牌"
    elif mode in[2, 3, 4]:
        return f"{mode}連拖"
    elif mode == 5:
        return "雙碼拖牌"
    elif mode == 9:
        return "立柱熱門"
    elif mode == 10:
        return "每月週牌(養牌)" if is_nurture else "每月週牌"
    elif mode == 11:
        return "N次週牌"
    elif mode == 14:
        return "同棟2號"
    elif mode == 16:
        return "日期版路"
    return ""


def get_compact_method_label(c_list, sum_mode, is_tail_drag):

    if not c_list:
        return ""
    if is_tail_drag:
        try:
            if c_list and isinstance(c_list[0], (tuple, list)):
                items = []
                for ent in c_list:
                    if not isinstance(ent, (tuple, list)) or len(ent) < 2:
                        continue
                    c, h = int(ent[0]), int(ent[1])
                    c_txt = f"合{c}" if sum_mode else (f"+{c}" if c >= 0 else f"{c}")
                    items.append(f"{c_txt}({h}頭)")
                return ".".join(items)
        except Exception:
            pass
        c = c_list[0]
        heads = c_list[1:]
        heads_str = ".".join(str(h) for h in sorted(heads))
        if sum_mode:
            return f"合{c}({heads_str}頭)"
        return f"{'+' if c >= 0 else ''}{c}({heads_str}頭)"
    if sum_mode:
        return "".join(f"合{c}" for c in sorted(c_list))
    return "".join((f"+{c}" if c >= 0 else f"{c}") for c in sorted(c_list))

def format_weekday_rule_parts(week_rules, sum_mode, is_tail_match=False, max_parts=None, is_tail_drag=False):
    """星期加減合數專用短格式:上2第1(02)+14→16;取尾配頭:上2第1(02)+4尾配1頭→16。"""
    parts = []
    if not week_rules:
        return parts
    rules = list(week_rules)
    if max_parts is not None and max_parts > 0:
        show_rules = rules[:max_parts]
    else:
        show_rules = rules
    for rule in show_rules:
        try:
            off = int(rule.get('offset', 0) or 0)
            pos = int(rule.get('pos', 0) or 0)
            base = int(rule.get('base', 0) or 0)
            c_val = int(rule.get('c', 0) or 0)
            pred = rule.get('pred', None)
            head_val = rule.get('head', None)
            if pred is None:
                pred_txt = '無'
            elif is_tail_match and not is_tail_drag:
                pred_txt = f'{int(pred) % 10}尾'
            else:
                pred_txt = f'{int(pred):02d}'
            c_txt = f"合{c_val}" if sum_mode else (f"+{c_val}" if c_val >= 0 else f"{c_val}")
            if is_tail_drag or head_val is not None:
                try:
                    head_txt = f"{int(head_val)}頭"
                except Exception:
                    head_txt = "?頭"
                parts.append(f"上{off}第{pos+1}({base:02d}){c_txt}尾配{head_txt}→{pred_txt}")
            else:
                parts.append(f"上{off}第{pos+1}({base:02d}){c_txt}→{pred_txt}")
        except Exception:
            continue
    if max_parts is not None and max_parts > 0 and len(rules) > max_parts:
        parts.append('...')
    return parts


def format_weekday_rule_parts_compact(week_rules, sum_mode, max_parts=None, is_tail_drag=False):
    """星期加減合數更精簡格式:上1第1隻+0、上2第1隻+19;取尾配頭:上2第1隻+4尾配1頭。"""
    parts = []
    if not week_rules:
        return parts
    rules = list(week_rules)
    if max_parts is not None and max_parts > 0:
        show_rules = rules[:max_parts]
    else:
        show_rules = rules
    for rule in show_rules:
        try:
            off = int(rule.get('offset', 0) or 0)
            pos = int(rule.get('pos', 0) or 0)
            c_val = int(rule.get('c', 0) or 0)
            head_val = rule.get('head', None)
            c_txt = f"合{c_val}" if sum_mode else (f"+{c_val}" if c_val >= 0 else f"{c_val}")
            prefix = f"上{off}第{pos+1}隻"
            if is_tail_drag or head_val is not None:
                try:
                    head_txt = f"{int(head_val)}頭"
                except Exception:
                    head_txt = "?頭"
                parts.append(f"{prefix}{c_txt}尾配{head_txt}")
            else:
                parts.append(f"{prefix}{c_txt}")
        except Exception:
            continue
    if max_parts is not None and max_parts > 0 and len(rules) > max_parts:
        parts.append('...')
    return parts

def _sorted_display_list(values):

    if not values:
        return []
    try:
        return sorted(values)
    except Exception:
        return sorted(values, key=lambda x: str(x))

def expand_tail_values(tail_values, max_val):
    """把尾數展開成實際號碼。例:尾 1、max_val=49 -> 01.11.21.31.41。"""
    try:
        max_v = int(max_val)
    except Exception:
        max_v = 0
    if max_v <= 0:
        return []

    tails = []
    for t in (tail_values or []):
        try:
            tv = int(t) % 10
        except Exception:
            continue
        if tv not in tails:
            tails.append(tv)

    nums = []
    for n in range(1, max_v + 1):
        if (n % 10) in tails:
            nums.append(n)
    return nums

def format_tail_number_groups(tail_values, max_val, group_sep='|', num_sep='.'):
    """顯示尾數時,每一尾都展開成同尾全部號碼。"""
    groups = []
    seen = []
    for t in (tail_values or []):
        try:
            tv = int(t) % 10
        except Exception:
            continue
        if tv in seen:
            continue
        seen.append(tv)
    for tv in sorted(seen):
        nums = expand_tail_values([tv], max_val)
        if nums:
            groups.append(num_sep.join(f'{n:02d}' for n in nums))
    return group_sep.join(groups)

def format_tail_labels(tail_values, sep='.'):
    """尾數簡短顯示。例:1尾2尾。"""
    seen = []
    for t in (tail_values or []):
        try:
            tv = int(t) % 10
        except Exception:
            continue
        if tv not in seen:
            seen.append(tv)
    return sep.join(f'{tv}尾' for tv in sorted(seen)) or '無'

def format_pred_nums_for_display(pred_nums, max_val=None, is_tail_match=False, expand_tails=False, group_tails=False):
    """統一輸出預測號碼文字;日期版路尾數模式簡短顯示為 1尾2尾。"""
    if expand_tails and is_tail_match:
        return format_tail_labels(pred_nums, sep='')
    return '.'.join(f'{int(n):02d}' for n in (pred_nums or [])) if pred_nums else '無'


def mode12_pred_value(base_val, c_val, sum_mode, cyclic, max_val):
    p = (c_val - base_val) if sum_mode else (base_val + c_val)
    if cyclic:
        p = (p - 1) % max_val + 1
    return p

def mode12_tail_value(base_val, c_tail, sum_mode):
    return (c_tail - base_val) % 10 if sum_mode else (base_val + c_tail) % 10


def weekly_mutual_add_sub_values(trigger_val, blue_val, sum_mode, max_val, sum_base=None, cyclic=True, tail_match=False):
    """週牌「號碼相互加減」結果。

    一般模式:先做互加/互減,再依彩種最大號碼循環。
    合數模式:先做互加/互減得到「基準值」,再套用其他版路相同的
    「參數減基準」邏輯。也就是:答案 = 合數參數 - 互加/互減結果。

    cyclic=False (不允許號碼循環):超出 1~max_val 範圍直接視為無效(None),不循環。
    tail_match=True (尾數模式):不限制範圍、不循環,回傳原始互加/互減結果,
    交由呼叫端只比對尾數(個位數)是否命中,而不要求整個號碼落在合法範圍內。

    例:
      21 + 13 = 34,合數參數 44 → 44 - 34 = 10
      |21 - 13| = 8,合數參數 44 → 44 - 8 = 36
    """
    raw_add = int(trigger_val) + int(blue_val)
    raw_sub = abs(int(trigger_val) - int(blue_val))

    if sum_mode:
        if sum_base is None:
            # 沒有提供合數參數時不再偷偷套「合數10」;由呼叫端搜尋真正的合數參數。
            return None, None
        try:
            base = int(sum_base)
        except Exception:
            return None, None
        add_val = base - raw_add
        sub_val = base - raw_sub
        if tail_match:
            return add_val, sub_val
        if cyclic:
            add_val = ((add_val - 1) % max_val) + 1
            sub_val = ((sub_val - 1) % max_val) + 1
        else:
            add_val = add_val if 1 <= add_val <= max_val else None
            sub_val = sub_val if 1 <= sub_val <= max_val else None
        return add_val, sub_val

    if tail_match:
        return raw_add, raw_sub
    if cyclic:
        add_val = ((raw_add - 1) % max_val) + 1
        sub_val = ((raw_sub - 1) % max_val) + 1
    else:
        add_val = raw_add if 1 <= raw_add <= max_val else None
        sub_val = raw_sub if 1 <= raw_sub <= max_val else None
    return add_val, sub_val

def _build_occurrence_indexes(processed_data, max_val):
    by_set = {n: [] for n in range(1, max_val + 1)}
    by_pos = []
    append_by_pos = by_pos.append
    for idx, item in enumerate(processed_data):
        item_set = item.get('set') or ()
        for n in item_set:
            if 1 <= n <= max_val:
                by_set[n].append(idx)

        item_list = item.get('list') or ()
        for pos, val in enumerate(item_list):
            while len(by_pos) <= pos:
                append_by_pos({})
            by_pos[pos].setdefault(val, []).append(idx)
    return by_set, by_pos


_PRED_RANGE_COUNT = {0: 1, 1: 2, 2: 3, 3: 2, 4: 3}
_PRED_RANGE_LABEL_FULL = {0: '【預測1期內】', 1: '【預測2期內】', 2: '【預測3期內】', 3: '【第2期到期】', 4: '【第3期到期】'}
_PRED_RANGE_LABEL_SHORT = {0: '[1期]', 1: '[2期]', 2: '[3期]', 3: '[2期到]', 4: '[3期到]'}

def get_pred_range_count(pred_range):
    return _PRED_RANGE_COUNT.get(pred_range, 1)

def get_pred_range_label(pred_range, full=False):
    return (_PRED_RANGE_LABEL_FULL if full else _PRED_RANGE_LABEL_SHORT).get(pred_range, '')

class LottoEngine:
    """
    從原始 Pythonista App 抽出的純運算引擎(不含 ui/photos/console 依賴)。
    給網頁版透過 Pyodide 呼叫,計算邏輯與原始 App 保持一致。
    """

    def __init__(self, lotto_type=2):
        self.lotto_type = lotto_type
        self.num_count = {0: 5, 1: 5, 2: 6, 3: 6}
        self.max_num = {0: 39, 1: 39, 2: 49, 3: 49}
        self.has_special = {0: False, 1: False, 2: True, 3: True}

        self.data = []  # list of dict: {'date': date, 'list': tuple(nums), 'set': set(nums), 'special': int|None}
        self.current_analysis_mode = 0
        self.mode_settings = {}
        self.pred_range_index = 0     # 對應原本 pred_range_seg.selected_index
        self.data_limit_index = 2     # 對應原本 data_limit_seg.selected_index
        self.overall_route_mode_id = 99
        self.is_analyzing = True      # 網頁版不支援中途取消,固定 True

        # 刻意不預先放內容,讓每次呼叫都重新計算,不吃到過期快取
        self._analysis_cache = {}
        self._analysis_result_cache = {}
        self._analysis_last_profile = {}

    def _make_analysis_cache_key(self, limit_date, exclude_today, params):
        # 網頁版每次都重新運算,回傳保證不重複的 key,讓快取永遠不命中
        import time as _t
        return (id(params), limit_date, exclude_today, _t.perf_counter())

    def set_data(self, rows):
        """rows: list of (date_iso_str, numbers_list, special_or_none)
        對應原始 self.data 的格式:(date, nums_tuple, special) 的純 tuple,
        不是 dict —— dict 化是 execute_analysis_for_date 內部自己做的事。"""
        from datetime import date as _date
        processed = []
        for date_iso, nums, special in rows:
            y, m, d = [int(x) for x in date_iso.split('-')]
            dt = _date(y, m, d)
            processed.append((dt, list(nums), special))
        processed.sort(key=lambda it: it[0])
        self.data = processed

    def get_default_mode_settings(self):
        return {
            'is_double_trigger': True,
            'is_weekly_double_position': False,


            'same_period_pair_mode': 1,
            'min_hit_list': [1],
            'max_n_index': 1,
            'interval_step': 1,
            'is_cyclic': False,
            'is_consec': False,
            'is_tail': False,
            'is_sum': False,
            'is_fixed_pos': True,
            'is_alternate': False,
            'is_alternate_vip': False,
            'is_staircase': False,
            'is_step_advance': False,
            'only_next_hot_drag': False,
            'is_incremental_n': False,
            'is_weekly_n_add_sub': False,
            'weekly_blue_pos': 0,
            'is_tail_match': False,
            'is_tail_drag': False,
            'is_triple_star': False,
            'is_dual_incremental_n': False,
            'is_dual_cyclic': False,
            'is_non_hit': False,
            'weekdays':[],
            'n_period_enable': False,
            'n_period_gap': 0,
            'is_nurture': False,
            'pillar_counts':[3, 0, 0, 0, 0],
            'date_route_periods':['0', '0', '0', '0'],
            'pred_range_index': 0,
            'select_count': '2',
            'min_streak': '0',
            'shape_index': 0,
            'lock_special': False
        }


    def next_draw_date(self, dt):
        draw_days = {0:[0, 1, 2, 3, 4, 5], 1:[0, 1, 2, 3, 4, 5, 6], 2:[1, 4], 3:[1, 3, 5]}
        while True:
            dt += timedelta(days=1)
            if dt.weekday() in draw_days[self.lotto_type]: return dt


    def get_overall_analysis_modes(self):
        return [
            (0, '定位合數加減'),
            (7, '週牌合數加減'),
            (12, '同期雙邊'),
            (1, '熱門拖牌'),
            (5, '雙碼拖牌'),
            (8, '定點定位拖牌'),
            (2, '2連拖'),
            (3, '3連拖'),
            (4, '4連拖'),
            (13, '圖形版路'),
            (15, '星期加減合數'),
        ]


    def is_overall_route_mode(self):
        return self.current_analysis_mode == getattr(self, 'overall_route_mode_id', 99)


    def get_pred_nums(self, R, C_list, max_val, sum_mode, cyclic, is_tail_match=False, is_tail_drag=False):
        return list(_cached_pred_nums_tuple(R, tuple(C_list), max_val, sum_mode, cyclic, is_tail_match, is_tail_drag))


    def get_analysis_params(self, mode_id=None):
        if mode_id is None:
            mode_id = self.current_analysis_mode

        settings = self.mode_settings.get(mode_id, self.get_default_mode_settings())

        alt_vip_enabled = bool(settings.get('is_alternate_vip', False))
        alt_enabled = bool(settings.get('is_alternate', False)) and not alt_vip_enabled

        try:
            min_streak = int(settings.get('min_streak', '7'))
            if min_streak < 0: min_streak = 0
        except ValueError:
            min_streak = 7

        if mode_id == 12:


            try:
                same_period_pair_mode = int(settings.get('same_period_pair_mode', 1))
            except Exception:
                same_period_pair_mode = 1
            if same_period_pair_mode not in (0, 1, 2):
                same_period_pair_mode = 1
        else:
            same_period_pair_mode = None

        is_weekly_double_position = (mode_id == 12 and same_period_pair_mode == 2)
        effective_mode_id = 14 if is_weekly_double_position else mode_id

        if mode_id in[9, 10, 16]:
            pick_count = sum(settings.get('pillar_counts',[3, 3, 3, 0, 0]))
        else:
            select_count_raw = settings.get('select_count', '2')
            if mode_id == 11 and (select_count_raw is None or str(select_count_raw).strip() == ''):
                try:
                    pick_count = max(1, sum(int(x or 0) for x in settings.get('pillar_counts', [3, 0, 0, 0, 0])))
                except Exception:
                    pick_count = 2
            else:
                try:
                    pick_count = max(1, int(select_count_raw))
                except ValueError:
                    pick_count = 2

            if effective_mode_id == 14 and not settings.get('is_tail_drag', False):


                if alt_enabled or alt_vip_enabled:
                    pick_count = max(2, pick_count)

        if mode_id == self.current_analysis_mode or self.is_overall_route_mode():
            pred_range = self.pred_range_index
        else:
            pred_range = settings.get('pred_range_index', 0)

        interval_val = settings.get('interval_step', 1)
        if interval_val == 6:
            interval_list =[1, 2, 3, 4, 5]
        else:
            interval_list =[interval_val]


        if effective_mode_id == 14 and 2 not in interval_list:
            interval_list = [2] + interval_list

        raw_min_hit_list = settings.get('min_hit_list', [1])
        try:
            min_hit_list = sorted({int(x) for x in raw_min_hit_list})
        except Exception:
            min_hit_list = [1]

        min_hit_req = min(min_hit_list) if min_hit_list else 1
        lock_special_enabled = bool(settings.get('lock_special', False) and self.lotto_type in (2, 3) and effective_mode_id in (0, 1, 2, 3, 4, 5, 7, 8, 12, 13, 14, 15))
        # 自動天地碰:六合彩/大樂透鎖定特別號/第7隻,且 1星關閉、最低星數為2以上時,
        # 開始分析/冠軍分析/整體版路分析都自動採用「特別號必須中 + 裡面號碼也必須中」。
        special_tiandi_mode = bool(
            lock_special_enabled
            and min_hit_req >= 2
            and not settings.get('is_tail_match', False)
            and not settings.get('is_tail_drag', False)
            and not settings.get('is_non_hit', False)
        )
        if special_tiandi_mode:
            # 例如選4星但選號數量還停在2,會永遠不可能達標;自動補到最低星數。
            pick_count = max(pick_count, min_hit_req)

        return {
            'analysis_mode': effective_mode_id,
            'source_mode': mode_id,
            'is_weekly_double_position': is_weekly_double_position,
            'same_period_pair_mode': same_period_pair_mode if mode_id == 12 else None,
            'pred_range': pred_range,
            # 星數可複選;實際門檻使用最低選取星數,例如 2星+3星 = 至少2星,另外統計含3星以上。
            'min_hit_list': list(min_hit_list),
            'min_hit_req': min_hit_req,
            'min_streak': min_streak,
            'pick_count': pick_count,
            'max_n':[3, 6, 9, 12, 15][settings.get('max_n_index', 1)],
            'interval_step': interval_val,
            'is_consec': settings.get('is_consec', False),
            'is_tail': settings.get('is_tail', False),
            'is_sum': settings.get('is_sum', False),
            'is_cyclic': settings.get('is_cyclic', False),
            'is_fixed_pos': settings.get('is_fixed_pos', True),
            'is_alternate': alt_enabled,
            'is_alternate_vip': alt_vip_enabled,
            'is_staircase': settings.get('is_staircase', False),
            'is_step_advance': settings.get('is_step_advance', False),
            'is_incremental_n': settings.get('is_incremental_n', False),
            'is_weekly_n_add_sub': settings.get('is_weekly_n_add_sub', False),
            'step_val': settings.get('step_val', 0),
            'is_step_interval': settings.get('is_step_interval', False),
            'is_tail_match': settings.get('is_tail_match', False),
            'is_tail_drag': settings.get('is_tail_drag', False),
            'is_triple_star': settings.get('is_triple_star', False),
            'is_dual_incremental_n': settings.get('is_dual_incremental_n', False),
            'is_dual_cyclic': settings.get('is_dual_cyclic', False),
            'lock_special': lock_special_enabled,
            'special_tiandi_mode': special_tiandi_mode,


            'is_double_trigger': ((same_period_pair_mode == 1) if mode_id == 12 else settings.get('is_double_trigger', True)),
            'is_non_hit': settings.get('is_non_hit', False),
            'balls_cnt': self.num_count[self.lotto_type],
            'max_val': self.max_num[self.lotto_type],
            'has_special': self.has_special[self.lotto_type],
            'interval_list': interval_list,
            'data_limit_mode': self.data_limit_index,
            'weekdays': settings.get('weekdays',[]),
            'n_period_enable': settings.get('n_period_enable', False),
            'n_period_gap': settings.get('n_period_gap', 0),
            'is_nurture': settings.get('is_nurture', False),
            'pillar_counts': settings.get('pillar_counts',[3, 3, 3, 0, 0]),
            'date_route_periods': settings.get('date_route_periods', ['0', '0', '0', '0']),
            'shape_index': settings.get('shape_index', 0)
        }


    def format_rule_text(self, idx, res, params):
        streak = res['streak']
        X, P_X= res.get('X'), res.get('P_X')
        N, P, M = res.get('N', 0), res.get('P', 0), res['M']
        C_list = res.get('C_list',[])
        ref_dir = res.get('ref_dir', 0)
        pred_nums = res['latest_pred_nums']
        mode = res.get('mode', 0)
        pred_range = res.get('pred_range', 0)
        is_tail_match = res.get('is_tail_match', False)
        is_tail_drag = res.get('is_tail_drag', False)
        is_non_hit = res.get('is_non_hit', False)
        sum_mode = res.get('sum_mode', params.get('is_sum', False))

        p_range_str = get_pred_range_label(pred_range, full=True)
        if res.get('lock_special', False):
            p_range_str = f"{p_range_str} 🔒特別號"
            if res.get('special_tiandi_mode', False) or (int(res.get('min_hit_req', 1) or 1) >= 2 and not res.get('is_tail_match', False) and not res.get('is_tail_drag', False) and not res.get('is_non_hit', False)):
                p_range_str = f"{p_range_str}|特殊天地碰"

        pred_str_dot = ".".join(f"{n:02d}" for n in pred_nums) if pred_nums else "無"
        if mode == 16 and is_tail_match:
            pred_str_dot = format_pred_nums_for_display(
                pred_nums,
                res.get('max_val', params.get('max_val')),
                is_tail_match=True,
                expand_tails=True,
                group_tails=True
            )

        elif mode == 18 and is_tail_match:
            # 號碼相互加減尾數模式:開始分析詳細結果顯示完整尾數群組。
            pred_str_dot = format_tail_number_groups(
                pred_nums,
                res.get('max_val', params.get('max_val')),
                group_sep='|',
                num_sep='.'
            ) or pred_str_dot

        if is_non_hit:
            lbl_pred = "不出尾數" if is_tail_match else "不出號碼"
            color_dot = "🟣"
        else:
            lbl_pred = "預測尾數" if is_tail_match else "預測號碼"
            color_dot = "🔴"

        res_text = ""
        if mode == 16:
            periods = res.get('date_route_periods', []) or params.get('date_route_periods', []) or []
            active_periods_for_range = [p for p in periods if str(p).strip() and str(p).strip() != '0']
            if active_periods_for_range:
                p_range_str = f"{len(active_periods_for_range)}期內" if len(active_periods_for_range) > 1 else "1期"
            period_str = '.'.join(str(p) for p in active_periods_for_range) or '未指定'
            issue_cnt = res.get('current_month_issue_count', 0)
            res_text += f"第 {idx+1} 條版路(日期版路) {p_range_str}\n"
            res_text += f"目前第{issue_cnt}期|指定每月第{period_str}期驗證|準 {streak} 次\n"
            if res.get('pillars'):
                pillar_parts = []
                for p_idx, p_nums in enumerate(res.get('pillars', [])):
                    if not p_nums:
                        continue
                    if is_tail_match:
                        nums_s = format_pred_nums_for_display(
                            p_nums,
                            res.get('max_val', params.get('max_val')),
                            is_tail_match=True,
                            expand_tails=True,
                            group_tails=True
                        )
                    else:
                        nums_s = '.'.join(f'{int(n):02d}' for n in p_nums)
                    pillar_parts.append(f'第{p_idx+1}柱:{nums_s}')
                if pillar_parts:
                    res_text += ' | '.join(pillar_parts) + '\n'
            res_text += f"{lbl_pred}: {pred_str_dot} {color_dot}\n"
        elif mode == 9:
            trigger_str = f"開出 {X:02d}" if P_X == -1 else f"開 {X:02d} 第 {P_X+1} 支"
            res_text += f"第 {idx+1} 條版路(立柱熱門) {p_range_str}\n"
            res_text += f"{trigger_str}, 下 {M} 期拖牌\n"
            pillars_text = ""
            for p_idx, p_nums in enumerate(res.get('pillars',[])):
                if p_nums:
                    sorted_nums = _sorted_display_list(p_nums)
                    pillars_text += f" 第{p_idx+1}柱(" + ".".join(f"{n:02d}" for n in sorted_nums) + ")"
            three_star_count = res.get('three_star_count', 0)
            extra_info = f" (含{three_star_count}次3星以上)" if three_star_count > 0 else ""
            res_text += f"準 {streak} 次{extra_info} 立柱:{pillars_text} {color_dot}\n\n"
        elif mode == 10:
            wd_names =['週一', '週二', '週三', '週四', '週五', '週六', '週日']
            wd_str = "、".join([wd_names[w] for w in res.get('weekdays',[])]) if res.get('weekdays') else "全部"
            n_period_enable = res.get('n_period_enable', False)
            gap = res.get('n_period_gap', 0)
            is_nurture = res.get('is_nurture', False)

            nurture_str = "[養牌中]" if is_nurture else "[預測未開]"

            res_text += f"第 {idx+1} 條版路(每月週牌) {nurture_str} {p_range_str}\n"
            if n_period_enable:
                res_text += f"過濾: {wd_str} | 每 {3+gap} 期群組中(空 {gap} 期) 達標一次即可\n"
            else:
                res_text += f"過濾: {wd_str} | 群組連續達標\n"

            pillars_text = ""
            for p_idx, p_nums in enumerate(res.get('pillars',[])):
                if p_nums:
                    sorted_nums = _sorted_display_list(p_nums)
                    pillars_text += f" 第{p_idx+1}柱(" + ".".join(f"{n:02d}" for n in sorted_nums) + ")"
            three_star_count = res.get('three_star_count', 0)
            extra_info = f" (含{three_star_count}次3星以上)" if three_star_count > 0 else ""
            res_text += f"準 {streak} 次{extra_info} 立柱:{pillars_text} {color_dot}\n\n"
        elif mode == 11:
            interval = res.get('interval', 1)
            is_step_interval = res.get('is_step_interval', False)
            is_alt_vip_n11 = res.get('is_alternate_vip', False)
            is_alt_n11 = res.get('is_alternate', False)
            alt_suffix_n11 = '(🌟嚴格輪流)' if is_alt_vip_n11 else ('(輪流)' if is_alt_n11 else '')
            seq_chain = res.get('seq_chain')
            if seq_chain:
                c_str = "→".join(f"{c:02d}" for c in seq_chain)
            else:
                is_tail = res.get('is_tail_match', False)
                if is_tail:
                    c_str = "尾" + ".".join(f"{c}" for c in sorted(C_list))
                else:
                    c_str = ".".join(f"{c:02d}" for c in sorted(C_list))
            res_text += f"第 {idx+1} 條版路(N次週牌){alt_suffix_n11} {p_range_str}\n"
            if is_step_interval:
                step_intervals_str = ".".join(str(interval - streak + 1 + i) for i in range(streak))
                res_text += f"步步間隔:{step_intervals_str} (下次{interval}期), 候選:{c_str}\n"
            else:
                res_text += f"每 {interval} 期一次, 候選:{c_str}\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 1:
            is_step_advance = res.get('is_step_advance', False)
            step_val = res.get('step_val', 0)
            step_adv_str = f" (步步進擊{'+' if step_val>0 else ''}{step_val})" if is_step_advance and step_val != 0 else ""
            trigger_str = f"開出 {X:02d}" if P_X == -1 else f"開 {X:02d} 第 {P_X+1} 支"
            res_text += f"第 {idx+1} 條版路(熱門拖牌) {p_range_str}\n"
            res_text += f"{trigger_str}, 下 {M} 期拖牌{step_adv_str}\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode in[2, 3, 4]:
            seq = res.get('seq',[])
            seq_pos = res.get('seq_pos', [-1]*len(seq))
            if seq_pos[0] != -1:
                seq_str = " ➔ ".join(f"{v:02d}(第{p+1}支)" for v, p in zip(seq, seq_pos))
            else:
                seq_str = " ➔ ".join(f"{v:02d}" for v in seq)
            res_text += f"第 {idx+1} 條版路({mode}連拖) {p_range_str}\n"
            res_text += f"{seq_str} (間隔{N}期), 再下 {M} 期拖牌\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 5:
            X_val, Y = res.get('X'), res.get('Y')
            Z = res.get('Z')
            P_X_val, P_Y = res.get('P_X', -1), res.get('P_Y', -1)
            P_Z = res.get('P_Z', -1)
            is_triple = res.get('is_triple_star', False)
            is_dual_incr = res.get('is_dual_incremental_n', False)
            is_dual_cyc = res.get('is_dual_cyclic', False)
            dual_str = ""
            if is_dual_incr or is_dual_cyc:
                dual_step = res.get('dual_step_val', 0)
                dual_label = "加減遞加N" if is_dual_incr else "號碼循環"
                cyc_str = "(允許循環)" if is_dual_cyc else ""
                step_word = f"+{dual_step}" if dual_step >= 0 else f"{dual_step}"
                dual_str = f" [{dual_label}:級距{step_word}{cyc_str}]"

            if is_triple:
                res_text += f"第 {idx+1} 條版路(三碼模式) {p_range_str}\n"
                if P_X_val != -1:
                    res_text += f"開出 {X_val:02d}(第{P_X_val+1}支), {Y:02d}(第{P_Y+1}支), {Z:02d}(第{P_Z+1}支), 下 {M} 期拖牌{dual_str}\n"
                else:
                    res_text += f"開出 {X_val:02d}, {Y:02d}, {Z:02d}, 下 {M} 期拖牌{dual_str}\n"
            else:
                res_text += f"第 {idx+1} 條版路(雙同星) {p_range_str}\n"
                if P_X_val != -1:
                    res_text += f"開出 {X_val:02d}(第{P_X_val+1}支) 與 {Y:02d}(第{P_Y+1}支), 下 {M} 期拖牌{dual_str}\n"
                else:
                    res_text += f"開出 {X_val:02d} 與 {Y:02d}, 下 {M} 期拖牌{dual_str}\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 12:
            pl1, pl2 = res['pl1'], res['pl2']
            pr1, pr2 = res['pr1'], res['pr2']
            is_double_trigger = res.get('is_double_trigger', True)
            interval = res.get('interval', 1)
            step_val = res.get('step_val', 0)
            is_step_advance = res.get('is_step_advance', False)
            step_adv_str = f" (步步進擊{'+' if step_val>0 else ''}{step_val})" if is_step_advance and step_val != 0 else ""
            c_str = get_method_string(0, C_list, sum_mode, is_tail_drag).replace("合數:", "").replace("加減:", "")

            op_str = "合數" if sum_mode else "加減"
            pair_mode = res.get('same_period_pair_mode', params.get('same_period_pair_mode', None))
            pair_label = '左右各2號' if is_double_trigger else '左右各1號'
            if pair_mode == 0:
                pair_label = '左右各1號'
            elif pair_mode == 1:
                pair_label = '左右各2號'

            res_text += f"第 {idx+1} 條版路(同期雙邊對齊|{pair_label}) {p_range_str}\n"
            if is_double_trigger:
                res_text += f"每 {interval} 期, 同排左右棟[左第{pl1+1}、{pl2+1}支|右第{pr1+1}、{pr2+1}支差] {op_str}\n"
            else:
                res_text += f"每 {interval} 期, 同排左右棟[左第{pl1+1}支|右第{pr1+1}支] {op_str}\n"
            res_text += f"再 {c_str}{step_adv_str}, 下 {M} 期開\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 13:
            shape_index = res.get('shape_index', 0)
            c_str = get_method_string(0, C_list, sum_mode, is_tail_drag).replace("合數:", "").replace("加減:", "")
            op_str = "合數" if sum_mode else "加減"

            shape_names =['菱形', '六芒星', '倒三角', '三角形', '星辰圖', '全部圖形', '圓形']
            shape_name = shape_names[shape_index] if 0 <= shape_index < len(shape_names) else '菱形'
            mode_name = f'{shape_name}加減'

            trigger_str = f"開出 {X:02d}" if P_X == -1 else f"開 {X:02d} 第 {P_X+1} 支"
            res_text += f"第 {idx+1} 條版路({mode_name}) {p_range_str}\n"
            if shape_index == 1:
                res_text += f"{trigger_str}, 第3隻號碼觸發點→六芒星尾數{op_str} {c_str}, 下 {M} 期開\n"
            elif shape_index == 2:
                res_text += f"{trigger_str}, 鎖定第一隻→當期第一隻/第三隻/下二期第二隻 互減尾數 {op_str} {c_str}, 下 {M} 期開\n"
            elif shape_index == 3:
                res_text += f"{trigger_str}, 鎖定第一隻→當期第一隻/第三隻/下二期第二隻 互減尾數 {op_str} {c_str}, 下 {M} 期開\n"
            elif shape_index == 4:
                res_text += f"{trigger_str}, 鎖定第三隻→上三期第三隻(藍)/上一期第一與第五隻(淡黃)/下二期第一與第五隻(淡綠) 互加尾數 {op_str} {c_str}, 下 {M} 期開\n"
            elif shape_index == 6:
                res_text += f"{trigger_str}, 鎖定第一隻→上五期第五隻/下三期第五隻/下六期第一隻 尾數相加 {op_str} {c_str}, 下 {M} 期開\n"
            else:
                res_text += f"{trigger_str}, 同期{shape_name}四頂點尾數相加 {op_str} {c_str}, 下 {M} 期開\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 15:
            wd_names = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
            wd = res.get('weekday', 0)
            wd_str = wd_names[wd] if isinstance(wd, int) and 0 <= wd < len(wd_names) else '指定星期'
            is_step_advance = res.get('is_step_advance', False)
            step_val = res.get('step_val', 0)
            step_adv_str = f" (步步進擊{'+' if step_val>0 else ''}{step_val})" if is_step_advance and step_val != 0 else ""
            op_str = '合數' if sum_mode else '加減'
            min_hit_req = int(res.get('min_hit_req', 1) or 1)

            rule_parts = format_weekday_rule_parts(res.get('week_rules', []), sum_mode, is_tail_match, is_tail_drag=is_tail_drag)

            if not rule_parts:
                off1 = int(res.get('ref1_offset', 3) or 3)
                p1 = int(res.get('P1', 0) or 0)
                r1 = int(res.get('R1', 0) or 0)
                c_str = get_method_string(15, C_list, sum_mode, False).replace('合數:', '').replace('加減:', '')
                rule_parts.append(f"上{off1}第{p1+1}({r1:02d}){op_str}{c_str}")

            res_text += f"第 {idx+1} 條版路(星期加減合數|{wd_str}) {p_range_str}\n"
            res_text += "、".join(rule_parts) + "\n"
            hit_line = f"{wd_str}本期開其中{min_hit_req}隻"
            if step_adv_str:
                hit_line += step_adv_str
            res_text += f"{hit_line}|準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 7:
            interval = res.get('interval', 1)
            P = res.get('P', 0)
            is_weekly_n_add_sub = bool(res.get('is_weekly_n_add_sub', False))
            if is_weekly_n_add_sub:
                n_period = int(res.get('weekly_n_period', interval) or interval or 1)
                M_n = int(res.get('M', 1) or 1)
                blue_pos = max(0, min(4, int(res.get('weekly_blue_pos', 0) or 0)))
                trigger_pos = int(res.get('P', P) or P)
                stair_str = '(觸發點依階梯)' if res.get('is_staircase', False) else '(觸發點固定)'
                pred_vals = '/'.join(f'{int(v):02d}' for v in (res.get('latest_pred_nums') or []))
                # 開始分析摘要精簡成一行:
                # 第 1 條版路(粉紅色+-藍色) 【預測1期內】準 7 次預測號碼: 10.15 🔴
                res_text += f'第 {idx+1} 條版路(粉紅色+-藍色) {p_range_str}準 {streak} 次預測號碼: {pred_str_dot} {color_dot}\n\n'
                return res_text

            is_staircase = res.get('is_staircase', False)
            is_step_advance = res.get('is_step_advance', False)
            step_val = res.get('step_val', 0)
            step_adv_str = f" (步步進擊{'+' if step_val>0 else ''}{step_val})" if is_step_advance and step_val != 0 else ""
            is_incremental_n = res.get('is_incremental_n', False)
            incremental_n_val = res.get('incremental_n_val', 0)

            if is_incremental_n:
                base_c = C_list[0] if C_list else 0
                base_str = f"+{base_c}" if base_c >= 0 else f"{base_c}"
                incr_word = f"加{incremental_n_val}" if incremental_n_val >= 0 else f"減{abs(incremental_n_val)}"
                c_str = base_str + incr_word
            else:
                c_str = get_method_string(mode, C_list, sum_mode, is_tail_drag) + step_adv_str

            res_text += f"第 {idx+1} 條版路(週牌) {p_range_str}\n"
            stair_str = " (階梯模式)" if is_staircase else ""
            res_text += f"每{interval}期{stair_str}, 第 {P+1} 支 {c_str}, 下 {M} 期開\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        elif mode == 14:
            interval = res.get('interval', 1)
            P1 = res.get('P1', 1)
            P2 = res.get('P2', 4)
            is_step_advance = res.get('is_step_advance', False)
            step_val = res.get('step_val', 0)
            step_adv_str = f" (步步進擊{'+' if step_val>0 else ''}{step_val})" if is_step_advance and step_val != 0 else ""
            c_str = get_method_string(mode, C_list, sum_mode, is_tail_drag) + step_adv_str
            res_text += f"第 {idx+1} 條版路(同棟2號) {p_range_str}\n"
            res_text += f"每{interval}期, 藍色順{P1+1}與粉紅下1期順{P2+1} 相減取正數 {c_str}, 下 {M} 期開\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        else:
            trigger_str = f"開出 {X:02d}" if P_X == -1 else f"開 {X:02d} 第 {P_X+1} 支"
            c_str = get_method_string(mode, C_list, sum_mode, is_tail_drag)

            mode_name = '定點定位拖牌' if mode == 8 else '定位合數加減'
            res_text += f"第 {idx+1} 條版路({mode_name}) {p_range_str}\n"
            if N == 0:
                if mode == 8:
                    res_text += f"{trigger_str}, 同期 {c_str}, 下 {M} 期開\n"
                else:
                    res_text += f"{trigger_str}, 同期 第 {P+1} 支 {c_str}, 下 {M} 期開\n"
            else:
                dir_str = f"下 {N} 期" if ref_dir == 1 else f"上 {N} 期"
                if mode == 8:
                    res_text += f"{trigger_str}, {dir_str}, {c_str}, 下 {M} 期開\n"
                else:
                    res_text += f"{trigger_str}, {dir_str}, 第 {P+1} 支 {c_str}, 下 {M} 期開\n"
            res_text += f"準 {streak} 次{lbl_pred}: {pred_str_dot} {color_dot}\n\n"
        return res_text


    def execute_overall_analysis_for_date(self, limit_date, exclude_today, progress_callback=None):
        overall_modes = self.get_overall_analysis_modes()
        combined_results = []
        next_draw_data = []
        total_modes = len(overall_modes)

        for idx, (mode_id, mode_name) in enumerate(overall_modes):
            if not self.is_analyzing:
                raise InterruptedError()

            params = self.get_analysis_params(mode_id)

            def sub_progress(p, base_idx=idx, name=mode_name):
                overall_p = (base_idx + p) / max(1, total_modes)
                if progress_callback:
                    progress_callback(overall_p, name)

            top, nd = self.execute_analysis_for_date(limit_date, exclude_today, params, sub_progress)
            if not next_draw_data and nd:
                next_draw_data = nd
            for r in top:
                rr = dict(r)
                rr['overall_source_mode'] = mode_id
                rr['overall_source_name'] = mode_name
                combined_results.append(rr)

        combined_results.sort(
            key=lambda x: (
                x.get('streak', 0),
                1 if x.get('weekly_double_core') else 0,
                x.get('three_star_count', 0),
                -x.get('M', 0)
            ),
            reverse=True
        )
        if progress_callback:
            progress_callback(1.0, '整體版路圖')
        return combined_results[:1000], next_draw_data


    def execute_analysis_for_date(self, limit_date, exclude_today, params, progress_callback=None):
        cache_key = self._make_analysis_cache_key(limit_date, exclude_today, params)
        analysis_result_cache = getattr(self, '_analysis_result_cache', None) or {}
        cached_result = analysis_result_cache.get(cache_key)
        if cached_result is not None:
            self._analysis_last_profile = dict(cached_result.get('profile', {}))
            self._analysis_last_profile['cache_hit'] = True
            if progress_callback:
                progress_callback(1.0)
            return [dict(r) for r in cached_result['top']], list(cached_result['next'])


        if params.get('analysis_mode') == 13 and int(params.get('shape_index', 0)) == 5:
            shape_names_all = ['菱形', '六芒星', '倒三角', '三角形', '星辰圖']
            combined_results = []
            next_draw_data_all = []
            total_shapes = len(shape_names_all)
            for sidx, sname in enumerate(shape_names_all):
                sub_params = dict(params)
                sub_params['shape_index'] = sidx

                def sub_progress(p, base_idx=sidx, name=sname):
                    if progress_callback:
                        progress_callback((base_idx + p) / max(1, total_shapes))

                top, nd = self.execute_analysis_for_date(limit_date, exclude_today, sub_params, sub_progress)
                if not next_draw_data_all and nd:
                    next_draw_data_all = nd
                for r in top:
                    rr = dict(r)
                    rr['shape_index'] = sidx
                    rr['shape_name'] = sname
                    combined_results.append(rr)

            combined_results.sort(key=lambda x: (x.get('streak', 0), x.get('three_star_count', 0), -x.get('M', 0)), reverse=True)
            result_top = [dict(r) for r in combined_results[:1000]]
            result_next = list(next_draw_data_all)
            self._analysis_last_profile = {
                'cache_hit': False,
                'result_count': len(result_top),
                'shape_all': True,
            }
            cache_store = getattr(self, '_analysis_result_cache', None)
            if cache_store is not None:
                if len(cache_store) > 24:
                    cache_store.clear()
                cache_store[cache_key] = {
                    'top': result_top,
                    'next': result_next,
                    'profile': dict(self._analysis_last_profile),
                }
            if progress_callback:
                progress_callback(1.0)
            return result_top, result_next

        t_total_start = time.perf_counter()

        def expand_tails(nums, max_v):
            expanded = set()
            tails = {abs(x) % 10 for x in nums}
            for v in range(1, max_v + 1):
                if v % 10 in tails:
                    expanded.add(v)
            return sorted(list(expanded))

        cache = getattr(self, '_analysis_cache', {}).get(self.lotto_type)
        dates = cache.get('dates') if cache else None
        processed_all = cache.get('processed_rows') if cache else None
        rows_all = cache.get('data') if cache else None
        occ_cache = cache.get('occurrence_indexes') if cache else None

        if dates and processed_all and rows_all:
            if exclude_today:
                end_idx = bisect_left(dates, limit_date) - 1
            else:
                end_idx = bisect_right(dates, limit_date) - 1

            if end_idx >= 0:
                full_valid_data = rows_all[:end_idx + 1]
                valid_data = processed_all[:end_idx + 1]
            else:
                full_valid_data = []
                valid_data = []
        else:
            if exclude_today:
                full_valid_data = [row for row in self.data if row[0] < limit_date]
            else:
                full_valid_data = [row for row in self.data if row[0] <= limit_date]
            valid_data = []
            for d, nums, sp in full_valid_data:
                l = nums[:]
                if params['has_special'] and sp is not None:
                    l.append(sp)
                s = set(l)
                valid_data.append({'date': d, 'list': l, 'set': s})
            dates = None
            rows_all = None
            occ_cache = None

        analysis_base_idx = 0
        data_limit_mode = params.get('data_limit_mode', 0)
        data_limit_count = ANALYSIS_DATA_LIMIT_OPTIONS.get(data_limit_mode, DATA_READ_LIMIT)
        # 2026-07 修正:原本 3連拖/4連拖(以及 mode 16)不管使用者選什麼資料筆數,
        # 一律強制使用「全部」資料。現在移除 3、4 的例外,改成跟其他模式一樣,
        # 正常讀取使用者在「資料筆數」設定的 20筆/51筆/231筆/全部。mode 16 維持原行為不動。
        if data_limit_count and params.get('analysis_mode', 0) not in [16]:
            if len(full_valid_data) > data_limit_count:
                original_len = len(full_valid_data)
                full_valid_data = full_valid_data[-data_limit_count:]
                valid_data = valid_data[-data_limit_count:]
                analysis_base_idx = original_len - len(full_valid_data)

        next_draw_data = []
        if full_valid_data:
            if dates:
                last_date = full_valid_data[-1][0]
                last_idx = bisect_right(dates, last_date) - 1
                if last_idx >= 0 and rows_all:
                    next_draw_data = rows_all[last_idx + 1:last_idx + 4]
            else:
                last_date = full_valid_data[-1][0]
                for row in self.data:
                    if row[0] > last_date:
                        next_draw_data.append(row)
                        if len(next_draw_data) >= 3:
                            break

        if params.get('analysis_mode') == 15 and full_valid_data:
            next_draw_data = []
            last_date = full_valid_data[-1][0]
            if dates and rows_all:
                last_idx = bisect_right(dates, last_date) - 1
                if last_idx >= 0:
                    next_draw_data = rows_all[last_idx + 1:last_idx + 22]
            else:
                for row in self.data:
                    if row[0] > last_date:
                        next_draw_data.append(row)
                        if len(next_draw_data) >= 21:
                            break

        processed_data = valid_data
        total_periods = len(processed_data)
        analysis_end_idx = total_periods - 1
        results_list =[]

        t_preprocess_end = time.perf_counter()

        analysis_mode = params.get('analysis_mode', 0)
        pred_range = params.get('pred_range', 0)
        max_val = params['max_val']
        if occ_cache and occ_cache[0] and occ_cache[1]:
            occ_set_map, occ_pos_maps = occ_cache
        else:
            occ_set_map, occ_pos_maps = _build_occurrence_indexes(processed_data, max_val)
            analysis_base_idx = 0

        t_occurrence_end = time.perf_counter()

        def _trim_occurrences(occurrences, t_limit=None):
            if not occurrences:
                return []
            limit = analysis_end_idx if t_limit is None else t_limit
            if limit < 0:
                return []
            limit_abs = analysis_base_idx + limit
            start_abs = analysis_base_idx
            if occurrences[0] > limit_abs or occurrences[-1] < start_abs:
                return []
            left = bisect_left(occurrences, start_abs)
            right = bisect_right(occurrences, limit_abs)
            if left == 0 and right == len(occurrences) and analysis_base_idx == 0:
                return occurrences
            return [idx - analysis_base_idx for idx in occurrences[left:right]]

        def get_occurrences_by_set(num, t_limit=None):
            occs = _trim_occurrences(occ_set_map.get(num, []), t_limit)
            try:
                return _limit_occurrences_for_combo(occs)
            except NameError:
                return occs

        def get_occurrences_by_pos(pos, num, t_limit=None):
            if 0 <= pos < len(occ_pos_maps):
                occs = _trim_occurrences(occ_pos_maps[pos].get(num, []), t_limit)
                try:
                    return _limit_occurrences_for_combo(occs)
                except NameError:
                    return occs
            return []

        def get_occurrences_for_candidate(x_val, px_val, y_val, py_val, z_val=None, pz_val=-1, t_limit=None):
            if px_val == -1:
                candidates = [get_occurrences_by_set(x_val), get_occurrences_by_set(y_val)]
                if z_val is not None:
                    candidates.append(get_occurrences_by_set(z_val))
            else:
                candidates = [get_occurrences_by_pos(px_val, x_val), get_occurrences_by_pos(py_val, y_val)]
                if z_val is not None:
                    candidates.append(get_occurrences_by_pos(pz_val, z_val))

            candidates = [c for c in candidates if c]
            if not candidates:
                return []

            base = min(candidates, key=len)
            result = set(base)
            for lst in candidates:
                if lst is base:
                    continue
                result.intersection_update(lst)
                if not result:
                    return []

            if t_limit is not None:
                result = {idx for idx in result if idx <= t_limit}
            occs = sorted(result)
            try:
                return _limit_occurrences_for_combo(occs)
            except NameError:
                return occs

        is_sum = params['is_sum']
        is_cyclic = params['is_cyclic']
        is_consec = params['is_consec']
        is_tail = params['is_tail']
        is_fixed_pos = params.get('is_fixed_pos', True)
        is_alternate = params.get('is_alternate', False)
        is_alternate_vip = params.get('is_alternate_vip', False)
        is_step_advance = params.get('is_step_advance', False)
        step_val = params.get('step_val', 0)
        is_tail_match = params.get('is_tail_match', False)
        is_tail_drag = params.get('is_tail_drag', False)
        is_non_hit = params.get('is_non_hit', False)
        pick_count = params['pick_count']
        min_hit_req = params['min_hit_req']
        shape_index = params.get('shape_index', 0)
        pillar_counts_for_guard = params.get('pillar_counts', [3, 3, 3, 0, 0])
        try:
            pillar_total_for_guard = sum(int(x or 0) for x in pillar_counts_for_guard)
        except Exception:
            pillar_total_for_guard = 0

        # 防閃退保護:選號數量 3 以上 + 一般加減完整組合,會讓 combinations 暴增。
        # 連號、尾號、尾數、取尾配頭本身會縮小候選,所以不啟動此保護。
        # 2026-06 修正:循環 + 選號數量 3 會在每個觸發點 / 位置 / N期重複掃 39選3、49選3,
        # 單次組合看似不大,但總工作量會讓 Pythonista 直接閃退,所以循環選3套用更嚴格的分批限量。
        combo_cycle_pick3_guard_active = (
            pick_count >= 3
            and is_cyclic
            and not is_consec
            and not is_tail
            and not is_tail_match
            and not is_tail_drag
            and not is_alternate
            and not is_alternate_vip
        )
        # 幾連拖防閃退:3連拖/4連拖在「選號數量 3」時,
        # 會在每個觸發序列裡反覆掃 39選3、49選3。
        # 單次組合不一定超大,但乘上序列與期數後會讓 Pythonista 記憶體/CPU 爆掉。
        combo_drag_chain_pick3_guard_active = (
            analysis_mode in (2, 3, 4)
            and pick_count >= 3
            and not is_tail_match
            and not is_alternate
            and not is_alternate_vip
        )
        # 大樂透/六合彩「定位合數加減」選號 2 以上也會爆量:
        # 49 號 + 6 正碼 + 特別號共 7 個位置,在每個觸發點/位置/N期反覆掃 49 選 2 等級的候選,
        # Pythonista 很容易被 iOS 直接殺掉。這裡提早啟用快篩,539/天天樂不受影響。
        combo_biglotto_mode0_pick2_guard_active = (
            analysis_mode == 0
            and self.lotto_type in (2, 3)
            and pick_count >= 2
            and not is_consec
            and not is_tail
            and not is_tail_match
            and not is_tail_drag
            and not is_alternate
            and not is_alternate_vip
        )
        # 立柱熱門快篩改成「只要是立柱熱門就能支援」:
        # 不再因為連號、尾號、尾數、取尾配頭、輪流等設定而整個關閉。
        # 這樣 1/2/3期內、2/3期到期、不同柱數設定,都會套用候選限量保護。
        combo_hot_pillar_guard_active = (
            analysis_mode == 9
            and pillar_total_for_guard > 0
        )
        if combo_hot_pillar_guard_active:
            combo_guard_active = True
        else:
            combo_guard_active = (
                combo_biglotto_mode0_pick2_guard_active
                or (
                    pick_count >= 3
                    and (analysis_mode in (0, 1, 7, 8, 12, 13, 14, 15, 16) or combo_cycle_pick3_guard_active or combo_drag_chain_pick3_guard_active)
                    and not is_consec
                    and not is_tail
                    and not is_tail_match
                    and not is_tail_drag
                    and not is_alternate
                    and not is_alternate_vip
                )
            )
        combo_guard_was_used = False

        if combo_hot_pillar_guard_active:
            # 立柱熱門一律支援快篩,但依柱數大小自動調整強度:
            # 小柱數保留較完整,大柱數才強力限量,避免 3+3+3 類設定爆量閃退。
            if pillar_total_for_guard >= 7:
                combo_source_limit = 900
                combo_candidate_limit = 220
                combo_occurrence_limit = 55
                combo_slot_limit = 900
            elif pillar_total_for_guard >= 5:
                combo_source_limit = 3000
                combo_candidate_limit = 800
                combo_occurrence_limit = 80
                combo_slot_limit = 1500
            else:
                combo_source_limit = 12000
                combo_candidate_limit = 2500
                combo_occurrence_limit = 0
                combo_slot_limit = 5000
        elif combo_drag_chain_pick3_guard_active:
            # 幾連拖選3專用:每個觸發序列只取近期/前段穩定候選,避免 3連拖點進去分析時閃退。
            combo_source_limit = 900
            combo_candidate_limit = 180
            combo_occurrence_limit = 70
            combo_slot_limit = 900
        elif combo_cycle_pick3_guard_active:
            # 循環選3專用:壓低每個小迴圈的候選量,避免多層巢狀迴圈累積爆掉。
            combo_source_limit = 1200
            combo_candidate_limit = 180
            combo_occurrence_limit = 70
            combo_slot_limit = 900
        elif combo_biglotto_mode0_pick2_guard_active:
            # 大樂透/六合彩定位合數加減選 2+ 專用:保留近期觸發與第一段命中候選,避免開始分析閃退。
            if pick_count == 2:
                combo_source_limit = 2500
                combo_candidate_limit = 320
                combo_occurrence_limit = 48
                combo_slot_limit = 900
            else:
                combo_source_limit = 1400
                combo_candidate_limit = 220
                combo_occurrence_limit = 42
                combo_slot_limit = 700
        else:
            combo_source_limit = 12000
            combo_candidate_limit = 2500
            combo_occurrence_limit = 0
            combo_slot_limit = 5000

        def _limit_occurrences_for_combo(occs):
            nonlocal combo_guard_was_used
            if not combo_occurrence_limit or not occs:
                return occs
            if len(occs) > combo_occurrence_limit:
                combo_guard_was_used = True
                return occs[-combo_occurrence_limit:]
            return occs

        def _guard_candidate_c_lists(seq, limit=None):
            nonlocal combo_guard_was_used
            if not combo_guard_active:
                return seq
            if seq is None:
                return []
            if limit is None:
                limit = combo_candidate_limit
            try:
                if len(seq) <= limit:
                    return seq
                combo_guard_was_used = True
                return list(seq[:limit])
            except TypeError:
                combo_guard_was_used = True
                return list(islice(seq, limit))

        def _prune_results_for_biglotto_guard(force=False):
            """大樂透/六合彩定位合數加減防閃退:搜尋中定期只保留較好的候選。"""
            nonlocal results_list, combo_guard_was_used
            if not combo_biglotto_mode0_pick2_guard_active:
                return
            prune_trigger = 7000
            keep_limit = 3000
            if (not force) and len(results_list) <= prune_trigger:
                return
            if len(results_list) <= keep_limit:
                return
            combo_guard_was_used = True
            results_list.sort(
                key=lambda x: (
                    x.get('streak', 0),
                    1 if x.get('weekly_double_core') else 0,
                    x.get('three_star_count', 0)
                ),
                reverse=True
            )
            del results_list[keep_limit:]

        min_streak_input = params['min_streak']

        effective_min_streak = min_streak_input if min_streak_input > 0 else 1

        max_n = params['max_n']
        balls_cnt = params['balls_cnt']
        lock_special = bool(params.get('lock_special', False) and params.get('has_special', False) and self.lotto_type in (2, 3))
        special_pos = balls_cnt
        # 特殊天地碰模式:六合彩/大樂透鎖定特別號/第7隻,且選 2星以上、1星關閉時自動啟動。
        # 必須「特別號中」+「正碼/裡面號碼也中」才算達標。
        # 星數 = 特別號 1 星 + 正碼命中數。
        special_tiandi_mode = bool(params.get('special_tiandi_mode', False) or (lock_special and int(min_hit_req or 1) >= 2 and not is_tail_match and not is_tail_drag and not is_non_hit))

        def _split_special_item(item):
            lst = list(item.get('list') or [])
            inner_set = set(lst[:special_pos]) if len(lst) >= special_pos else set(item.get('set') or set())
            sp_val = lst[special_pos] if len(lst) > special_pos else None
            return inner_set, sp_val

        def _target_item_set(item):
            if lock_special:
                lst = item.get('list') or []
                if special_tiandi_mode:
                    # 2/3/4星特殊天地碰要同時看正碼與特別號,後面再檢查「特別號必須中」。
                    return set(item.get('set') or set(lst))
                if len(lst) > special_pos:
                    return {lst[special_pos]}
                return set()
            return set(item.get('set') or set())

        def _special_tiandi_window(t_idx, M):
            if not special_tiandi_mode:
                return None
            target_idx = t_idx + M
            if target_idx >= total_periods:
                return None
            idxs = [target_idx]
            if pred_range in [1, 3] and target_idx + 1 < total_periods:
                idxs.append(target_idx + 1)
            elif pred_range in [2, 4]:
                if target_idx + 1 < total_periods:
                    idxs.append(target_idx + 1)
                if target_idx + 2 < total_periods:
                    idxs.append(target_idx + 2)

            # 天地碰不能把「不同期」混在一起湊星。
            # 例如:第一期只中正碼、第二期只中特別號,不能算天2。
            # 所以這裡保留每一期自己的 (正碼集合, 特別號集合),後面逐期判定。
            windows = []
            for idx in idxs:
                inner_set, sp_val = _split_special_item(processed_data[idx])
                special_set = {sp_val} if sp_val is not None else set()
                windows.append((set(inner_set), special_set))
            return windows

        def _special_tiandi_window_parts(window):
            if not window:
                return []
            # 相容舊格式:(inner_set, special_set)
            if isinstance(window, tuple) and len(window) == 2:
                return [(set(window[0] or set()), set(window[1] or set()))]
            parts = []
            for entry in window:
                if isinstance(entry, tuple) and len(entry) == 2:
                    parts.append((set(entry[0] or set()), set(entry[1] or set())))
            return parts

        def _special_tiandi_window_union(window):
            inner_all = set()
            special_all = set()
            for inner_set, special_set in _special_tiandi_window_parts(window):
                inner_all.update(inner_set)
                special_all.update(special_set)
            return inner_all, special_all

        def _special_tiandi_success_for_sets(pred_values, inner_set, special_set):
            pred_set = set(pred_values or [])
            special_hits = pred_set & set(special_set or set())
            inner_hits = pred_set & set(inner_set or set())
            need_inner = max(1, int(min_hit_req or 1) - 1)
            ok = bool(special_hits) and len(inner_hits) >= need_inner
            hit_values = sorted(special_hits | inner_hits)
            return ok, hit_values

        def _special_tiandi_success_for_item(pred_values, item):
            inner_set, sp_val = _split_special_item(item)
            special_set = {sp_val} if sp_val is not None else set()
            return _special_tiandi_success_for_sets(pred_values, inner_set, special_set)

        def _special_tiandi_success_for_window(pred_values, window):
            combined_hits = set()
            for inner_set, special_set in _special_tiandi_window_parts(window):
                ok, hits = _special_tiandi_success_for_sets(pred_values, inner_set, special_set)
                if ok:
                    return True, hits
                combined_hits.update(hits)
            return False, sorted(combined_hits)

        def _special_tiandi_c_value(base, target_num):
            if is_sum:
                c = base + target_num
                if is_cyclic:
                    c = (c - 1) % max_val + 1
            else:
                c = target_num - base
                if is_cyclic:
                    c = c % max_val
                    if c <= 0:
                        c += max_val
            return c

        def _special_tiandi_c_window(base, window):
            c_windows = []
            for inner_set, special_set in _special_tiandi_window_parts(window):
                c_windows.append({
                    'inner': {_special_tiandi_c_value(base, n) for n in inner_set},
                    'special': {_special_tiandi_c_value(base, n) for n in special_set},
                })
            return c_windows

        def _special_tiandi_c_window_with_step(base, window, step_offset=0):
            # 週牌/同棟2號的「步步進擊」會把歷史 C 值正規化回候選 c_tuple 空間。
            # 天地碰也必須同樣處理,否則只會看裡面號碼,漏掉「特別號必須中」。
            cwins = _special_tiandi_c_window(base, window)
            try:
                off = int(step_offset or 0)
            except Exception:
                off = 0
            if off:
                stepped = []
                for cwin in cwins:
                    stepped.append({
                        'inner': {c + off for c in cwin.get('inner', set())},
                        'special': {c + off for c in cwin.get('special', set())},
                    })
                return stepped
            return cwins

        def _special_tiandi_c_window_parts(c_window):
            if not c_window:
                return []
            if isinstance(c_window, dict):
                return [c_window]
            parts = []
            for entry in c_window:
                if isinstance(entry, dict):
                    parts.append(entry)
            return parts

        def _special_tiandi_success_for_c_tuple(c_tuple, c_window):
            combined_hits = set()
            c_set = set(c_tuple or [])
            need_inner = max(1, int(min_hit_req or 1) - 1)
            for part in _special_tiandi_c_window_parts(c_window):
                special_hits = c_set & set(part.get('special', set()))
                inner_hits = c_set & set(part.get('inner', set()))
                hits = special_hits | inner_hits
                if bool(special_hits) and len(inner_hits) >= need_inner:
                    return True, sorted(hits)
                combined_hits.update(hits)
            return False, sorted(combined_hits)

        target_set_cache = {}

        def helper_get_target_set(t_idx, M):
            key = (t_idx, M)
            if key in target_set_cache:
                return target_set_cache[key]

            target_idx = t_idx + M
            if target_idx >= total_periods:
                target_set_cache[key] = None
                return None

            t_set = _target_item_set(processed_data[target_idx])
            if pred_range in[1, 3]:
                if target_idx + 1 < total_periods: t_set.update(_target_item_set(processed_data[target_idx + 1]))
            elif pred_range in[2, 4]:
                if target_idx + 1 < total_periods: t_set.update(_target_item_set(processed_data[target_idx + 1]))
                if target_idx + 2 < total_periods: t_set.update(_target_item_set(processed_data[target_idx + 2]))
            target_set_cache[key] = t_set
            return t_set

        last_set = _target_item_set(processed_data[-1]) if processed_data else set()
        last2_set = _target_item_set(processed_data[-2]) if len(processed_data) > 1 else set()

        def verify_miss(p_nums):
            # 立柱熱門共用熱門拖牌核心時,到期早中檢查不能用熱門拖牌的 hit count,
            # 要交給立柱自己的「同一天幾柱達標」重算,否則 3期到期會被錯誤濾光。
            if params.get('pillar_hot_candidate_only', False):
                return True
            if pred_range not in[3, 4]: return True
            if special_tiandi_mode:
                # 特殊天地碰到期模式:前面期數若已經「特別號+正碼」達標,才算提前中。
                if pred_range == 3:
                    if processed_data:
                        ok, _ = _special_tiandi_success_for_item(p_nums, processed_data[-1])
                        if ok:
                            return False
                elif pred_range == 4:
                    if len(processed_data) > 1:
                        ok1, _ = _special_tiandi_success_for_item(p_nums, processed_data[-2])
                        if ok1:
                            return False
                    if processed_data:
                        ok2, _ = _special_tiandi_success_for_item(p_nums, processed_data[-1])
                        if ok2:
                            return False
                return True
            if pred_range == 3:
                if is_tail_match:
                    pt = {x % 10 for x in p_nums}
                    tt = {x % 10 for x in last_set}
                    hits_val = len(pt & tt)
                else:
                    hits_val = sum(1 for n in p_nums if n in last_set)

                if (hits_val > 0) if is_non_hit else (hits_val >= min_hit_req): return False
            elif pred_range == 4:
                if is_tail_match:
                    pt = {x % 10 for x in p_nums}
                    tt1 = {x % 10 for x in last2_set}
                    tt2 = {x % 10 for x in last_set}
                    hits_val1 = len(pt & tt1)
                    hits_val2 = len(pt & tt2)
                else:
                    hits_val1 = sum(1 for n in p_nums if n in last2_set)
                    hits_val2 = sum(1 for n in p_nums if n in last_set)

                if (hits_val1 > 0) if is_non_hit else (hits_val1 >= min_hit_req): return False
                if (hits_val2 > 0) if is_non_hit else (hits_val2 >= min_hit_req): return False
            return True

        def _make_candidate_c_lists_for_history(c_pool, first_h_cs=None):
            """建立選號候選組合,並在高風險模式下分批限量,避免反覆 list(combinations()) 閃退。"""
            nonlocal combo_guard_was_used
            if not c_pool:
                return []

            c_pool_list = list(c_pool)

            # 大樂透/六合彩定位合數加減選 2+ 的重點修正:
            # 不再每個位置都先展開完整 combinations 再過濾,改用第一段命中集合直接生成候選。
            # 這樣「選號數量=2」也會套用快篩,避免開始分析時記憶體/CPU 暴衝。
            if combo_guard_active and first_h_cs is not None and not special_tiandi_mode:
                combo_guard_was_used = True
                first_set = set(first_h_cs or set())
                cand_set = set()

                if is_non_hit:
                    safe_pool = [c for c in c_pool_list if c not in first_set]
                    for tup in islice(combinations(safe_pool, pick_count), combo_candidate_limit):
                        cand_set.add(tuple(sorted(tup)))
                    return list(cand_set)

                hit_pool = [c for c in c_pool_list if c in first_set]
                if not hit_pool:
                    return []

                min_h = max(1, min(int(min_hit_req or 1), pick_count, len(hit_pool)))
                max_h = min(pick_count, len(hit_pool))
                add_cap = combo_candidate_limit

                for h_cnt in range(min_h, max_h + 1):
                    for hit_part in combinations(hit_pool, h_cnt):
                        need = pick_count - h_cnt
                        fill_pool = [c for c in c_pool_list if c not in hit_part]
                        if need < 0 or len(fill_pool) < need:
                            continue
                        fill_iter = combinations(fill_pool, need) if need else [()]
                        for fill_part in fill_iter:
                            tup = tuple(sorted(hit_part + fill_part))
                            cand_set.add(tup)
                            if len(cand_set) >= add_cap:
                                return list(cand_set)

                return list(cand_set)

            combo_iter = combinations(c_pool_list, pick_count)
            if combo_guard_active:
                combo_guard_was_used = True
                combo_iter = islice(combo_iter, combo_source_limit)

            if first_h_cs is None:
                cand_c_lists = list(combo_iter)
            else:
                cand_c_lists = []
                for tup in combo_iter:
                    if special_tiandi_mode:
                        ok, _ = _special_tiandi_success_for_window(tup, first_h_cs)
                        if ok:
                            cand_c_lists.append(tup)
                    else:
                        hits_val = sum(1 for c in tup if c in first_h_cs)
                        if is_non_hit:
                            if hits_val == 0:
                                cand_c_lists.append(tup)
                        else:
                            if hits_val >= min_hit_req:
                                cand_c_lists.append(tup)
                    if combo_guard_active and len(cand_c_lists) >= combo_candidate_limit:
                        combo_guard_was_used = True
                        break

            return _guard_candidate_c_lists(cand_c_lists)

        def _mode9_current_range_status(latest_occ, M, pillars):
            """立柱熱門專用:2/3期內允許部分開獎先命中,未開完不算斷莊;到期只認到期格。"""
            try:
                pr = int(pred_range)
            except Exception:
                pr = 0

            base_idx = latest_occ + M
            if pr == 0:
                hit_offsets = [0]
                miss_offsets = []
            elif pr == 1:
                hit_offsets = [0, 1]
                miss_offsets = []
            elif pr == 2:
                hit_offsets = [0, 1, 2]
                miss_offsets = []
            elif pr == 3:
                hit_offsets = [1]
                miss_offsets = [0]
            elif pr == 4:
                hit_offsets = [2]
                miss_offsets = [0, 1]
            else:
                hit_offsets = [0]
                miss_offsets = []

            def _stars_at_idx(idx):
                if idx < 0 or idx >= total_periods:
                    return None
                t_set_now = _target_item_set(processed_data[idx])
                stars_now = 0
                for one_pillar in pillars:
                    if one_pillar and any(num in t_set_now for num in one_pillar):
                        stars_now += 1
                return stars_now

            # 到期模式:前面已開獎若已達到「中幾柱」門檻,才算提前中而斷莊。
            for off in miss_offsets:
                stars_miss = _stars_at_idx(base_idx + off)
                if stars_miss is None:
                    return False, 0, False
                early_success = (stars_miss == 0) if is_non_hit else (stars_miss >= min_hit_req)
                if early_success:
                    return False, 0, True

            resolved_any = False
            hit_found = False
            best_stars = 0
            fully_expired = True

            for off in hit_offsets:
                stars_now = _stars_at_idx(base_idx + off)
                if stars_now is None:
                    fully_expired = False
                    continue
                resolved_any = True
                success_now = (stars_now == 0) if is_non_hit else (stars_now >= min_hit_req)
                if success_now:
                    hit_found = True
                    if stars_now > best_stars:
                        best_stars = stars_now
                    break

            # 2期內/3期內:必須目前已開出的區間已經命中,才算「目前連續命中」。
            # 如果第1格已開但還沒中,不能先當成連莊版路輸出;等第2/3格真的中再出現。
            if pr in (1, 2):
                current_failed = not hit_found
            else:
                current_failed = resolved_any and (not hit_found) and fully_expired
            return hit_found, best_stars, current_failed

        def _mode10_build_pillars(items, counts, sequential=False):
            pillars = [[] for _ in range(len(counts))]
            if sequential:
                pos = 0
                for i, cnt in enumerate(counts):
                    if cnt <= 0:
                        continue
                    pillars[i] = list(items[pos:pos + cnt])
                    pos += cnt
            else:
                needed = list(counts)
                for num in items:
                    best_p = -1
                    max_n = -1
                    for i, n in enumerate(needed):
                        if n > max_n:
                            max_n = n
                            best_p = i
                    if best_p != -1:
                        pillars[best_p].append(num)
                        needed[best_p] -= 1
            return pillars

        if analysis_mode == 16:
            # 日期版路:以「每個月份的第 N 次開獎」為一個區塊。
            # 例如輸入 5/6/7,就用每個月第5、6、7期的集合去驗證;本月第5、6、7期作為目前使用區塊。
            raw_periods = params.get('date_route_periods', []) or []
            date_periods = []
            for p in raw_periods:
                try:
                    v = int(str(p).strip())
                except Exception:
                    continue
                if v > 0 and v not in date_periods:
                    date_periods.append(v)
            date_periods = sorted(date_periods)
            if not date_periods:
                return [], next_draw_data

            pillar_counts = params.get('pillar_counts', [3, 0, 0, 0, 0])
            try:
                pillar_counts = [max(0, int(x or 0)) for x in pillar_counts]
            except Exception:
                pillar_counts = [3, 0, 0, 0, 0]
            k_total = sum(pillar_counts)
            if k_total <= 0:
                return [], next_draw_data

            month_blocks = {}
            month_order = []
            current_key = None
            current_ord = 0
            for item in processed_data:
                d = item['date']
                key = (d.year, d.month)
                if key != current_key:
                    current_key = key
                    current_ord = 1
                    month_order.append(key)
                    month_blocks[key] = []
                else:
                    current_ord += 1
                if current_ord in date_periods:
                    month_blocks[key].append({'date': d, 'set': item['set'], 'list': item['list'], 'ord': current_ord, 'is_future': False})

            if not month_order:
                return [], next_draw_data

            # 修復:當「目前查看日期」(limit_date) 已跨入新的月份,但該月份
            # 尚未有任何一期實際開獎資料時(例如每月1號、或該月第一次開獎前),
            # processed_data 裡最後一筆歷史資料仍停留在「上個月」,若直接把
            # month_order[-1](上個月)當成目前月份,會導致指定期數的預測藍色
            # 誤畫在上個月份的格子上。這裡改成:一律以 limit_date 所在月份
            # 作為「目前月份」,若該月份還沒有任何資料則補一個空區塊,
            # 讓後面的「本月未來期數」補算邏輯能正確地從新月份的第1期算起。
            limit_key = (limit_date.year, limit_date.month)
            if not month_order or month_order[-1] != limit_key:
                month_order.append(limit_key)
                month_blocks.setdefault(limit_key, [])

            target_key = month_order[-1]
            target_month_issue_count = 0
            for item in processed_data:
                d = item['date']
                if (d.year, d.month) == target_key:
                    target_month_issue_count += 1

            blocks = {}
            target_idx_in_order = len(month_order) - 1
            for mi, key in enumerate(month_order):
                b_id = target_idx_in_order - mi
                selected_items = list(month_blocks.get(key, []))
                if selected_items:
                    blocks[b_id] = selected_items

            if not blocks:
                return [], next_draw_data

            # 盡量補出本月指定期數的未來日期,只作為說明/圖表目標日期,不參與歷史命中驗證。
            target_block_dates = [x['date'] for x in blocks.get(0, [])]
            if processed_data:
                try:
                    last_known_date = processed_data[-1]['date']
                    known_count = target_month_issue_count
                    d_future = last_known_date
                    future_guard = 0
                    while known_count < max(date_periods) and future_guard < 80:
                        d_future = self.next_draw_date(d_future)
                        future_guard += 1
                        if (d_future.year, d_future.month) != target_key:
                            break
                        known_count += 1
                        if known_count in date_periods:
                            target_block_dates.append(d_future)
                except Exception:
                    pass
            target_block_dates = sorted(set(target_block_dates))

            # 顯示用:歷史驗證區塊=每個月指定期數(不含本月),
            # 預測區塊=本月指定期數(已開+未開)。
            validation_blocks = []
            for b_id in sorted([bid for bid in blocks.keys() if bid > 0], reverse=True):
                b_dates = [x['date'] for x in blocks.get(b_id, [])]
                if b_dates:
                    validation_blocks.append(sorted(b_dates))


            if is_tail_match:
                domain_elements = list(range(10))
            else:
                domain_elements = list(range(1, max_val + 1))

            if is_consec:
                cand_c_lists = []
                active_pillar_counts = [cnt for cnt in pillar_counts if cnt > 0]

                def _build_date_consec(idx, min_start, current):
                    if idx >= len(active_pillar_counts):
                        cand_c_lists.append(tuple(current))
                        return
                    cnt = active_pillar_counts[idx]
                    max_start = len(domain_elements) - cnt
                    for s_idx in range(min_start, max_start + 1):
                        block = domain_elements[s_idx:s_idx + cnt]
                        if len(block) < cnt:
                            break
                        ok_seq = True
                        for j in range(len(block) - 1):
                            if block[j + 1] - block[j] != 1:
                                ok_seq = False
                                break
                        if ok_seq:
                            _build_date_consec(idx + 1, s_idx + cnt, current + block)

                _build_date_consec(0, 0, [])
                cand_c_lists = list(set(cand_c_lists))
            else:
                freq = Counter()
                recent_freq = Counter()
                for b_id, items in blocks.items():
                    if b_id <= 0:
                        continue
                    for x in items:
                        for num in x.get('set', set()):
                            key_num = num % 10 if is_tail_match else num
                            freq[key_num] += 1
                            if b_id <= 18:
                                recent_freq[key_num] += (20 - b_id)

                if not freq:
                    return [], next_draw_data

                # 日期版路深層分析:
                # 舊版只取前 24 個熱門號再被 combo_guard 截前 2500 組,容易漏掉最高準度組合。
                # 這裡改成:熱門池 + 近期加權池 + 固定亂數深搜 + 快速評分排序。
                # 目標是比原本更容易找到最高準度版路,同時避免一次展開 39C9 爆量。
                date_route_deep_keep_limit = 80000 if k_total <= 9 else 50000
                date_route_random_sample_limit = 90000 if k_total <= 9 else 55000
                cand_set = set()

                weighted_counter = Counter()
                weighted_counter.update(freq)
                weighted_counter.update(recent_freq)

                if is_tail_match:
                    pool_size = min(len(weighted_counter), 10)
                else:
                    pool_size = min(len(weighted_counter), max(24, min(max_val, k_total + 26)))
                deep_pool = [num for num, count in weighted_counter.most_common(pool_size)]

                def _add_limited_combinations(pool, limit):
                    added = 0
                    if len(pool) < k_total:
                        return
                    for tup in combinations(pool, k_total):
                        cand_set.add(tuple(sorted(tup)))
                        added += 1
                        if added >= limit:
                            break

                # 先完整跑較小熱門池,避免 lexicographic 前幾組偏掉。
                if k_total <= 3:
                    small_pool_size = min(len(deep_pool), 30)
                    small_combo_limit = 60000
                elif k_total <= 6:
                    small_pool_size = min(len(deep_pool), 22)
                    small_combo_limit = 90000
                else:
                    small_pool_size = min(len(deep_pool), 18)
                    small_combo_limit = 90000
                _add_limited_combinations(deep_pool[:small_pool_size], small_combo_limit)

                # 近期加權池再補一輪。
                recent_pool = [num for num, count in recent_freq.most_common(min(len(recent_freq), max(k_total + 12, 18)))]
                _add_limited_combinations(recent_pool, 45000)

                # 從各月份指定期數出現的號碼補種子,增加找到非總熱門但連莊強的組合機率。
                month_seed_pool = []
                for b_id in range(1, min(13, max(blocks.keys()) + 1)):
                    month_nums = []
                    for x in blocks.get(b_id, []):
                        for num in x.get('set', set()):
                            month_nums.append(num % 10 if is_tail_match else num)
                    if month_nums:
                        month_seed_pool.extend([n for n, c in Counter(month_nums).most_common()])
                merged_seed = []
                for n in month_seed_pool + deep_pool:
                    if n not in merged_seed:
                        merged_seed.append(n)
                _add_limited_combinations(merged_seed[:min(len(merged_seed), max(k_total + 10, 20))], 45000)

                # 固定種子的亂數深搜:每次一樣結果,不會飄。
                try:
                    _rnd = __import__('random').Random(5391600 + k_total * 17 + sum(date_periods) * 31 + int(min_hit_req or 1))
                    if len(deep_pool) >= k_total:
                        sample_guard = 0
                        while len(cand_set) < date_route_deep_keep_limit * 2 and sample_guard < date_route_random_sample_limit:
                            sample_guard += 1
                            # 70% 從深池抽,30% 混入完整 domain,避免被熱門池限制住。
                            if (not is_tail_match) and sample_guard % 10 in (0, 3, 7):
                                pool = list(domain_elements)
                            else:
                                pool = deep_pool
                            if len(pool) >= k_total:
                                cand_set.add(tuple(sorted(_rnd.sample(pool, k_total))))
                except Exception:
                    pass

                def _quick_one_draw_stars(pillars_tmp, draw_item):
                    draw_nums = draw_item.get('set', set())
                    if is_tail_match:
                        draw_keys = {int(n) % 10 for n in draw_nums}
                        return sum(1 for p in pillars_tmp if p and ({int(v) % 10 for v in p} & draw_keys))
                    else:
                        return sum(1 for p in pillars_tmp if p and any(num in draw_nums for num in p))

                def _quick_score_tuple(tup):
                    pillars_tmp = _mode10_build_pillars(tuple(sorted(tup)), pillar_counts, sequential=False)
                    streak_s = 0
                    three_s = 0
                    star_sum = 0
                    curr_s = 1
                    while curr_s in blocks:
                        best_s = 0
                        for x in blocks.get(curr_s, []):
                            st = _quick_one_draw_stars(pillars_tmp, x)
                            if st > best_s:
                                best_s = st
                        ok = (best_s == 0) if is_non_hit else (best_s >= min_hit_req)
                        if not ok:
                            break
                        streak_s += 1
                        star_sum += best_s
                        if best_s >= 3 and not is_non_hit:
                            three_s += 1
                        curr_s += 1
                    hot_score = sum(weighted_counter.get(n, 0) for n in tup)
                    return (streak_s, three_s, star_sum, hot_score)

                # 排序保留深層候選,後面仍會用正式邏輯精算。
                if len(cand_set) > date_route_deep_keep_limit:
                    scored_cands = []
                    for tup in cand_set:
                        scored_cands.append((_quick_score_tuple(tup), tup))
                    scored_cands.sort(key=lambda x: x[0], reverse=True)
                    cand_c_lists = [tup for score, tup in scored_cands[:date_route_deep_keep_limit]]
                    combo_guard_was_used = True
                else:
                    cand_c_lists = list(cand_set)

                cand_c_lists = list(set(cand_c_lists))
            cand_c_lists = _guard_candidate_c_lists(cand_c_lists, limit=(80000 if analysis_mode == 16 else None))

            def _date_one_draw_star_count(pillars, draw_item):
                """日期版路星數必須同一期計算,不可把 8/9/10 期分開命中加總。"""
                if not draw_item:
                    return 0
                draw_nums = draw_item.get('set', set())
                stars = 0
                if is_tail_match:
                    draw_tails = {int(n) % 10 for n in draw_nums}
                    for p in pillars:
                        p_tails = {int(v) % 10 for v in p}
                        if p_tails and (p_tails & draw_tails):
                            stars += 1
                else:
                    for p in pillars:
                        if p and any(num in draw_nums for num in p):
                            stars += 1
                return stars

            def _date_block_star_count(pillars, block_items):
                """
                日期版路:例如指定 8.9.10 期、立柱 333、選 3星,
                必須是 8/9/10 其中同一期命中 3 柱才算 3星達標。
                不可以第8期中1柱、第9期中1柱、第10期中1柱加總成3星。
                """
                if not block_items:
                    return 0, None
                best_stars = -1
                best_date = None
                for x in block_items:
                    stars = _date_one_draw_star_count(pillars, x)
                    if stars > best_stars:
                        best_stars = stars
                        best_date = x.get('date')
                return max(0, best_stars), best_date

            def _date_success(stars):
                return (stars == 0) if is_non_hit else (stars >= min_hit_req)

            total_cand = max(1, len(cand_c_lists))
            for idx_c, c_tuple in enumerate(cand_c_lists):
                if idx_c % 200 == 0 or idx_c + 1 == total_cand:
                    if not self.is_analyzing:
                        raise InterruptedError()
                    if progress_callback:
                        progress_callback(min(0.99, (idx_c + 1) / float(total_cand)))

                pillars = _mode10_build_pillars(tuple(sorted(c_tuple)), pillar_counts, sequential=is_consec)

                streak = 0
                three_star_count = 0
                trigger_dates = []
                hit_blocks = []
                curr_b = 1
                while curr_b in blocks:
                    hist_items = blocks.get(curr_b, [])
                    stars, same_draw_hit_date = _date_block_star_count(pillars, hist_items)
                    if _date_success(stars):
                        streak += 1
                        if stars >= 3 and not is_non_hit:
                            three_star_count += 1
                        if hist_items:
                            trigger_dates.append(same_draw_hit_date or hist_items[-1]['date'])
                            hit_blocks.append([x['date'] for x in hist_items])
                        curr_b += 1
                    else:
                        break

                if streak < effective_min_streak:
                    continue
                if min_streak_input == 0 and streak <= 1:
                    continue

                latest_pred_nums = list(tuple(sorted(c_tuple)))
                results_list.append({
                    'mode': 16,
                    'pred_range': pred_range,
                    'streak': streak,
                    'three_star_count': three_star_count,
                    'M': 1,
                    'C_list': tuple(sorted(c_tuple)),
                    'pillars': pillars,
                    'max_val': max_val,
                    'min_hit_req': min_hit_req,
                    'sum_mode': False,
                    'cyclic': False,
                    'ref_dir': 0,
                    'latest_occ': total_periods - 1,
                    'latest_pred_nums': latest_pred_nums,
                    'trigger_dates': trigger_dates[::-1],
                    'hit_blocks': hit_blocks[::-1],
                    'validation_blocks': validation_blocks,
                    'target_block_dates': target_block_dates,
                    'date_route_periods': list(date_periods),
                    'current_month_issue_count': target_month_issue_count,
                    'is_tail_match': is_tail_match,
                    'is_consec': is_consec,
                    'is_non_hit': is_non_hit,
                })

        valid_c_lists =[]
        if analysis_mode == 8:
            c_pool = list(range(balls_cnt + (1 if params['has_special'] else 0)))
            combo_iter = combinations(c_pool, pick_count)
            if combo_guard_active:
                combo_guard_was_used = True
                valid_c_lists = list(islice(combo_iter, combo_source_limit))
            else:
                valid_c_lists = list(combo_iter)
        elif analysis_mode in[0, 7, 12, 13, 14]:
            if is_tail_drag:
                max_head = max_val // 10
                heads_pool = list(range(max_head + 1))
                valid_c_lists =[]
                for c in range(10):
                    for heads in combinations(heads_pool, pick_count):
                        valid_c_lists.append((c,) + heads)
            elif is_tail_match:
                if is_sum:
                    c_pool = list(range(0, 10))
                else:
                    c_pool = list(range(-9, 10))
            else:
                if is_sum:
                    if is_cyclic:
                        c_pool = list(range(1, max_val + 1))
                    else:
                        if analysis_mode in[12, 13]:
                            c_pool = list(range(2, max_val * 4 + 1))
                        elif analysis_mode == 14:
                            c_pool = list(range(1, max_val * 2 + 1))
                        else:
                            c_pool = list(range(2, max_val * 2 + 1))
                else:
                    if is_cyclic:
                        c_pool = list(range(1, max_val))
                    else:
                        c_pool = list(range(-max_val + 1, max_val))
                        if analysis_mode != 14 and 0 in c_pool:
                            c_pool.remove(0)

            if (not is_tail_drag) and is_tail and (not is_tail_match):
                # 尾號模式要支援 +19+49 / +9+39 這類以最大球號作為 C 值的同尾組合。
                # 原本一般非循環加減只到 max_val-1, 這裡只在尾號模式補齊。
                if max_val not in c_pool:
                    c_pool.append(max_val)
                if any(c < 0 for c in c_pool) and -max_val not in c_pool:
                    c_pool.append(-max_val)
                c_pool = sorted(set(c_pool))

            if not is_tail_drag:
                if is_consec:
                    c_pool.sort()
                    for i in range(len(c_pool) - pick_count + 1):
                        sub = c_pool[i:i+pick_count]
                        if all(sub[j+1] - sub[j] == 1 for j in range(len(sub)-1)):
                            valid_c_lists.append(tuple(sub))
                elif is_tail:
                    # 尾號模式改成「同尾全支援」邏輯。
                    # 同尾且同方向都保留,可支援 +11+21、+19+39、+11+41、+19+49 等距離。
                    # 避免混出 -11+41 這種正負混搭。
                    for t in range(10):
                        same_tail_cs = [c for c in c_pool if abs(c) % 10 == t]
                        if len(same_tail_cs) >= pick_count:
                            for combo in combinations(same_tail_cs, pick_count):
                                if not (all(c > 0 for c in combo) or all(c < 0 for c in combo)):
                                    continue
                                valid_c_lists.append(combo)
                else:
                    combo_iter = combinations(c_pool, pick_count)
                    if combo_guard_active:
                        combo_guard_was_used = True
                        valid_c_lists = list(islice(combo_iter, combo_source_limit))
                    else:
                        valid_c_lists = list(combo_iter)


        if analysis_mode == 15:
            weekdays = list(params.get('weekdays', []))
            if not weekdays:
                weekdays = sorted({item['date'].weekday() for item in processed_data})
            weekdays = [w for w in weekdays if isinstance(w, int) and 0 <= w <= 6]
            if not weekdays:
                return [], next_draw_data

            # 星期加減合數:選週幾只決定「目標驗證日」。
            # 例:選週五,每一次目標都是週五本期開出;參考資料不是前幾個週五,
            # 而是這個週五往上數的最近 5 個開獎期:週四、週三、週二、週一、週六。
            # 選號數量 N = 在「上 5 期」中固定抓 N 個「期數+位置」,
            # 每個位置各自加減/合數,算出號碼後直接驗證該期週五是否開出。
            max_ref_back = 5
            max_pos = balls_cnt + (1 if params['has_special'] else 0)
            week_pick_count = max(1, int(pick_count or 1))
            week_pick_count = min(week_pick_count, 4, max_ref_back * max(1, max_pos))

            # 星期加減合數的歷史驗證固定是「本期指定星期」;預測範圍只保留 UI 標籤與不出過濾用途,
            # 不再把命中延伸到下一個同星期。
            pred_span = 1

            step_values = [1, -1, 10, -10] if is_step_advance else [0]
            seen_week_keys = set()

            def weekday_target_set_global(target_idx):
                if 0 <= target_idx < len(processed_data):
                    return set(_target_item_set(processed_data[target_idx]))
                return set()

            def calc_week_refs_global(target_idx, slot_combo):
                bases = []
                ref_indexes = []
                for off, pos in slot_combo:
                    r_idx = target_idx - off
                    # target_idx 可以是未來空白列;但參考列一定要已經開獎,不能吃未來空白資料。
                    if r_idx < 0 or r_idx >= len(processed_data):
                        return None
                    row_list = processed_data[r_idx].get('list') or []
                    if pos >= len(row_list):
                        return None
                    bases.append(row_list[pos])
                    ref_indexes.append(r_idx)
                return bases, ref_indexes

            def next_selected_weekday_virtual_index(wd):
                if not processed_data:
                    return None, None
                last_date = processed_data[-1]['date']
                probe = last_date
                steps = 0
                # 539/大樂透/六合彩的 next_draw_date 會跳過非開獎日。
                while steps < 28:
                    probe = self.next_draw_date(probe)
                    steps += 1
                    if probe.weekday() == wd:
                        return len(processed_data) + steps - 1, probe
                return None, None

            def _tail_drag_entry_parts(entry):
                """星期加減合數取尾配頭:每個固定位置各自保存 (尾差, 頭數)。"""
                if isinstance(entry, (tuple, list)) and len(entry) >= 2:
                    try:
                        return int(entry[0]), int(entry[1])
                    except Exception:
                        return 0, 0
                try:
                    return int(entry), 0
                except Exception:
                    return 0, 0

            def _tail_drag_tail_c(entry):
                return _tail_drag_entry_parts(entry)[0] if is_tail_drag else entry

            def pred_nums_for_ref(base, c_val, tail_only=False):
                if is_tail_drag:
                    c_tail, head = _tail_drag_entry_parts(c_val)
                    tail = (c_tail - base) % 10 if is_sum else (base + c_tail) % 10
                    p = head * 10 + tail
                    if 1 <= p <= max_val:
                        return [p]
                    return []

                p = (c_val - base) if is_sum else (base + c_val)
                if tail_only:
                    return [p % 10]
                if is_cyclic:
                    p = (p - 1) % max_val + 1
                    return [p]
                if 1 <= p <= max_val:
                    return [p]
                return []

            def c_values_for_ref(base, draw_set, k_idx, step_val):
                vals = set()
                if is_tail_drag:
                    for target_num in draw_set:
                        try:
                            target_num = int(target_num)
                        except Exception:
                            continue
                        head = target_num // 10
                        tail = target_num % 10
                        if is_sum:
                            c = (base + tail) % 10
                        else:
                            c = (tail - base) % 10
                        if is_step_advance:
                            c += k_idx * step_val
                        vals.add((c, head))
                    return vals

                if is_tail_match:
                    tails = {n % 10 for n in draw_set}
                    for tail in tails:
                        if is_sum:
                            c = (base + tail) % 10
                        else:
                            c = (tail - base) % 10
                        if is_step_advance:
                            c += k_idx * step_val
                        vals.add(c)
                    return vals

                for target_num in draw_set:
                    if is_sum:
                        c = base + target_num
                        if is_cyclic:
                            c = (c - 1) % max_val + 1
                    else:
                        c = target_num - base
                        if is_cyclic:
                            c = c % max_val
                            if c <= 0:
                                c += max_val
                    if is_step_advance:
                        c += k_idx * step_val
                    vals.add(c)
                return vals

            def build_c_domain():
                if is_tail_drag:
                    max_head = max_val // 10
                    return [(c, h) for c in range(10) for h in range(max_head + 1)]
                if is_tail_match:
                    return list(range(10))
                if is_cyclic:
                    domain = list(range(1, max_val + 1))
                elif is_sum:
                    domain = list(range(2, max_val * 2 + 1))
                else:
                    domain = list(range(-max_val + 1, max_val))
                    if 0 in domain:
                        domain.remove(0)

                if is_tail:
                    # 星期模式也補齊最大球號, 讓 +19+49、+9+39 這類同尾組合不會漏掉。
                    if max_val not in domain:
                        domain.append(max_val)
                    if any(isinstance(c, int) and c < 0 for c in domain) and -max_val not in domain:
                        domain.append(-max_val)
                    domain = sorted(set(domain))
                return domain

            def c_tuple_passes_style(c_tuple):
                if not c_tuple:
                    return False
                style_vals = []
                for c in c_tuple:
                    if is_tail_drag:
                        style_vals.append(_tail_drag_entry_parts(c)[0])
                    else:
                        style_vals.append(c)
                if is_consec:
                    s_vals = sorted(style_vals)
                    return all(s_vals[i + 1] - s_vals[i] == 1 for i in range(len(s_vals) - 1))
                if is_tail:
                    tails = {abs(int(c)) % 10 for c in style_vals}
                    same_tail = len(tails) == 1
                    same_direction = all(int(c) > 0 for c in style_vals) or all(int(c) < 0 for c in style_vals)
                    return same_tail and same_direction
                return True

            def build_candidate_c_tuples(hist_entries, step_val):
                if not hist_entries:
                    return []

                if is_non_hit:
                    domain = build_c_domain()
                    if is_tail_drag:
                        cand = []
                        for c_tuple in product(domain, repeat=week_pick_count):
                            if c_tuple_passes_style(c_tuple):
                                cand.append(tuple(c_tuple))
                            if len(cand) >= 25000:
                                break
                        return cand
                    if (not is_tail) and (not is_tail_match) and (not is_cyclic) and (not is_sum):
                        domain = [c for c in domain if -20 <= c <= 20]
                    if is_consec:
                        seqs = []
                        d_sorted = sorted(domain)
                        for i in range(len(d_sorted) - week_pick_count + 1):
                            sub = tuple(d_sorted[i:i + week_pick_count])
                            if c_tuple_passes_style(sub):
                                seqs.append(sub)
                        return seqs[:25000]
                    if is_tail:
                        cand = []
                        for t in range(10):
                            same_tail = [c for c in domain if abs(c) % 10 == t]
                            if len(same_tail) >= week_pick_count:
                                for combo in combinations(same_tail, week_pick_count):
                                    if c_tuple_passes_style(combo):
                                        cand.append(combo)
                        return cand[:25000]
                    return list(combinations(domain, week_pick_count))[:25000]

                pool_limit = 18 if is_tail_drag and week_pick_count <= 2 else (14 if week_pick_count <= 2 else (8 if week_pick_count == 3 else 5))
                pools = []
                first_ent = hist_entries[0]
                for ref_i in range(week_pick_count):
                    freq = Counter()
                    first_vals = c_values_for_ref(first_ent['bases'][ref_i], first_ent['target_set'], first_ent['k'], step_val)
                    for ent in hist_entries[:max(8, effective_min_streak + 3)]:
                        for c in c_values_for_ref(ent['bases'][ref_i], ent['target_set'], ent['k'], step_val):
                            freq[c] += 1
                    pool = [c for c, _ in freq.most_common(pool_limit)]
                    for c in first_vals:
                        if c not in pool:
                            pool.append(c)
                    if is_tail_drag:
                        pool = sorted(set(pool), key=lambda x: (x[0], x[1]))[:max(pool_limit, len(first_vals))]
                    else:
                        pool = sorted(set(pool))[:max(pool_limit, len(first_vals))]
                    if not pool:
                        return []
                    pools.append(pool)

                cand = []
                for c_tuple in product(*pools):
                    c_tuple = tuple(c_tuple)
                    if not c_tuple_passes_style(c_tuple):
                        continue
                    _, hit_count, _ = hit_info_for_candidate(first_ent, c_tuple, step_val)
                    if hit_count >= min_hit_req:
                        cand.append(c_tuple)
                    if len(cand) >= 25000:
                        break
                return cand

            def hit_info_for_candidate(ent, c_tuple, step_val):
                matched_cs = []
                hit_keys = set()
                target_set = ent['target_set']
                target_tails = {n % 10 for n in target_set}
                k_idx = ent['k']

                for ref_i, base in enumerate(ent['bases']):
                    c_future = c_tuple[ref_i]
                    if is_step_advance:
                        if is_tail_drag:
                            c0, h0 = _tail_drag_entry_parts(c_future)
                            c_act = (c0 - k_idx * step_val, h0)
                        else:
                            c_act = c_future - k_idx * step_val
                    else:
                        c_act = c_future
                    preds = pred_nums_for_ref(base, c_act, tail_only=(is_tail_match and not is_tail_drag))
                    if is_tail_match and not is_tail_drag:
                        for p_tail in preds:
                            if p_tail in target_tails:
                                matched_cs.append(c_future)
                                hit_keys.add(p_tail)
                                break
                    else:
                        for p in preds:
                            if p in target_set:
                                matched_cs.append(c_future)
                                hit_keys.add(p)
                                break
                return matched_cs, len(hit_keys), hit_keys

            def latest_predictions(latest_bases, c_tuple):
                nums = []
                for base, c_future in zip(latest_bases, c_tuple):
                    nums.extend(pred_nums_for_ref(base, c_future, tail_only=(is_tail_match and not is_tail_drag)))
                nums = sorted(set(nums))
                if is_tail_match and not is_tail_drag:
                    nums = expand_tails(nums, max_val)
                return nums

            def weekday_verify_miss(pred_nums, target_indices):
                if pred_range not in (3, 4):
                    return True
                miss_count = 1 if pred_range == 3 else 2
                if len(target_indices) < miss_count:
                    return True
                last_targets = target_indices[-miss_count:]
                if is_tail_match and not is_tail_drag:
                    pred_tails = {n % 10 for n in pred_nums}
                    for t_idx in last_targets:
                        draw_tails = {n % 10 for n in _target_item_set(processed_data[t_idx])}
                        if pred_tails & draw_tails:
                            return False
                else:
                    pred_set = set(pred_nums)
                    for t_idx in last_targets:
                        if pred_set & _target_item_set(processed_data[t_idx]):
                            return False
                return True

            all_slots = [(off, pos) for off in range(1, max_ref_back + 1) for pos in range(max_pos)]
            slot_combos_all = list(combinations(all_slots, week_pick_count))
            if week_pick_count >= 3 and len(slot_combos_all) > combo_slot_limit:
                combo_guard_was_used = True
                slot_combos_all = slot_combos_all[:combo_slot_limit]

            total_work = max(1, len(weekdays) * len(slot_combos_all) * max(1, len(step_values)))
            done_work = 0

            for wd in weekdays:
                target_indices = [i for i, item in enumerate(processed_data) if item['date'].weekday() == wd and i >= max_ref_back]
                if len(target_indices) < effective_min_streak:
                    continue

                latest_target_idx, latest_target_date = next_selected_weekday_virtual_index(wd)
                if latest_target_idx is None:
                    continue

                for slot_combo in slot_combos_all:
                    latest_pack = calc_week_refs_global(latest_target_idx, slot_combo)
                    if latest_pack is None:
                        continue
                    latest_bases, latest_ref_indexes = latest_pack

                    for step_val in step_values:
                        done_work += 1
                        if done_work % 120 == 0 and progress_callback:
                            progress_callback(min(0.98, done_work / float(total_work)))

                        hist_entries = []
                        # 從最近的指定星期往回驗證;每一筆 target_idx 都是「本期指定星期」。
                        for k_idx, target_idx in enumerate(reversed(target_indices), start=1):
                            refs_pack = calc_week_refs_global(target_idx, slot_combo)
                            if refs_pack is None:
                                continue
                            bases, ref_indexes = refs_pack
                            target_set = weekday_target_set_global(target_idx)
                            if not target_set:
                                continue
                            hist_entries.append({
                                'bases': bases,
                                'ref_indexes': ref_indexes,
                                'target_set': target_set,
                                'k': k_idx,
                                'date': processed_data[target_idx]['date'],
                                'target_idx': target_idx,
                            })

                        if len(hist_entries) < effective_min_streak:
                            continue

                        candidate_c_lists = build_candidate_c_tuples(hist_entries, step_val)
                        if not candidate_c_lists:
                            continue

                        candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                        for c_tuple in candidate_c_lists:
                            if (is_alternate or is_alternate_vip) and len(c_tuple) != 2:
                                continue

                            streak = 0
                            hit_history_c = []
                            for ent in hist_entries:
                                matched_cs, hit_count, _ = hit_info_for_candidate(ent, c_tuple, step_val)
                                success = (hit_count == 0) if is_non_hit else (hit_count >= min_hit_req)
                                if success:
                                    streak += 1
                                    hit_history_c.append(list(c_tuple) if is_non_hit else matched_cs)
                                else:
                                    break

                            if streak < effective_min_streak:
                                continue

                            if is_alternate or is_alternate_vip:
                                if streak < 4:
                                    continue
                                c1_val, c2_val = c_tuple[0], c_tuple[1]
                                if is_alternate_vip:
                                    valid_streak = 0
                                    for length in range(streak, 3, -1):
                                        if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                            valid_streak = length
                                            break
                                    if valid_streak < max(4, effective_min_streak):
                                        continue
                                    streak = valid_streak
                                elif is_alternate:
                                    if not check_alt_any(hit_history_c, c1_val, c2_val):
                                        continue

                            latest_pred_nums_to_save = latest_predictions(latest_bases, c_tuple)
                            if not latest_pred_nums_to_save:
                                continue
                            if not weekday_verify_miss(latest_pred_nums_to_save, target_indices):
                                continue
                            if min_streak_input == 0 and streak <= 1:
                                continue

                            week_rules = []
                            for (off, pos), base_val, c_val, ref_idx in zip(slot_combo, latest_bases, c_tuple, latest_ref_indexes):
                                one_pred = pred_nums_for_ref(base_val, c_val, tail_only=(is_tail_match and not is_tail_drag))
                                rule_item = {
                                    'offset': off,
                                    'pos': pos,
                                    'base': base_val,
                                    'pred': one_pred[0] if one_pred else None,
                                    'ref_idx': ref_idx,
                                }
                                if is_tail_drag:
                                    c_tail, head_val = _tail_drag_entry_parts(c_val)
                                    rule_item['c'] = c_tail
                                    rule_item['head'] = head_val
                                else:
                                    rule_item['c'] = c_val
                                week_rules.append(rule_item)

                            result_key = (wd, tuple(slot_combo), tuple(c_tuple), step_val, tuple(latest_pred_nums_to_save), bool(is_sum), bool(is_cyclic), bool(is_tail_match), bool(is_tail_drag), bool(is_non_hit))
                            if result_key in seen_week_keys:
                                continue
                            seen_week_keys.add(result_key)

                            first_off, first_pos = slot_combo[0]
                            second_off, second_pos = slot_combo[1] if len(slot_combo) > 1 else slot_combo[0]
                            first_base = latest_bases[0]
                            second_base = latest_bases[1] if len(latest_bases) > 1 else latest_bases[0]

                            results_list.append({
                                'mode': 15,
                                'pred_range': pred_range,
                                'streak': streak,
                                'weekday': wd,
                                'target_weekday_date': latest_target_date,
                                'ref1_offset': first_off,
                                'ref2_offset': second_off,
                                'P1': first_pos,
                                'P2': second_pos,
                                'X': first_base,
                                'P_X': first_pos,
                                'N': first_off,
                                'P': first_pos,
                                'R1': first_base,
                                'R2': second_base,
                                'week_rules': week_rules,
                                'M': 1,
                                'C_list': tuple(c_tuple),
                                'max_val': max_val,
                                'min_hit_req': min_hit_req,
                                'sum_mode': is_sum,
                                'cyclic': is_cyclic,
                                'ref_dir': 0,
                                'latest_occ': len(processed_data) - 1,
                                'latest_pred_nums': latest_pred_nums_to_save,
                                'trigger_dates': [ent['date'] for ent in hist_entries[:streak]],
                                'is_step_advance': is_step_advance,
                                'step_val': step_val,
                                'is_tail_match': (is_tail_match and not is_tail_drag),
                                'is_tail_drag': is_tail_drag,
                                'is_non_hit': is_non_hit,
                                'lock_special': lock_special,
                            })

        elif analysis_mode == 9:
            # 立柱熱門混合修復:
            # 1) 2期/3期內:保留目前「熱門拖牌核心 + 立柱分組」邏輯。
            # 2) 2期到期/3期到期:直接沿用測試127成功的立柱熱門核心,避免熱門拖牌早中邏輯把到期版路濾掉。
            pillar_counts = params.get('pillar_counts', [3, 3, 3, 0, 0])
            k_total = sum(pillar_counts)

            if pred_range in (3, 4):
                if k_total > 0:
                    # 立柱到期正確規則:
                    # 2期到期只看第2期那一天;3期到期只看第3期那一天。
                    # 前面期數如果同一天已達標才算提前中;不能把2/3天加總。
                    def _mode9_due_offsets_for_range():
                        # 第一個回傳值:歷史驗證用的範圍,範圍內任一天同日達標即可。
                        # 第二個回傳值:最新預測用的提前中檢查。
                        if pred_range == 3:
                            return [0, 1], [0]
                        if pred_range == 4:
                            return [0, 1, 2], [0, 1]
                        return [0], []

                    def _mode9_pillar_stars_same_day(pillars, draw_set):
                        stars = 0
                        draw_set = set(draw_set)
                        for one_pillar in pillars:
                            if one_pillar and any(num in draw_set for num in one_pillar):
                                stars += 1
                        return stars

                    def _mode9_star_success(stars):
                        return (stars == 0) if is_non_hit else (stars >= min_hit_req)

                    def _mode9_due_pack_for_occ(t_idx, M):
                        base_idx = t_idx + M
                        hit_offsets, early_offsets = _mode9_due_offsets_for_range()

                        hit_sets = []
                        early_sets = []
                        for off in hit_offsets:
                            idx = base_idx + off
                            if idx < 0 or idx >= total_periods:
                                return None
                            hit_sets.append(_target_item_set(processed_data[idx]))
                        for off in early_offsets:
                            idx = base_idx + off
                            if idx < 0 or idx >= total_periods:
                                return None
                            early_sets.append(_target_item_set(processed_data[idx]))
                        return {'hit_sets': hit_sets, 'early_sets': early_sets}

                    def _mode9_due_success_for_pack(pillars, pack):
                        if not isinstance(pack, dict):
                            return False, 0, None

                        # 歷史驗證:2/3期到期不是要求每一段都剛好到期那天中,
                        # 而是範圍內任一天「同一天達標」即可算連莊。
                        # 最新預測段的提前中,另外由 _mode9_current_due_not_early 檢查。
                        best_stars = 0
                        for h_set in pack.get('hit_sets', []):
                            stars = _mode9_pillar_stars_same_day(pillars, h_set)
                            if stars > best_stars:
                                best_stars = stars
                            if _mode9_star_success(stars):
                                return True, stars, None
                        return False, best_stars, None

                    def _mode9_current_due_not_early(latest_occ, M, pillars):
                        # 目前最新預測只檢查前面已開的早期區,不要求未來到期日已開。
                        base_idx = latest_occ + M
                        _, early_offsets = _mode9_due_offsets_for_range()
                        for off in early_offsets:
                            idx = base_idx + off
                            if 0 <= idx < total_periods:
                                stars = _mode9_pillar_stars_same_day(pillars, _target_item_set(processed_data[idx]))
                                if _mode9_star_success(stars):
                                    return False
                        return True

                    max_px = balls_cnt + (1 if params['has_special'] else 0)
                    if shape_index in (1, 2, 3):
                        px_list = [0]
                    else:
                        px_list = range(max_px) if is_fixed_pos else [-1]

                    for X in range(1, max_val + 1):
                        if progress_callback: progress_callback(X / max_val)

                        for P_X in px_list:
                            if P_X == -1:
                                occurrences = get_occurrences_by_set(X)
                            else:
                                occurrences = get_occurrences_by_pos(P_X, X)

                            if len(occurrences) < effective_min_streak: continue

                            for latest_occ_idx in range(len(occurrences)-1, -1, -1):
                                if latest_occ_idx + 1 < effective_min_streak: break

                                latest_occ = occurrences[latest_occ_idx]
                                if pred_range == 3: M = total_periods - 1 - latest_occ
                                elif pred_range == 4: M = total_periods - 2 - latest_occ
                                else: M = total_periods - latest_occ

                                if M < 1 or M > 15: continue
                                if pred_range == 3 and M < 2: continue
                                if pred_range == 4 and M < 3: continue

                                history_targets = []
                                broken = False
                                for i in range(latest_occ_idx, -1, -1):
                                    t_idx = occurrences[i]
                                    if i == latest_occ_idx:
                                        history_targets.append("PENDING")
                                    else:
                                        pack = _mode9_due_pack_for_occ(t_idx, M)
                                        if pack is None:
                                            broken = True
                                            break
                                        history_targets.append(pack)

                                if broken or len(history_targets) < effective_min_streak: continue

                                freq = Counter()
                                lookback_blocks = max(50, effective_min_streak + 20)
                                for pack in history_targets[1:lookback_blocks]:
                                    if isinstance(pack, dict):
                                        for t_set in pack.get('hit_sets', []):
                                            for num in t_set:
                                                freq[num] += 1

                                if combo_hot_pillar_guard_active:
                                    # 3/3/3/0/0 = 9 碼,C(20,9) 會在每個觸發點重跑。
                                    # 改成只取熱門前段 + 少量隨機補強,避免 Pythonista 閃退。
                                    pool_size = min(len(freq), max(k_total + 3, 13))
                                    top_candidates = [num for num, count in freq.most_common(pool_size)]
                                    cand_c_lists = list(islice(combinations(top_candidates, k_total), combo_source_limit))

                                    wider_pool = [num for num, count in freq.most_common(min(len(freq), max(k_total + 7, 16)))]
                                    if len(wider_pool) >= k_total:
                                        random_try_count = 700
                                        for _ in range(random_try_count):
                                            cand_c_lists.append(tuple(sorted(random.sample(wider_pool, k_total))))
                                else:
                                    pool_size = min(len(freq), 20)
                                    top_candidates =[num for num, count in freq.most_common(pool_size)]
                                    cand_c_lists = list(combinations(top_candidates, k_total))

                                    wider_pool =[num for num, count in freq.most_common(30)]
                                    if len(wider_pool) >= k_total:
                                        for _ in range(5000):
                                            cand_c_lists.append(tuple(sorted(random.sample(wider_pool, k_total))))
                                cand_c_lists = list(set(cand_c_lists))
                                cand_c_lists = _guard_candidate_c_lists(cand_c_lists)

                                for c_tuple in cand_c_lists:
                                    pillars = _mode10_build_pillars(c_tuple, pillar_counts, sequential=is_consec)

                                    streak = 0
                                    three_star_count = 0
                                    for k in range(1, len(history_targets)):
                                        pack = history_targets[k]
                                        success, stars, fail_reason = _mode9_due_success_for_pack(pillars, pack)
                                        if success:
                                            streak += 1
                                            if stars >= 3 and not is_non_hit:
                                                three_star_count += 1
                                        else:
                                            break

                                    if streak >= effective_min_streak:
                                        if not _mode9_current_due_not_early(latest_occ, M, pillars):
                                            continue

                                        trigger_dates = [processed_data[occurrences[latest_occ_idx - k]]['date'] for k in range(streak + 1)]

                                        results_list.append({
                                            'mode': 9,
                                            'pred_range': pred_range,
                                            'streak': streak,
                                            'three_star_count': three_star_count,
                                            'X': X,
                                            'P_X': P_X,
                                            'M': M,
                                            'pillars': pillars,
                                            'max_val': max_val,
                                            'min_hit_req': min_hit_req,
                                            'latest_occ': latest_occ,
                                            'latest_pred_nums': list(c_tuple),
                                            'trigger_dates': trigger_dates,
                                            'is_tail_match': False,
                                            'is_non_hit': is_non_hit
                                        })

            else:
                if k_total > 0:
                    hot_params = dict(params)
                    hot_params['analysis_mode'] = 1
                    hot_params['source_mode'] = 9
                    hot_params['pick_count'] = k_total
                    hot_params['select_count'] = str(k_total)
                    if pred_range in (3, 4):
                        hot_params['pillar_hot_candidate_only'] = True

                    hot_results, _ = self.execute_analysis_for_date(limit_date, exclude_today, hot_params, progress_callback)

                    def _pillar_star_count_same_day(pillars, draw_set):
                        stars = 0
                        for p_nums in pillars:
                            if p_nums and any(n in draw_set for n in p_nums):
                                stars += 1
                        return stars

                    def _pillar_range_success_for_occ(occ_idx_value, m_value, pillars):
                        # 歷史連莊驗證規則:
                        # 2/3期內:範圍內任一天「同一天達標」即可。
                        # 2/3期到期:歷史前面驗證也看範圍內任一天達標;
                        #            只有最新預測那一段才是「前面沒達標、到期日達標」。
                        if pred_range == 0:
                            offs = [0]
                        elif pred_range in (1, 3):
                            offs = [0, 1]
                        elif pred_range in (2, 4):
                            offs = [0, 1, 2]
                        else:
                            offs = [0]

                        best_stars = 0
                        best_target_idx = None
                        for off in offs:
                            target_idx = occ_idx_value + m_value + off
                            if target_idx < 0 or target_idx >= total_periods:
                                continue
                            draw_set = _target_item_set(processed_data[target_idx])
                            stars = _pillar_star_count_same_day(pillars, draw_set)
                            if stars > best_stars:
                                best_stars = stars
                                best_target_idx = target_idx
                            success = (stars == 0) if is_non_hit else (stars >= min_hit_req)
                            if success:
                                return True, stars, target_idx
                        return False, best_stars, best_target_idx

                    def _pillar_due_not_early(occ_idx_value, m_value, pillars):
                        # 2期到期/3期到期:前面期數如果同一天已達標,就不是到期。
                        if pred_range == 3:
                            early_offsets = [0]
                        elif pred_range == 4:
                            early_offsets = [0, 1]
                        else:
                            return True
                        for off in early_offsets:
                            target_idx = occ_idx_value + m_value + off
                            if target_idx < 0 or target_idx >= total_periods:
                                continue
                            stars = _pillar_star_count_same_day(pillars, _target_item_set(processed_data[target_idx]))
                            early_success = (stars == 0) if is_non_hit else (stars >= min_hit_req)
                            if early_success:
                                return False
                        return True

                    def _recalc_pillar_streak_from_hot(hr, pillars):
                        try:
                            x_val = int(hr.get('X'))
                            p_x_val = int(hr.get('P_X', -1))
                            m_val = int(hr.get('M'))
                            latest_occ_val = int(hr.get('latest_occ'))
                        except Exception:
                            return 0, 0, [], []

                        if p_x_val == -1:
                            occs = get_occurrences_by_set(x_val)
                        else:
                            occs = get_occurrences_by_pos(p_x_val, x_val)
                        if latest_occ_val not in occs:
                            return 0, 0, [], []

                        latest_idx = occs.index(latest_occ_val)
                        streak_val = 0
                        three_star_count_val = 0

                        # 修正立柱熱門繪圖:
                        # 熱門拖牌核心的 trigger_dates 會包含 latest_occ 這個「最新預測觸發點」,
                        # 但 v27 重新計算立柱 streak 時把 latest_occ 拿掉了,
                        # 導致最新一期預測不會塗黃色、觸發點也不會畫出來。
                        trigger_dates_val = [processed_data[latest_occ_val]['date']]
                        hit_target_dates_val = []

                        # 歷史連莊從前一個 occurrence 開始往回驗證。
                        # 注意:2/3期到期的「歷史驗證」不是要求每段都到期才中,
                        # 而是範圍內任一天達標即可;最新預測段才套用到期概念。
                        for j in range(latest_idx - 1, -1, -1):
                            occ_val = occs[j]

                            ok, stars, target_idx = _pillar_range_success_for_occ(occ_val, m_val, pillars)
                            if ok:
                                streak_val += 1
                                if stars >= 3 and not is_non_hit:
                                    three_star_count_val += 1
                                trigger_dates_val.append(processed_data[occ_val]['date'])
                                if target_idx is not None and 0 <= target_idx < total_periods:
                                    hit_target_dates_val.append(processed_data[target_idx]['date'])
                            else:
                                break

                        return streak_val, three_star_count_val, trigger_dates_val, hit_target_dates_val

                    for hr in hot_results:
                        nums = list(hr.get('latest_pred_nums', []))[:k_total]
                        if len(nums) < k_total:
                            continue

                        pillars = _mode10_build_pillars(tuple(nums), pillar_counts, sequential=is_consec)

                        pillar_streak, pillar_three_star_count, pillar_trigger_dates, pillar_hit_dates = _recalc_pillar_streak_from_hot(hr, pillars)
                        if pillar_streak < effective_min_streak:
                            continue
                        if min_streak_input == 0 and pillar_streak <= 1:
                            continue

                        rr = dict(hr)
                        rr['mode'] = 9
                        rr['source_mode'] = 1
                        rr['pillars'] = pillars
                        rr['latest_pred_nums'] = nums
                        rr['streak'] = pillar_streak
                        rr['three_star_count'] = pillar_three_star_count
                        rr['trigger_dates'] = pillar_trigger_dates or list(hr.get('trigger_dates', []))
                        rr['pillar_hit_dates'] = pillar_hit_dates
                        rr['min_hit_req'] = min_hit_req
                        rr['min_hit_list'] = list(params.get('min_hit_list', []))
                        rr['combo_guarded_hot_core'] = bool(k_total > 4)
                        results_list.append(rr)

        elif analysis_mode == 10:
            weekdays = params.get('weekdays',[])
            if progress_callback:
                progress_callback(0.02)
            n_period_enable = params.get('n_period_enable', False)
            n_period_gap = params.get('n_period_gap', 0)
            is_nurture = params.get('is_nurture', False)
            pillar_counts = params.get('pillar_counts',[3, 3, 3, 0, 0])
            k_total = sum(pillar_counts)

            L_all =[]
            for item in processed_data:
                L_all.append({'date': item['date'], 'set': item['set'], 'is_future': False, 'list': item['list']})

            if not L_all: return[], next_draw_data

            last_date = processed_data[-1]['date']
            future_dates =[]
            curr_d = last_date
            for _ in range(60):
                curr_d = self.next_draw_date(curr_d)
                future_dates.append(curr_d)

            for fd in future_dates:
                L_all.append({'date': fd, 'set': set(), 'is_future': True, 'list': []})

            if weekdays:
                L =[x for x in L_all if x['date'].weekday() in weekdays]
            else:
                L = L_all

            if not L: return[], next_draw_data

            idx_F = -1
            for i, x in enumerate(L):
                if x['is_future']:
                    idx_F = i
                    break

            if idx_F == -1: return[], next_draw_data

            blocks = {}
            if n_period_enable:
                active_len = 3
                gap_len = n_period_gap
                cycle_len = active_len + gap_len

                anchor_idx = idx_F - 1 if is_nurture else idx_F

                if anchor_idx >= 0:
                    for i, x in enumerate(L):
                        dist = anchor_idx - i
                        block_id = dist // cycle_len
                        cycle_pos = dist % cycle_len

                        if cycle_pos < active_len:
                            if block_id not in blocks:
                                blocks[block_id] =[]
                            blocks[block_id].append((i, x))
            else:
                special_patterns = {
                    (4, 5, 0): [4, 5, 0],
                    (5, 0, 1): [5, 0, 1],
                    (5, 6, 0): [5, 6, 0],
                    (6, 0, 1): [6, 0, 1],
                }
                selected_key = None
                if len(weekdays) == 3:
                    wd_set = set(weekdays)
                    for pat in special_patterns:
                        if wd_set == set(pat):
                            selected_key = pat
                            break

                if selected_key is not None:

                    filtered = [(i, x) for i, x in enumerate(L) if x['date'].weekday() in selected_key]
                    blocks_list = []
                    i = 0
                    while i <= len(filtered) - len(selected_key):
                        chunk = filtered[i:i + len(selected_key)]
                        if [x['date'].weekday() for _, x in chunk] == list(selected_key):
                            blocks_list.append(chunk)
                            i += len(selected_key)
                        else:
                            i += 1

                    future_block_idx = -1
                    for bi, block in enumerate(blocks_list):
                        if any(x['is_future'] for _, x in block):
                            future_block_idx = bi
                            break

                    if future_block_idx != -1:
                        for bi, block in enumerate(blocks_list):
                            if is_nurture:
                                b_id = future_block_idx - bi - 1
                            else:
                                b_id = future_block_idx - bi
                            blocks[b_id] = block
                else:
                    weeks =[]
                    curr_w =[]
                    curr_iso = None
                    for x in L:
                        iso = x['date'].isocalendar()[:2]
                        if iso != curr_iso:
                            if curr_w: weeks.append(curr_w)
                            curr_w =[]
                            curr_iso = iso
                        curr_w.append(x)
                    if curr_w: weeks.append(curr_w)

                    w_idx_F = -1
                    for i, w in enumerate(weeks):
                        if any(x['is_future'] for x in w):
                            w_idx_F = i
                            break
                    if w_idx_F != -1:
                        for i, w in enumerate(weeks):
                            if is_nurture:
                                b_id = w_idx_F - i - 1
                            else:
                                b_id = w_idx_F - i
                            blocks[b_id] =[(j, x) for j, x in enumerate(w)]

            target_b_id = -1 if is_nurture else 0
            if target_b_id + 1 not in blocks:
                return[], next_draw_data

            if k_total == 0: return[], next_draw_data

            if is_tail_match:
                domain_elements = list(range(10))
            else:
                domain_elements = list(range(1, max_val + 1))


            if is_consec:
                cand_c_lists =[]
                active_pillar_counts =[cnt for cnt in pillar_counts if cnt > 0]
                if active_pillar_counts:
                    total_steps = 1
                    for cnt in active_pillar_counts:
                        total_steps *= max(0, len(domain_elements) - cnt + 1)
                    done_steps = 0

                    def build_pillar_consec(idx, min_start, current):
                        nonlocal done_steps
                        if idx >= len(active_pillar_counts):
                            cand_c_lists.append(tuple(current))
                            return
                        cnt = active_pillar_counts[idx]
                        max_start = len(domain_elements) - cnt
                        for s_idx in range(min_start, max_start + 1):
                            block = domain_elements[s_idx:s_idx + cnt]
                            if len(block) < cnt:
                                break
                            if all(block[j+1] - block[j] == 1 for j in range(len(block)-1)):
                                build_pillar_consec(idx + 1, s_idx + cnt, current + block)
                            done_steps += 1
                            if progress_callback and total_steps > 0 and done_steps % 25 == 0:
                                progress_callback(min(0.38, done_steps / float(total_steps) * 0.38))

                    build_pillar_consec(0, 0, [])
                    cand_c_lists = list(set(cand_c_lists))
                    if progress_callback:
                        progress_callback(0.4)
                else:
                    cand_c_lists = []
            else:
                target_items =[]
                max_lookback = max(150, effective_min_streak + 40)
                for b_id in range(1, max_lookback):
                    if b_id in blocks:
                        target_items.extend([x for i, x in blocks[b_id] if not x['is_future']])

                freq = Counter()
                for x in target_items:
                    for num in x['set']:
                        if is_tail_match:
                            freq[num % 10] += 1
                        else:
                            freq[num] += 1

                pool_size = min(max(20, k_total), len(freq))

                top_candidates =[num for num, count in freq.most_common(pool_size)]
                cand_c_lists = list(combinations(top_candidates, k_total))

                draw_masks = {}
                for b in blocks:
                    draw_masks[b] =[]
                    for j, x in blocks[b]:
                        if not x['is_future']:
                            if is_tail_match:
                                mask = 0
                                for num in x['set']:
                                    mask |= (1 << (num % 10))
                            else:
                                mask = sum(1 << num for num in x['set'])
                            draw_masks[b].append(mask)


                start_b_id = 0 if is_nurture else 1
                def evaluate_tup_fast_with_gradient(c_tup):
                    pillars = _mode10_build_pillars(c_tup, pillar_counts, sequential=is_consec)
                    p_masks = [0] * len(pillars)
                    for p_idx, p_nums in enumerate(pillars):
                        for num in p_nums:
                            p_masks[p_idx] |= (1 << num)
                    active_p_masks =[m for m in p_masks if m != 0]

                    if not is_nurture:
                        if 0 in draw_masks:
                            hit_found = False
                            for d_mask in draw_masks[0]:
                                stars = 0
                                for p_mask in active_p_masks:
                                    if d_mask & p_mask:
                                        stars += 1
                                if (stars > 0) if is_non_hit else (stars >= min_hit_req):
                                    hit_found = True
                                    break
                            if hit_found:
                                return (-1, -1, -1.0)
                    else:
                        if 0 not in draw_masks:
                            return (-1, -1, -1.0)
                        hit_found = False
                        for d_mask in draw_masks[0]:
                            stars = 0
                            for p_mask in active_p_masks:
                                if d_mask & p_mask:
                                    stars += 1
                            if (stars == 0) if is_non_hit else (stars >= min_hit_req):
                                hit_found = True
                                break
                        if not hit_found:
                            return (-1, -1, -1.0)

                    streak = 0
                    three_star_count = 0
                    curr_b = start_b_id
                    while curr_b in draw_masks:
                        success_found = False
                        max_stars = 0
                        for d_mask in draw_masks[curr_b]:
                            stars = 0
                            for p_mask in active_p_masks:
                                if d_mask & p_mask:
                                    stars += 1
                            if is_non_hit:
                                if stars == 0: success_found = True
                            else:
                                if stars >= min_hit_req:
                                    success_found = True
                                    if stars > max_stars:
                                        max_stars = stars
                        if success_found:
                            streak += 1
                            curr_b += 1
                            if max_stars >= 3 and not is_non_hit:
                                three_star_count += 1
                        else:
                            break

                    extra_hits = 0
                    for b_id in range(curr_b, curr_b + 15):
                        if b_id in draw_masks:
                            for d_mask in draw_masks[b_id]:
                                for p_mask in active_p_masks:
                                    if d_mask & p_mask:
                                        extra_hits += 1

                    return (streak, three_star_count, streak + (extra_hits / 100.0))

                for lookahead in[5, 10, 15, 20, 30]:
                    freq_recent = Counter()
                    for b_id in range(start_b_id, start_b_id + lookahead):
                        if b_id in draw_masks:
                            for d_mask in draw_masks[b_id]:
                                for num in domain_elements:
                                    if (1 << num) & d_mask:
                                        freq_recent[num] += 1
                    top_rec =[num for num, c in freq_recent.most_common(min(len(domain_elements), k_total + 10))]
                    if len(top_rec) >= k_total:
                        for _ in range(800):
                            cand_c_lists.append(tuple(sorted(random.sample(top_rec, k_total))))

                best_hill_climbed = set()
                wider_pool_list = list(domain_elements)
                for restart in range(2000):
                    if progress_callback and restart % 200 == 0:
                        progress_callback(restart / 2000.0)

                    curr_tup = tuple(sorted(random.sample(wider_pool_list, k_total)))
                    curr_score = evaluate_tup_fast_with_gradient(curr_tup)[2]

                    improved = True
                    steps = 0
                    while improved and steps < 15:
                        improved = False
                        steps += 1
                        for i in range(k_total):
                            for new_num in wider_pool_list:
                                if new_num not in curr_tup:
                                    new_tup_list = list(curr_tup)
                                    new_tup_list[i] = new_num
                                    new_tup = tuple(sorted(new_tup_list))
                                    new_score = evaluate_tup_fast_with_gradient(new_tup)[2]
                                    if new_score > curr_score:
                                        curr_score = new_score
                                        curr_tup = new_tup
                                        improved = True
                                        break
                            if improved:
                                break

                    final_res = evaluate_tup_fast_with_gradient(curr_tup)
                    if final_res[0] >= effective_min_streak:
                        best_hill_climbed.add(curr_tup)

                cand_c_lists.extend(list(best_hill_climbed))
                cand_c_lists = list(set(cand_c_lists))

            cand_c_lists = _guard_candidate_c_lists(cand_c_lists)
            count_iter = 0
            total_cand = max(1, len(cand_c_lists))
            for c_tuple in cand_c_lists:
                count_iter += 1
                if count_iter % 100 == 0 or count_iter == total_cand:
                    if not self.is_analyzing: raise InterruptedError()
                    if progress_callback: progress_callback(min(0.99, count_iter / float(total_cand)))

                best_streak = 0
                best_three_star_count = 0
                best_trigger_dates = []
                best_hit_blocks =[]
                best_target_block_dates =[]

                pillars = _mode10_build_pillars(c_tuple, pillar_counts, sequential=is_consec)

                def check_hit(block_items):
                    success_found = False
                    best_date = None
                    max_stars = 0
                    for x in block_items:
                        if x['is_future']: continue
                        stars = 0
                        for p in pillars:
                            if p:
                                if is_tail_match:
                                    p_tails = set(p)
                                    x_tails = {num % 10 for num in x['set']}
                                    if p_tails & x_tails:
                                        stars += 1
                                else:
                                    if any(num in x['set'] for num in p):
                                        stars += 1
                        if is_non_hit:
                            if stars == 0:
                                success_found = True
                                best_date = x['date']
                        else:
                            if stars >= min_hit_req:
                                success_found = True
                                if stars > max_stars:
                                    max_stars = stars
                                    best_date = x['date']
                    if success_found:
                        return True, best_date, max_stars
                    return False, None, 0

                if is_nurture:
                    curr_b_id = 0
                else:
                    curr_b_id = 1
                    # 到期修正:本輪(第0區塊)已開獎的日子如果已經達標,
                    # 代表這組合這輪已經中過了,不是「到期」,直接跳過不列入候選。
                    zero_items = [x for i, x in blocks.get(0, []) if not x['is_future']]
                    zero_hit, _, _ = check_hit(zero_items)
                    if zero_hit:
                        continue

                streak = 0
                three_star_count = 0
                trigger_dates =[]
                hit_blocks =[]

                while curr_b_id in blocks:
                    hist_items =[x for i, x in blocks[curr_b_id] if not x['is_future']]
                    if not hist_items:
                        break
                    hit, h_date, max_stars = check_hit(hist_items)
                    if hit:
                        streak += 1
                        if max_stars >= 3 and not is_non_hit:
                            three_star_count += 1
                        trigger_dates.append(h_date)
                        hit_blocks.append([x['date'] for x in hist_items])
                        curr_b_id += 1
                    else:
                        break

                if streak > best_streak:
                    best_streak = streak
                    best_three_star_count = three_star_count
                    best_trigger_dates = trigger_dates
                    best_hit_blocks = hit_blocks
                    if target_b_id in blocks:
                        best_target_block_dates = [x['date'] for i, x in blocks[target_b_id]]
                    else:
                        best_target_block_dates =[]

                if best_streak >= effective_min_streak:
                    if min_streak_input == 0:
                        effective_min_streak = best_streak
                    results_list.append({
                        'mode': analysis_mode,
                        'pred_range': pred_range,
                        'streak': best_streak,
                        'three_star_count': best_three_star_count,
                        'M': 1,
                        'C_list': c_tuple,
                        'pillars': pillars,
                        'max_val': max_val,
                        'min_hit_req': min_hit_req,
                        'sum_mode': False,
                        'cyclic': False,
                        'ref_dir': 0,
                        'latest_occ': total_periods - 1,
                        'latest_pred_nums': list(c_tuple),
                        'trigger_dates': best_trigger_dates[::-1],
                        'hit_blocks': best_hit_blocks[::-1],
                        'target_block_dates': best_target_block_dates,
                        'is_tail_match': is_tail_match,
                        'weekdays': weekdays,
                        'n_period_enable': n_period_enable,
                        'n_period_gap': n_period_gap,
                        'is_nurture': is_nurture,
                        'is_non_hit': is_non_hit
                    })

        elif analysis_mode in[0, 1, 8]:
            for X in range(1, max_val + 1):
                if progress_callback: progress_callback(X / max_val)

                max_px = balls_cnt + (1 if params['has_special'] else 0)
                px_list = range(max_px) if is_fixed_pos else [-1]

                for P_X in px_list:
                    if P_X == -1:
                        occurrences = get_occurrences_by_set(X)
                    else:
                        occurrences = get_occurrences_by_pos(P_X, X)

                    if len(occurrences) < effective_min_streak: continue

                    for latest_occ_idx in range(len(occurrences)-1, -1, -1):
                        if latest_occ_idx + 1< effective_min_streak: break

                        latest_occ = occurrences[latest_occ_idx]
                        if pred_range == 3: M = total_periods - 1 - latest_occ
                        elif pred_range == 4: M = total_periods - 2 - latest_occ
                        else: M = total_periods - latest_occ

                        if M < 1: continue
                        if M > 15: break

                        # 熱門拖牌的「只找下1期」必須先讓 M=1 的原始資料產生,
                        # 再由外層開關做第二層過濾;不能在 2/3 期到期模式提前排除 M=1。
                        if analysis_mode != 1:
                            if pred_range == 3 and M < 2: continue
                            if pred_range == 4 and M < 3: continue

                        if analysis_mode == 1:
                            step_values = [1, -1, 10, -10] if is_step_advance else [0]
                            for step_val in step_values:
                                history_diffs =[]
                                broken = False
                                for i in range(latest_occ_idx, -1, -1):
                                    t_idx = occurrences[i]
                                    k = latest_occ_idx - i
                                    if i == latest_occ_idx:
                                        history_diffs.append("PENDING")
                                    else:
                                        t_set = helper_get_target_set(t_idx, M)
                                        if t_set is None:
                                            broken = True; break
                                        # 步步進擊:歷史第 k 個觸發點的實際命中值,先位移 k*step_val
                                        # 正規化回候選 c_tuple(第0點)的空間,後面才能一律用同一組
                                        # 固定 c_tuple 直接比對每一個歷史點,不必個別調整比對式。
                                        off = k * step_val
                                        if special_tiandi_mode:
                                            win = _special_tiandi_window(t_idx, M)
                                            if win is None:
                                                broken = True; break
                                            if off:
                                                win = [({n + off for n in inner}, {n + off for n in special}) for inner, special in win]
                                            history_diffs.append(win)
                                        elif is_tail_match:
                                            history_diffs.append({(x % 10 + off) % 10 for x in t_set})
                                        else:
                                            history_diffs.append({x + off for x in t_set} if off else t_set)

                                if broken or len(history_diffs) < effective_min_streak: continue

                                def _build_special_tiandi_hot_candidates(first_window, history_windows):
                                    # 特殊天地碰熱門拖牌核心:候選組合必須先符合
                                    # 「特別號 1 星 + 正碼至少 (星數-1) 隻」。
                                    nonlocal combo_guard_was_used
                                    c_pool = list(range(1, max_val + 1))
                                    inner_set, special_set = _special_tiandi_window_union(first_window)
                                    freq = Counter()
                                    lookback = max(60, effective_min_streak + 30)
                                    for win in history_windows[1:min(len(history_windows), lookback)]:
                                        if not win:
                                            continue
                                        inner_w, special_w = _special_tiandi_window_union(win)
                                        for n in set(inner_w) | set(special_w):
                                            freq[n] += 1

                                    priority = []
                                    for n in sorted(special_set):
                                        if n not in priority:
                                            priority.append(n)
                                    for n in sorted(inner_set, key=lambda x: (-freq.get(x, 0), x)):
                                        if n not in priority:
                                            priority.append(n)
                                    for n, _ in freq.most_common(max(max_val, 30)):
                                        if n not in priority:
                                            priority.append(n)
                                    for n in c_pool:
                                        if n not in priority:
                                            priority.append(n)

                                    if pick_count <= 4:
                                        pool = c_pool
                                        source_limit = None
                                    else:
                                        combo_guard_was_used = True
                                        pool = priority[:min(len(priority), 22)]
                                        source_limit = combo_source_limit

                                    cand = []
                                    combo_iter = combinations(pool, pick_count)
                                    if source_limit:
                                        combo_iter = islice(combo_iter, source_limit)
                                    for tup in combo_iter:
                                        ok, _ = _special_tiandi_success_for_window(tup, first_window)
                                        if ok:
                                            cand.append(tuple(sorted(tup)))

                                    # 若完整 pool 被限量切掉,強制補一些「特別號 + 正碼」的組合,避免好牌被切掉。
                                    if pick_count > 1 and special_set and inner_set:
                                        add_cap = max(combo_candidate_limit * 2, 1000)
                                        added = 0
                                        fill_pool = priority[:min(len(priority), 26)]
                                        for sp in sorted(special_set):
                                            if sp not in fill_pool:
                                                continue
                                            inner_pool = [n for n in fill_pool if n != sp]
                                            need = pick_count - 1
                                            if need < 1 or len(inner_pool) < need:
                                                continue
                                            for fill in islice(combinations(inner_pool, need), 500):
                                                tup = tuple(sorted((sp,) + fill))
                                                ok, _ = _special_tiandi_success_for_window(tup, first_window)
                                                if ok:
                                                    cand.append(tup)
                                                    added += 1
                                                    if added >= add_cap:
                                                        break
                                            if added >= add_cap:
                                                break
                                    return list(dict.fromkeys(cand))

                                def _build_hot_number_candidates_guarded(first_h_cs, history_diffs):
                                    # 熱門拖牌核心反閃退快篩:
                                    # 小選號數量維持原本完整核心;選號數量大時用「第一段命中條件 + 近期頻率池」限量。
                                    nonlocal combo_guard_was_used

                                    first_set = set(first_h_cs or set())
                                    if is_tail_match:
                                        c_pool = list(range(0, 10))
                                    else:
                                        c_pool = list(range(1, max_val + 1))

                                    # 尾數池很小,或選號 <=4,維持原本完整熱門拖牌核心。
                                    if is_tail_match or pick_count <= 4:
                                        candidate_c_lists_pre = list(combinations(c_pool, pick_count))
                                        candidate_c_lists = []
                                        for tup in candidate_c_lists_pre:
                                            hits_val = sum(1 for c in tup if c in first_set)
                                            if is_non_hit:
                                                if hits_val == 0:
                                                    candidate_c_lists.append(tup)
                                            else:
                                                if hits_val >= min_hit_req:
                                                    candidate_c_lists.append(tup)
                                        return candidate_c_lists

                                    # 選號數量 5 以上會爆量,啟用熱門拖牌核心快篩。
                                    combo_guard_was_used = True
                                    freq = Counter()
                                    lookback = max(80, effective_min_streak + 35)
                                    for h_set in history_diffs[1:min(len(history_diffs), lookback)]:
                                        if isinstance(h_set, set):
                                            for n in h_set:
                                                freq[n] += 1

                                    # 第一段命中號碼優先,然後補近期熱門,最後補全域號碼。
                                    target_sorted = sorted(first_set, key=lambda n: (-freq.get(n, 0), n))
                                    freq_sorted = [n for n, _ in freq.most_common(max(max_val, 30))]
                                    pool = []
                                    for n in target_sorted + freq_sorted + c_pool:
                                        if n not in pool:
                                            pool.append(n)

                                    if pick_count <= 6:
                                        pool_limit = min(len(pool), 18)
                                        source_limit = min(combo_source_limit, 2500)
                                        random_try = 700
                                    elif pick_count <= 9:
                                        pool_limit = min(len(pool), 16)
                                        source_limit = min(combo_source_limit, 900)
                                        random_try = 900
                                    else:
                                        pool_limit = min(len(pool), 15)
                                        source_limit = min(combo_source_limit, 500)
                                        random_try = 1000

                                    pool = pool[:pool_limit]
                                    cand_set = set()

                                    # 第一層:穩定 deterministic combinations。
                                    for tup in islice(combinations(pool, pick_count), source_limit):
                                        tup = tuple(sorted(tup))
                                        hits_val = sum(1 for c in tup if c in first_set)
                                        if is_non_hit:
                                            if hits_val == 0:
                                                cand_set.add(tup)
                                        else:
                                            if hits_val >= min_hit_req:
                                                cand_set.add(tup)

                                    # 第二層:強制保留第一段命中條件,避免 islice 截掉好組合。
                                    if not is_non_hit and first_set:
                                        hit_pool = [n for n in target_sorted if n in pool]
                                        fill_pool = [n for n in pool]
                                        max_h = min(pick_count, len(hit_pool))
                                        min_h = min(min_hit_req, max_h)
                                        add_cap = max(combo_candidate_limit * 3, 1200)
                                        added = 0
                                        for h_cnt in range(min_h, max_h + 1):
                                            for hit_part in islice(combinations(hit_pool, h_cnt), 300):
                                                remain_pool = [n for n in fill_pool if n not in hit_part]
                                                need = pick_count - h_cnt
                                                if need < 0 or len(remain_pool) < need:
                                                    continue
                                                for fill_part in islice(combinations(remain_pool, need), 50):
                                                    cand_set.add(tuple(sorted(hit_part + fill_part)))
                                                    added += 1
                                                    if added >= add_cap:
                                                        break
                                                if added >= add_cap:
                                                    break
                                            if added >= add_cap:
                                                break

                                    # 第三層:少量隨機補強,仍需符合第一段命中條件。
                                    if len(pool) >= pick_count:
                                        for _ in range(random_try):
                                            tup = tuple(sorted(random.sample(pool, pick_count)))
                                            hits_val = sum(1 for c in tup if c in first_set)
                                            if is_non_hit:
                                                if hits_val == 0:
                                                    cand_set.add(tup)
                                            else:
                                                if hits_val >= min_hit_req:
                                                    cand_set.add(tup)

                                    return list(cand_set)

                                if len(history_diffs) > 1:
                                    first_h_cs = history_diffs[1]
                                    if special_tiandi_mode:
                                        candidate_c_lists = _build_special_tiandi_hot_candidates(first_h_cs, history_diffs)
                                    else:
                                        candidate_c_lists = _build_hot_number_candidates_guarded(first_h_cs, history_diffs)
                                else:
                                    if is_tail_match:
                                        c_pool = list(range(0, 10))
                                    else:
                                        c_pool = list(range(1, max_val + 1))
                                    if pick_count <= 4 or is_tail_match:
                                        candidate_c_lists = list(combinations(c_pool, pick_count))
                                    else:
                                        combo_guard_was_used = True
                                        candidate_c_lists = list(islice(combinations(c_pool, pick_count), combo_source_limit))

                                candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                                for c_tuple in candidate_c_lists:
                                    if (is_alternate or is_alternate_vip) and len(c_tuple) != 2:
                                        continue

                                    streak = 0
                                    hit_history_c =[]

                                    for k in range(1, len(history_diffs)):
                                        if special_tiandi_mode:
                                            success, valid_cs_in_draw = _special_tiandi_success_for_window(c_tuple, history_diffs[k])
                                        elif is_tail_match:
                                            valid_cs_in_draw =[c for c in c_tuple if c % 10 in history_diffs[k]]
                                            success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                        else:
                                            valid_cs_in_draw =[c for c in c_tuple if c in history_diffs[k]]
                                            success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)

                                        if success:
                                            streak += 1
                                            hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                        else:
                                            break

                                    if streak >= effective_min_streak:
                                        if is_alternate or is_alternate_vip:
                                            if streak < 4:
                                                continue
                                            c1, c2 = c_tuple[0], c_tuple[1]

                                            if is_alternate_vip:
                                                valid_streak = 0
                                                for length in range(streak, 3, -1):
                                                    if check_alt_vip(hit_history_c[:length], c1, c2):
                                                        valid_streak = length
                                                        break
                                                if valid_streak < max(4, effective_min_streak):
                                                    continue
                                                streak = valid_streak
                                            elif is_alternate:
                                                if not check_alt_any(hit_history_c, c1, c2):
                                                    continue

                                        if not verify_miss(c_tuple): continue


                                        trigger_dates =[processed_data[occurrences[latest_occ_idx - k]]['date'] for k in range(streak + 1)]

                                        latest_pred_nums_to_save = list(c_tuple)
                                        if is_tail_match: latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)

                                        results_list.append({
                                            'mode': analysis_mode,
                                            'pred_range': pred_range,
                                            'streak': streak, 'X': X, 'P_X': P_X, 'N': 0, 'P': 0, 'M': M,
                                            'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                            'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                                            'latest_occ': latest_occ, 'latest_pred_nums': latest_pred_nums_to_save,
                                            'trigger_dates': trigger_dates,
                                            'is_tail_match': is_tail_match,
                                            'is_non_hit': is_non_hit,
                                            'is_step_advance': is_step_advance,
                                            'step_val': step_val
                                        })
                        else:
                            for ref_dir in [0, 1]:
                                for N in range(0, max_n + 1):
                                    if N == 0 and ref_dir == 1:
                                        continue

                                    latest_ref = latest_occ - N if ref_dir == 0 else latest_occ + N
                                    if latest_ref < 0 or latest_ref >= total_periods:
                                        continue

                                    max_px_ref = 1 if analysis_mode == 8 else max_px
                                    for P in range(max_px_ref):
                                        history_diffs =[]
                                        broken = False

                                        for i in range(latest_occ_idx, -1, -1):
                                            t_idx = occurrences[i]
                                            ref_idx = t_idx - N if ref_dir == 0 else t_idx + N
                                            if ref_idx < 0 or ref_idx >= total_periods:
                                                broken = True; break

                                            if analysis_mode == 8:
                                                if i == latest_occ_idx:
                                                    history_diffs.append(("PENDING", ref_idx))
                                                else:
                                                    if special_tiandi_mode:
                                                        win = _special_tiandi_window(t_idx, M)
                                                        if win is None:
                                                            broken = True; break
                                                        history_diffs.append((ref_idx, win))
                                                    else:
                                                        t_set = helper_get_target_set(t_idx, M)
                                                        if t_set is None:
                                                            broken = True; break
                                                        history_diffs.append((ref_idx, t_set))
                                            else:
                                                R = processed_data[ref_idx]['list'][P]
                                                if i == latest_occ_idx:
                                                    history_diffs.append("PENDING")
                                                else:
                                                    t_set = helper_get_target_set(t_idx, M)
                                                    if t_set is None:
                                                        broken = True; break

                                                    if special_tiandi_mode:
                                                        win = _special_tiandi_window(t_idx, M)
                                                        if win is None:
                                                            broken = True; break
                                                        history_diffs.append(_special_tiandi_c_window(R, win))
                                                    elif is_tail_drag:
                                                        history_diffs.append((R, t_set))
                                                    elif is_tail_match:
                                                        history_diffs.append((R, {x % 10 for x in t_set}))
                                                    else:
                                                        valid_c_set = set()
                                                        for t_num in t_set:
                                                            if is_sum:
                                                                c = R + t_num
                                                                if is_cyclic: c = (c - 1) % max_val + 1
                                                                valid_c_set.add(c)
                                                            else:
                                                                c = t_num - R
                                                                if is_cyclic:
                                                                    c = c % max_val
                                                                    if c <= 0: c += max_val
                                                                valid_c_set.add(c)
                                                        history_diffs.append(valid_c_set)

                                        if broken or len(history_diffs) < effective_min_streak: continue

                                        if len(history_diffs) > 1:
                                            if special_tiandi_mode:
                                                candidate_c_lists = []
                                                if analysis_mode == 8:
                                                    r_1, win_1 = history_diffs[1]
                                                    ref_list_1 = processed_data[r_1]['list']
                                                    for tup in valid_c_lists:
                                                        pred_nums = [ref_list_1[c] for c in tup if c < len(ref_list_1)]
                                                        ok, _ = _special_tiandi_success_for_window(pred_nums, win_1)
                                                        if ok:
                                                            candidate_c_lists.append(tup)
                                                else:
                                                    cwin_1 = history_diffs[1]
                                                    for tup in valid_c_lists:
                                                        ok, _ = _special_tiandi_success_for_c_tuple(tup, cwin_1)
                                                        if ok:
                                                            candidate_c_lists.append(tup)
                                            elif analysis_mode == 8:
                                                r_1, t_set_1 = history_diffs[1]
                                                ref_list_1 = processed_data[r_1]['list']
                                                candidate_c_lists =[]
                                                for tup in valid_c_lists:
                                                    pred_nums =[ref_list_1[c] for c in tup if c < len(ref_list_1)]
                                                    if is_tail_match:
                                                        combo_tails = {x % 10 for x in pred_nums}
                                                        draw_tails = {x % 10 for x in t_set_1}
                                                        hits_val = len(combo_tails & draw_tails)
                                                    else:
                                                        hits_val = sum(1 for p in pred_nums if p in t_set_1)
                                                    if is_non_hit:
                                                        if hits_val == 0: candidate_c_lists.append(tup)
                                                    else:
                                                        if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                            elif is_tail_drag:
                                                R_1, draw_set_1 = history_diffs[1]
                                                candidate_c_lists =[]
                                                for tup in valid_c_lists:
                                                    p_nums = self.get_pred_nums(R_1, tup, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                                    hits_val = sum(1 for p in p_nums if p in draw_set_1)
                                                    if is_non_hit:
                                                        if hits_val == 0: candidate_c_lists.append(tup)
                                                    else:
                                                        if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                            elif is_tail_match:
                                                R_1, draw_tails_1 = history_diffs[1]
                                                candidate_c_lists =[]
                                                for tup in valid_c_lists:
                                                    p_nums =[]
                                                    for c in tup:
                                                        if is_sum: p = c - R_1
                                                        else: p = R_1 + c
                                                        p_nums.append(p)
                                                    combo_tails = {x % 10 for x in p_nums}
                                                    hits_val = len(combo_tails & draw_tails_1)
                                                    if is_non_hit:
                                                        if hits_val == 0: candidate_c_lists.append(tup)
                                                    else:
                                                        if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                            else:
                                                first_h_cs = history_diffs[1]
                                                if combo_biglotto_mode0_pick2_guard_active and analysis_mode == 0:
                                                    candidate_c_lists = _make_candidate_c_lists_for_history(c_pool, first_h_cs)
                                                else:
                                                    candidate_c_lists =[]
                                                    for tup in valid_c_lists:
                                                        hits_val = sum(1 for c in tup if c in first_h_cs)
                                                        if is_non_hit:
                                                            if hits_val == 0: candidate_c_lists.append(tup)
                                                        else:
                                                            if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                        else:
                                            candidate_c_lists = [] if combo_biglotto_mode0_pick2_guard_active and analysis_mode == 0 else valid_c_lists

                                        candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                                        for c_tuple in candidate_c_lists:
                                            if is_alternate or is_alternate_vip:
                                                if is_tail_drag and len(c_tuple) != 3: continue
                                                elif not is_tail_drag and len(c_tuple) != 2: continue

                                            streak = 0
                                            hit_history_c =[]
                                            for k in range(1, len(history_diffs)):
                                                if special_tiandi_mode:
                                                    if analysis_mode == 8:
                                                        r_k, win_k = history_diffs[k]
                                                        ref_list_k = processed_data[r_k]['list']
                                                        pred_nums_k = [ref_list_k[c] for c in c_tuple if c < len(ref_list_k)]
                                                        success, valid_cs_in_draw = _special_tiandi_success_for_window(pred_nums_k, win_k)
                                                    else:
                                                        success, valid_cs_in_draw = _special_tiandi_success_for_c_tuple(c_tuple, history_diffs[k])
                                                elif analysis_mode == 8:
                                                    r_k, t_set_k = history_diffs[k]
                                                    ref_list_k = processed_data[r_k]['list']
                                                    if is_tail_match:
                                                        valid_cs_in_draw =[]
                                                        for c in c_tuple:
                                                            if c < len(ref_list_k) and (ref_list_k[c] % 10) in {x % 10 for x in t_set_k}:
                                                                valid_cs_in_draw.append(c)
                                                    else:
                                                        valid_cs_in_draw =[c for c in c_tuple if c < len(ref_list_k) and ref_list_k[c] in t_set_k]
                                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                                elif is_tail_drag:
                                                    R_k, draw_set_k = history_diffs[k]
                                                    p_nums = self.get_pred_nums(R_k, c_tuple, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                                    valid_cs_in_draw =[p for p in p_nums if p in draw_set_k]
                                                    if valid_cs_in_draw: valid_cs_in_draw =[p // 10 for p in valid_cs_in_draw]
                                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                                elif is_tail_match:
                                                    R_k, draw_tails_k = history_diffs[k]
                                                    p_nums =[]
                                                    for c in c_tuple:
                                                        if is_sum: p = c - R_k
                                                        else: p = R_k + c
                                                        p_nums.append(p)

                                                    valid_cs_in_draw =[]
                                                    for c in c_tuple:
                                                        if is_sum: p = c - R_k
                                                        else: p = R_k + c
                                                        if p % 10 in draw_tails_k:
                                                            valid_cs_in_draw.append(c)
                                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                                else:
                                                    valid_cs_in_draw =[c for c in c_tuple if c in history_diffs[k]]
                                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)

                                                if success:
                                                    streak += 1
                                                    hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                                else:
                                                    break

                                            if streak >= effective_min_streak:
                                                if is_alternate or is_alternate_vip:
                                                    if streak < 4:
                                                        continue
                                                    if is_tail_drag:
                                                        c1, c2 = c_tuple[1], c_tuple[2]
                                                    else:
                                                        c1, c2 = c_tuple[0], c_tuple[1]

                                                    if is_alternate_vip:
                                                        valid_streak = 0
                                                        for length in range(streak, 3, -1):
                                                            if check_alt_vip(hit_history_c[:length], c1, c2):
                                                                valid_streak = length
                                                                break
                                                        if valid_streak < max(4, effective_min_streak):
                                                            continue
                                                        streak = valid_streak
                                                    elif is_alternate:
                                                        if not check_alt_any(hit_history_c, c1, c2):
                                                            continue

                                                if analysis_mode == 8:
                                                    curr_ref_idx = latest_ref
                                                    ref_list = processed_data[curr_ref_idx]['list']
                                                    pred_nums =[ref_list[c] for c in c_tuple if c < len(ref_list)]
                                                    if is_tail_match:
                                                        pred_nums = expand_tails(pred_nums, max_val)
                                                    latest_pred_nums_to_save = sorted(list(set(pred_nums)))
                                                else:
                                                    l = processed_data[latest_ref]['list']
                                                    curr_R = l[P]
                                                    pred_nums = self.get_pred_nums(curr_R, c_tuple, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                                    latest_pred_nums_to_save = pred_nums
                                                    if is_tail_match and not is_tail_drag:
                                                        latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)

                                                if not verify_miss(latest_pred_nums_to_save): continue


                                                trigger_dates =[processed_data[occurrences[latest_occ_idx - k]]['date'] for k in range(streak + 1)]

                                                results_list.append({
                                                    'mode': analysis_mode,
                                                    'pred_range': pred_range,
                                                    'streak': streak, 'X': X, 'P_X': P_X, 'N': N, 'P': P, 'M': M,
                                                    'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                                    'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': ref_dir,
                                                    'latest_occ': latest_ref, 'latest_pred_nums': latest_pred_nums_to_save,
                                                    'trigger_dates': trigger_dates,
                                                    'is_tail_match': is_tail_match,
                                                    'is_tail_drag': is_tail_drag,
                                                    'is_non_hit': is_non_hit
                                                })
                                                _prune_results_for_biglotto_guard()
        elif analysis_mode in [2, 3, 4]:
            seq_len = analysis_mode
            t_start = max(0, total_periods - 15)
            # 2026-07 修正:原本間隔寫死 for N in [1],導致連拖只能「下一期」觸發。
            # 2026-07 再修正:間隔期數(N)與下M期,改成自動搜尋1~5期,不用手動設定,
            # 也不寫死無上限(避免資料期數一長分析就太慢),由系統自動挑出連續命中最多的組合。

            num_occ = {}
            for n in range(1, max_val + 1):
                num_occ[n] = get_occurrences_by_set(n)

            for t in range(t_start, total_periods):
                if progress_callback: progress_callback((t - t_start) / max(1, total_periods - t_start))

                if pred_range == 3: M = total_periods - 1 - t
                elif pred_range == 4: M = total_periods - 2 - t
                else: M = total_periods - t

                if M < 1 or M > 5: continue
                if pred_range == 3 and M < 2: continue
                if pred_range == 4 and M < 3: continue

                for N in range(1, 6):
                    if t - (seq_len - 1) * N < 0: continue

                    cands_list =[]
                    for step in range(seq_len):
                        idx_step = t - (seq_len - 1 - step) * N
                        lst = processed_data[idx_step]['list']
                        if is_fixed_pos:
                            cands_list.append([(val, p) for p, val in enumerate(lst)])
                        else:
                            cands_list.append([(val, -1) for val in lst])

                    for seq_with_pos in product(*cands_list):
                        seq =[item[0] for item in seq_with_pos]
                        seq_pos = [item[1] for item in seq_with_pos]

                        occurrences =[]
                        last_val = seq[-1]
                        last_pos = seq_pos[-1]

                        for i in num_occ[last_val]:
                            if i > t: break
                            if i >= (seq_len - 1) * N:
                                if last_pos != -1:
                                    if last_pos >= len(processed_data[i]['list']) or processed_data[i]['list'][last_pos] != last_val:
                                        continue

                                match = True
                                for step in range(seq_len - 1, 0, -1):
                                    val = seq[seq_len - 1 - step]
                                    pos = seq_pos[seq_len - 1 - step]
                                    check_idx = i - step * N
                                    if pos == -1:
                                        if val not in processed_data[check_idx]['set']:
                                            match = False
                                            break
                                    else:
                                        if pos >= len(processed_data[check_idx]['list']) or processed_data[check_idx]['list'][pos] != val:
                                            match = False
                                            break
                                if match:
                                    occurrences.append(i)

                        if len(occurrences) < effective_min_streak: continue

                        history_diffs =[]
                        broken = False
                        for idx, occ_t in enumerate(reversed(occurrences)):
                            if idx == 0:
                                history_diffs.append("PENDING")
                            else:
                                t_set = helper_get_target_set(occ_t, M)
                                if t_set is None:
                                    broken = True; break
                                if special_tiandi_mode:
                                    win = _special_tiandi_window(occ_t, M)
                                    if win is None:
                                        broken = True; break
                                    history_diffs.append(win)
                                elif is_tail_match:
                                    history_diffs.append({x % 10 for x in t_set})
                                else:
                                    history_diffs.append(t_set)

                        if broken or len(history_diffs) < effective_min_streak: continue

                        if is_tail_match:
                            c_pool = list(range(0, 10))
                        else:
                            c_pool = list(range(1, max_val + 1))

                        first_h_cs = history_diffs[1] if len(history_diffs) > 1 else None
                        cand_c_lists = _make_candidate_c_lists_for_history(c_pool, first_h_cs)
                        for c_tuple in cand_c_lists:
                            if is_alternate or is_alternate_vip:
                                if len(c_tuple) != 2:
                                    continue

                            streak = 0
                            hit_history_c =[]
                            for k in range(1, len(history_diffs)):
                                if special_tiandi_mode:
                                    success, valid_cs_in_draw = _special_tiandi_success_for_window(c_tuple, history_diffs[k])
                                    hits = len(valid_cs_in_draw)
                                else:
                                    valid_cs_in_draw =[c for c in c_tuple if c in history_diffs[k]]
                                    hits = len(valid_cs_in_draw)
                                    success = (hits == 0) if is_non_hit else (hits >= min_hit_req)
                                if success:
                                    streak += 1
                                    hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                else:
                                    break

                            if streak >= effective_min_streak:
                                if is_alternate or is_alternate_vip:
                                    if streak < 4: continue
                                    c1, c2 = c_tuple[0], c_tuple[1]
                                    if is_alternate_vip:
                                        valid_streak = 0
                                        for length in range(streak, 3, -1):
                                            if check_alt_vip(hit_history_c[:length], c1, c2):
                                                valid_streak = length
                                                break
                                        if valid_streak < max(4, effective_min_streak):
                                            continue
                                        streak = valid_streak
                                    elif is_alternate:
                                        if not check_alt_any(hit_history_c, c1, c2):
                                            continue

                                if not verify_miss(c_tuple): continue


                                trigger_dates = [processed_data[occurrences[-1 - k]]['date'] for k in range(streak + 1)]

                                latest_pred_nums_to_save = list(c_tuple)
                                if is_tail_match: latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)

                                res_dict = {
                                    'mode': analysis_mode,
                                    'pred_range': pred_range,
                                    'streak': streak,
                                    'seq': seq,
                                    'seq_pos': seq_pos,
                                    'N': N, 'M': M,
                                    'C_list': c_tuple,
                                    'max_val': max_val,
                                    'min_hit_req': min_hit_req,
                                    'sum_mode': False, 'cyclic': False, 'ref_dir': 1,
                                    'latest_occ': t,
                                    'latest_pred_nums': latest_pred_nums_to_save,
                                    'trigger_dates': trigger_dates,
                                    'is_tail_match': is_tail_match,
                                    'is_non_hit': is_non_hit
                                }
                                res_dict['X'] = seq[0]
                                res_dict['Y'] = seq[1]
                                if seq_len >= 3: res_dict['Z'] = seq[2]
                                results_list.append(res_dict)

        elif analysis_mode == 5:
            t_start = max(0, total_periods -15)
            is_triple_star = params.get('is_triple_star', False)
            is_dual_incremental_n = params.get('is_dual_incremental_n', False)
            is_dual_cyclic = params.get('is_dual_cyclic', False)

            for t in range(t_start, total_periods):
                if progress_callback: progress_callback((t - t_start) / max(1, total_periods - t_start))

                if pred_range == 3: M = total_periods - 1 - t
                elif pred_range == 4: M = total_periods - 2 - t
                else: M = total_periods - t

                if M < 1 or M > 15: continue
                if pred_range == 3 and M < 2: continue
                if pred_range == 4 and M < 3: continue

                current_list = processed_data[t]['list']

                if is_triple_star:
                    if len(current_list) < 3: continue
                    if is_fixed_pos:
                        cands =[(current_list[i], i, current_list[j], j, current_list[k], k) for i in range(len(current_list)) for j in range(i+1, len(current_list)) for k in range(j+1, len(current_list))]
                    else:
                        cands =[(current_list[i], -1, current_list[j], -1, current_list[k], -1) for i in range(len(current_list)) for j in range(i+1, len(current_list)) for k in range(j+1, len(current_list))]
                else:
                    if len(current_list) < 2: continue
                    if is_fixed_pos:
                        cands = [(current_list[i], i, current_list[j], j, None, -1) for i in range(len(current_list)) for j in range(i+1, len(current_list))]
                    else:
                        cands =[(current_list[i], -1, current_list[j], -1, None, -1) for i in range(len(current_list)) for j in range(i+1, len(current_list))]

                for X_val, P_X_val, Y_val, P_Y_val, Z_val, P_Z_val in cands:
                    occurrences = get_occurrences_for_candidate(
                        X_val, P_X_val, Y_val, P_Y_val, Z_val, P_Z_val, t
                    )

                    if len(occurrences) < effective_min_streak: continue

                    if is_dual_incremental_n or is_dual_cyclic:
                        # 加減遞加N / 允許號碼循環:X,Y(或Z)本身是觸發條件,每次出現的
                        # 數值都相同,所以不能像下面預設邏輯那樣直接拿 X,Y 當基準做加減;
                        # 改成直接用「歷史上每次觸發後,M期實際開出的號碼」本身建立等差
                        # 數列(base c0 + k*N),k 為倒回去第幾次觸發,N 為兩次觸發間的固定級距。
                        raw_vals =[]
                        broken = False
                        for idx, occ_t in enumerate(reversed(occurrences)):
                            if idx == 0:
                                raw_vals.append(None)
                            else:
                                t_set = helper_get_target_set(occ_t, M)
                                if not t_set:
                                    broken = True; break
                                raw_vals.append(t_set)

                        if broken or len(raw_vals) < max(3, effective_min_streak + 1):
                            continue

                        def _dual_wrap(v, _max_val=max_val, _cyclic=is_dual_cyclic):
                            if not _cyclic:
                                return v
                            return (v - 1) % _max_val + 1

                        set1 = raw_vals[1]
                        set2 = raw_vals[2]
                        derived_pairs = set()
                        for v1 in set1:
                            for v2 in set2:
                                n_val = v2 - v1
                                if n_val == 0:
                                    continue
                                c0 = v1 - n_val
                                derived_pairs.add((c0, n_val))

                        derived_pairs = _guard_candidate_c_lists(list(derived_pairs))
                        for c0, n_val in derived_pairs:
                            streak = 0
                            for k in range(1, len(raw_vals)):
                                raw_set_k = raw_vals[k]
                                expected = _dual_wrap(c0 + k * n_val)
                                if is_tail_match:
                                    success = any((expected % 10) == (x % 10) for x in raw_set_k)
                                else:
                                    success = expected in raw_set_k
                                if success:
                                    streak += 1
                                else:
                                    break

                            if streak >= effective_min_streak:
                                final_c = _dual_wrap(c0)
                                c_tuple = (final_c,)
                                if not verify_miss(c_tuple): continue

                                trigger_dates =[processed_data[occurrences[-1 - k]]['date'] for k in range(streak + 1)]
                                latest_pred_nums_to_save = list(c_tuple)
                                if is_tail_match: latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)

                                results_list.append({
                                    'mode': 5,
                                    'pred_range': pred_range,
                                    'streak': streak,
                                    'X': X_val, 'Y': Y_val, 'Z': Z_val,
                                    'P_X': P_X_val, 'P_Y': P_Y_val, 'P_Z': P_Z_val,
                                    'M': M,
                                    'C_list': c_tuple,
                                    'max_val': max_val,
                                    'min_hit_req': min_hit_req,
                                    'sum_mode': False, 'cyclic': is_dual_cyclic, 'ref_dir': 0,
                                    'latest_occ': t,
                                    'latest_pred_nums': latest_pred_nums_to_save,
                                    'trigger_dates': trigger_dates,
                                    'is_tail_match': is_tail_match,
                                    'is_triple_star': is_triple_star,
                                    'is_non_hit': is_non_hit,
                                    'is_dual_incremental_n': is_dual_incremental_n,
                                    'is_dual_cyclic': is_dual_cyclic,
                                    'dual_step_val': n_val,
                                    'dual_base_raw': c0
                                })
                        continue

                    history_diffs =[]
                    broken = False
                    for idx, occ_t in enumerate(reversed(occurrences)):
                        if idx == 0:
                            history_diffs.append("PENDING")
                        else:
                            t_set = helper_get_target_set(occ_t, M)
                            if t_set is None:
                                broken = True; break
                            if special_tiandi_mode:
                                win = _special_tiandi_window(occ_t, M)
                                if win is None:
                                    broken = True; break
                                history_diffs.append(win)
                            elif is_tail_match:
                                history_diffs.append({x % 10 for x in t_set})
                            else:
                                history_diffs.append(t_set)

                    if broken or len(history_diffs) < effective_min_streak: continue

                    if len(history_diffs) > 1:
                        first_h_cs = history_diffs[1]
                        if is_tail_match:
                            c_pool = list(range(0, 10))
                        else:
                            c_pool = list(range(1, max_val + 1))
                        cand_c_lists_pre = list(combinations(c_pool, pick_count))
                        cand_c_lists =[]
                        for tup in cand_c_lists_pre:
                            if special_tiandi_mode:
                                ok, _ = _special_tiandi_success_for_window(tup, first_h_cs)
                                if ok:
                                    cand_c_lists.append(tup)
                                continue
                            hits_val = sum(1 for c in tup if c in first_h_cs)
                            if is_non_hit:
                                if hits_val == 0: cand_c_lists.append(tup)
                            else:
                                if hits_val >= min_hit_req: cand_c_lists.append(tup)
                    else:
                        if is_tail_match:
                            c_pool = list(range(0, 10))
                        else:
                            c_pool = list(range(1, max_val + 1))
                        cand_c_lists = list(combinations(c_pool, pick_count))

                    cand_c_lists = _guard_candidate_c_lists(cand_c_lists)
                    for c_tuple in cand_c_lists:
                        streak = 0
                        for k in range(1, len(history_diffs)):
                            if special_tiandi_mode:
                                success, valid_cs_in_draw = _special_tiandi_success_for_window(c_tuple, history_diffs[k])
                            else:
                                hits = sum(1 for c in c_tuple if c in history_diffs[k])
                                success = (hits == 0) if is_non_hit else (hits >= min_hit_req)
                            if success:
                                streak += 1
                            else:
                                break

                        if streak >= effective_min_streak:
                            if not verify_miss(c_tuple): continue


                            trigger_dates =[processed_data[occurrences[-1 - k]]['date'] for k in range(streak + 1)]

                            latest_pred_nums_to_save = list(c_tuple)
                            if is_tail_match: latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)

                            results_list.append({
                                'mode': 5,
                                'pred_range': pred_range,
                                'streak': streak,
                                'X': X_val, 'Y': Y_val, 'Z': Z_val,
                                'P_X': P_X_val, 'P_Y': P_Y_val, 'P_Z': P_Z_val,
                                'M': M,
                                'C_list': c_tuple,
                                'max_val': max_val,
                                'min_hit_req': min_hit_req,
                                'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                                'latest_occ': t,
                                'latest_pred_nums': latest_pred_nums_to_save,
                                'trigger_dates': trigger_dates,
                                'is_tail_match': is_tail_match,
                                'is_triple_star': is_triple_star,
                                'is_non_hit': is_non_hit
                            })

        elif analysis_mode in (7, 18):
            # mode 18「號碼相互加減」是從 mode 7 拆出來的獨立版路:
            # 恆等於過去 mode 7 內「號碼相互加減」開關=True 的情況;
            # mode 7 本身不再支援這個開關(移到 mode 18)。
            is_weekly_n_add_sub = (analysis_mode == 18)

            if is_weekly_n_add_sub:
                # 號碼相互加減(粉紅色+-藍色)。
                # 合數模式沿用其他版路的「參數減基準」邏輯:
                # 先算互加/互減基準,再用「合數參數 - 基準」得到答案。
                is_cyclic_weekly = bool(params.get('is_cyclic', False))
                is_tail_match_weekly = bool(params.get('is_tail_match', False))
                is_tail_drag_weekly = bool(params.get('is_tail_drag', False))
                n_list = list(params.get('interval_list', [params.get('interval_step', 1)]))
                n_list = [max(1, int(n)) for n in n_list if int(n) > 0]
                n_list = sorted(set(n_list)) or [1]

                blue_positions = range(5)
                # 號碼相互加減支援輪流模式/嚴格輪流。
                # 一般輪流:最近4個有效命中區段 A-B-A-B 或 B-A-B-A。
                # 嚴格輪流:整段驗證歷史都必須保持 A-B-A-B / B-A-B-A。
                is_alternate_weekly = bool(params.get('is_alternate', False))
                is_alternate_vip_weekly = bool(params.get('is_alternate_vip', False))
                # 輪流/嚴格輪流的定義是兩個候選交替命中;不能沿用多星同時命中的門檻。
                weekly_alt_hit_req = 1 if (is_alternate_weekly or is_alternate_vip_weekly) and not is_non_hit else min_hit_req
                is_staircase = bool(params.get('is_staircase', False))
                max_p = balls_cnt - 1 + (1 if params['has_special'] else 0)
                if max_p < 0:
                    return [], next_draw_data

                if is_staircase:
                    stair_max_p = balls_cnt - 1
                    if stair_max_p > 0:
                        stair_cycle = list(range(stair_max_p + 1)) + list(range(stair_max_p - 1, 0, -1))
                    else:
                        stair_cycle = [0]
                    trigger_offsets = range(len(stair_cycle))
                else:
                    stair_cycle = None
                    trigger_offsets = range(max_p + 1)

                max_M_n = 150
                if pred_range == 3:
                    latest_target_idx = total_periods - 1
                    min_M_n = 2
                elif pred_range == 4:
                    latest_target_idx = total_periods - 2
                    min_M_n = 3
                else:
                    latest_target_idx = total_periods
                    min_M_n = 1

                total_weekly_work = max(1, len(list(blue_positions)) * len(n_list) * max(1, len(list(trigger_offsets))) * max(1, max_M_n - min_M_n))
                weekly_done = 0
                for blue_pos in blue_positions:
                    for n_period in n_list:
                        for stair_offset in trigger_offsets:
                            for M in range(min_M_n, max_M_n):
                                weekly_done += 1
                                if progress_callback and (weekly_done == 1 or weekly_done % 40 == 0 or weekly_done == total_weekly_work):
                                    progress_callback(min(0.97, weekly_done / float(total_weekly_work)))
                                # Mode 18 的「間隔期數」定義:控制「觸發點」多久出現一次。
                                # 例如間隔=1:每一期都有粉紅觸發點;間隔=2:中間空一格,
                                # 也就是第N期觸發、隔1期、第N+2期再觸發;以此類推。
                                # 粉紅觸發點與藍色配對仍固定為「下一期」,間隔不再被誤當成
                                # 粉紅→藍色的位移。
                                latest_blue_idx = latest_target_idx - M
                                latest_trigger_idx = latest_blue_idx - 1
                                if latest_trigger_idx < 0 or latest_blue_idx < 0:
                                    continue

                                # 先把歷史每一格的「互加/互減原始基準」存起來。
                                # 重要:後面的歷史資料迴圈可能因資料不足而設定 broken=True,
                                # 因此每一次 M / 間隔組合都必須重新初始化,避免區域變數未賦值。
                                broken = False
                                history_pairs = []
                                # 最新「粉紅→藍色」這一組是目前要拿來預測下一期的待測組,
                                # 不能拿未開出的 target 當歷史連莊驗證。
                                # 歷史驗證要從上一個觸發點開始,再依「間隔期數」往前跳。
                                # 例如間隔=2:目前組 A→B,上一組從 A 往前 2 期,再配下一期 B。
                                for k in range(1, total_periods + 1):
                                    trigger_idx = latest_trigger_idx - k * n_period
                                    blue_idx = trigger_idx + 1
                                    target_idx = blue_idx + M
                                    if trigger_idx < 0:
                                        break
                                    if blue_idx < 0 or blue_idx >= total_periods:
                                        broken = True
                                        break
                                    if target_idx < 0 or target_idx >= total_periods:
                                        break

                                    trigger_list = processed_data[trigger_idx]['list']
                                    blue_list = processed_data[blue_idx]['list']
                                    if not blue_list:
                                        broken = True
                                        break

                                    if is_staircase:
                                        trigger_pos = stair_cycle[(stair_offset + k) % len(stair_cycle)]
                                    else:
                                        trigger_pos = stair_offset
                                    if trigger_pos >= len(trigger_list) or blue_pos >= len(blue_list):
                                        broken = True
                                        break

                                    trigger_val = int(trigger_list[trigger_pos])
                                    blue_val = int(blue_list[blue_pos])
                                    raw_add = trigger_val + blue_val
                                    raw_sub = abs(trigger_val - blue_val)
                                    t_set = helper_get_target_set(target_idx, 0)
                                    if t_set is None:
                                        broken = True
                                        break
                                    history_pairs.append({
                                        'trigger_idx': trigger_idx, 'blue_idx': blue_idx, 'target_idx': target_idx,
                                        'trigger_pos': trigger_pos, 'blue_pos': blue_pos,
                                        'trigger_val': trigger_val, 'blue_val': blue_val,
                                        'raw_add': raw_add, 'raw_sub': raw_sub, 'target_set': set(t_set),
                                    })

                                if broken and len(history_pairs) < effective_min_streak:
                                    continue
                                if len(history_pairs) < effective_min_streak:
                                    continue

                                # 合數模式:從第一個歷史驗證點反推可能的「合數參數」。
                                # target = 合數參數 - raw,所以合數參數 = target + raw。
                                if is_sum:
                                    first = history_pairs[0]
                                    sum_base_candidates = set()
                                    for target_num in first['target_set']:
                                        for raw in (first['raw_add'], first['raw_sub']):
                                            c_val = int(target_num) + int(raw)
                                            if 1 <= c_val <= max_val * 2:
                                                sum_base_candidates.add(c_val)
                                else:
                                    sum_base_candidates = [None]

                                head_range = range(0, 10) if is_tail_drag_weekly else [None]
                                eff_tail_match = is_tail_match_weekly or is_tail_drag_weekly
                                for sum_base in (sorted(sum_base_candidates) if is_sum else sum_base_candidates):
                                  for head_val in head_range:
                                    streak = 0
                                    hit_history = []
                                    for ent in history_pairs:
                                        add_val, sub_val = weekly_mutual_add_sub_values(
                                            ent['trigger_val'], ent['blue_val'], is_sum, max_val, sum_base,
                                            cyclic=is_cyclic_weekly, tail_match=eff_tail_match
                                        )
                                        if is_tail_drag_weekly:
                                            # 取尾配頭:互加/互減先得到尾差,套上固定頭數 head_val 組成完整號碼。
                                            add_val = (head_val * 10 + add_val % 10) if add_val is not None else None
                                            sub_val = (head_val * 10 + sub_val % 10) if sub_val is not None else None
                                            add_val = add_val if (add_val is not None and 1 <= add_val <= max_val) else None
                                            sub_val = sub_val if (sub_val is not None and 1 <= sub_val <= max_val) else None

                                        if is_tail_match_weekly and not is_tail_drag_weekly:
                                            # 尾數模式(未取尾配頭):只比對個位數尾數是否命中,不要求整個號碼落在合法範圍。
                                            target_tails = {v % 10 for v in ent['target_set']}
                                            hits = {v for v in (add_val, sub_val) if v is not None and (v % 10) in target_tails}
                                            branch_hits = []
                                            if add_val is not None and (add_val % 10) in target_tails:
                                                branch_hits.append('add')
                                            if sub_val is not None and (sub_val % 10) in target_tails:
                                                branch_hits.append('sub')
                                        else:
                                            candidates = {v for v in (add_val, sub_val) if v is not None}
                                            hits = candidates.intersection(ent['target_set'])

                                            # 輪流/嚴格輪流不能把「互加結果的數字」和「互減結果的數字」
                                            # 當成固定的兩顆候選號碼;合數模式下兩個結果會隨每一期的粉紅/藍色
                                            # 數字變動。因此改以「互加分支/互減分支」本身作為 A/B。
                                            branch_hits = []
                                            if add_val is not None and add_val in ent['target_set']:
                                                branch_hits.append('add')
                                            if sub_val is not None and sub_val in ent['target_set']:
                                                branch_hits.append('sub')

                                        success = (len(hits) == 0) if is_non_hit else (
                                            bool(branch_hits) if (is_alternate_weekly or is_alternate_vip_weekly) else (len(hits) >= weekly_alt_hit_req)
                                        )
                                        if success:
                                            streak += 1
                                            hit_history.append({
                                                **ent,
                                                'candidates': tuple(sorted({v for v in (add_val, sub_val) if v is not None})),
                                                'branch_hits': tuple(branch_hits),
                                            })
                                        else:
                                            break

                                    if streak < effective_min_streak:
                                        continue

                                    # 輪流模式:A=互加命中、B=互減命中。
                                    # 一般輪流只要求最近4期形成 A-B-A-B / B-A-B-A;
                                    # 嚴格輪流則整段連莊歷史都必須維持同樣交替。
                                    if (is_alternate_weekly or is_alternate_vip_weekly) and not is_non_hit:
                                        if streak < max(4, effective_min_streak):
                                            continue
                                        branch_seq = []
                                        bad_branch = False
                                        for ent in hit_history:
                                            bh = ent.get('branch_hits', ())
                                            # 同一期同時互加、互減都中,無法判定輪流方向。
                                            if len(bh) != 1:
                                                bad_branch = True
                                                break
                                            branch_seq.append(bh[0])
                                        if bad_branch or len(branch_seq) < 4:
                                            continue

                                        def _branch_alternates(seq, require_all):
                                            check_seq = seq if require_all else seq[:4]
                                            if len(check_seq) < 4:
                                                return False
                                            return all(check_seq[i] != check_seq[i-1] for i in range(1, len(check_seq)))

                                        if is_alternate_vip_weekly:
                                            if not _branch_alternates(branch_seq, True):
                                                continue
                                        else:
                                            if not _branch_alternates(branch_seq, False):
                                                continue

                                    latest_trigger_list = processed_data[latest_trigger_idx]['list']
                                    latest_blue_list = processed_data[latest_blue_idx]['list'] if latest_blue_idx < total_periods else []
                                    if not latest_blue_list or blue_pos >= len(latest_blue_list):
                                        continue
                                    if is_staircase:
                                        latest_trigger_pos = stair_cycle[stair_offset % len(stair_cycle)]
                                    else:
                                        latest_trigger_pos = stair_offset
                                    if latest_trigger_pos >= len(latest_trigger_list):
                                        continue

                                    latest_trigger_val = int(latest_trigger_list[latest_trigger_pos])
                                    latest_blue_val = int(latest_blue_list[blue_pos])
                                    latest_add, latest_sub = weekly_mutual_add_sub_values(
                                        latest_trigger_val, latest_blue_val, is_sum, max_val, sum_base,
                                        cyclic=is_cyclic_weekly, tail_match=eff_tail_match
                                    )
                                    if is_tail_drag_weekly:
                                        latest_add = (head_val * 10 + latest_add % 10) if latest_add is not None else None
                                        latest_sub = (head_val * 10 + latest_sub % 10) if latest_sub is not None else None
                                        latest_add = latest_add if (latest_add is not None and 1 <= latest_add <= max_val) else None
                                        latest_sub = latest_sub if (latest_sub is not None and 1 <= latest_sub <= max_val) else None
                                    latest_candidates = {v for v in (latest_add, latest_sub) if v is not None}
                                    if not latest_candidates:
                                        continue
                                    latest_pred_nums = sorted(latest_candidates)
                                    if not is_non_hit and len(latest_pred_nums) < weekly_alt_hit_req:
                                        continue
                                    if not verify_miss(latest_pred_nums):
                                        continue

                                    trigger_dates = []
                                    for k in range(streak + 1):
                                        idx_t = latest_trigger_idx - k * n_period
                                        if 0 <= idx_t < total_periods:
                                            trigger_dates.append(processed_data[idx_t]['date'])

                                    results_list.append({
                                        'mode': analysis_mode, 'pred_range': pred_range, 'streak': streak,
                                        'X': latest_trigger_val, 'P_X': latest_trigger_pos,
                                        'N': n_period, 'P': latest_trigger_pos, 'M': M, 'interval': n_period,
                                        'C_list': (sum_base,) if is_sum else tuple(latest_pred_nums),
                                        'max_val': max_val, 'min_hit_req': min_hit_req,
                                        'sum_mode': is_sum, 'cyclic': is_cyclic_weekly, 'ref_dir': 0,
                                        'latest_occ': latest_trigger_idx, 'latest_pred_nums': latest_pred_nums,
                                        'trigger_dates': trigger_dates,
                                        'is_staircase': is_staircase, 'stair_offset': stair_offset,
                                        'is_step_advance': False, 'step_val': 0,
                                        'is_incremental_n': False, 'incremental_n_val': 0,
                                        'is_weekly_n_add_sub': True, 'weekly_n_period': n_period,
                                        'is_alternate': is_alternate_weekly, 'is_alternate_vip': is_alternate_vip_weekly,
                                        'weekly_blue_pos': blue_pos, 'weekly_trigger_pos': latest_trigger_pos,
                                        'weekly_sum_base': sum_base if is_sum else None,
                                        'weekly_latest_raw_add': latest_trigger_val + latest_blue_val,
                                        'weekly_latest_raw_sub': abs(latest_trigger_val - latest_blue_val),
                                        'is_tail_match': is_tail_match_weekly, 'is_tail_drag': is_tail_drag_weekly,
                                        'weekly_tail_drag_head': head_val if is_tail_drag_weekly else None,
                                        'is_non_hit': is_non_hit,
                                    })

            if not is_weekly_n_add_sub:
                # 一般分析也固定從參數取得 interval_list,避免先前使用前未初始化。
                interval_list = params.get('interval_list', [params.get('interval_step', 1)])
                try:
                    interval_list = [max(1, int(n)) for n in interval_list if int(n) > 0]
                except Exception:
                    interval_list = [1]
                interval_list = sorted(set(interval_list)) or [1]

                is_alternate = params.get('is_alternate', False)
                is_alternate_vip = params.get('is_alternate_vip', False)
                is_staircase = params.get('is_staircase', False)
                is_step_advance = params.get('is_step_advance', False)
                is_incremental_n = params.get('is_incremental_n', False)
                max_M = 150
    
                max_p = balls_cnt - 1 + (1 if params['has_special'] else 0)
                if is_staircase:
                    if max_p > 0:
                        cycle = list(range(max_p + 1)) + list(range(max_p - 1, 0, -1))
                    else:
                        cycle =[0]
                    iterator = range(len(cycle))
                else:
                    iterator = range(max_p + 1)
    
                step_values =[1, -1, 10, -10] if is_step_advance else[0]
    
                for interval in interval_list:
                    for P_or_offset in iterator:
                        for M in range(1, max_M):
                            if progress_callback and P_or_offset == 0 and M % 10 == 0:
                                progress_callback(M / float(max_M))
    
                            if pred_range == 3:
                                latest_target_idx = total_periods - 1
                                if M < 2: continue
                            elif pred_range == 4:
                                latest_target_idx = total_periods - 2
                                if M < 3: continue
                            else:
                                latest_target_idx = total_periods
    
                            latest_ref_idx = latest_target_idx - M
    
                            if latest_ref_idx < 0:
                                continue
    
                            if latest_target_idx - (effective_min_streak - 1) * interval < 0:
                                break
    
                            if is_incremental_n and not is_tail_drag and not is_tail_match and not special_tiandi_mode and not is_staircase and not is_non_hit:
                                # 定點加減遞加N:不暴力窮舉所有可能的N,而是從歷史第1、2個
                                # 觸發點的實際差值反推遞增級距N與基準候選值c0(2點即可決定一條
                                # 等差數列),再往回驗證後續觸發點是否延續同一級距,效率遠優於
                                # 對每個N值各跑一次完整的history_diffs。
                                raw_diffs = []
                                broken = False
                                for k in range(total_periods):
                                    t_idx = latest_target_idx - k * interval
                                    r_idx = latest_ref_idx - k * interval
                                    if r_idx < 0:
                                        break
                                    R = processed_data[r_idx]['list'][P_or_offset]
                                    if k == 0:
                                        raw_diffs.append(("PENDING", R))
                                    else:
                                        if t_idx < 0 or t_idx >= total_periods:
                                            broken = True; break
                                        t_set = helper_get_target_set(t_idx, 0)
                                        if t_set is None:
                                            broken = True; break
                                        raw_set = set()
                                        for t_num in t_set:
                                            if is_sum:
                                                c = R + t_num
                                                if is_cyclic: c = (c - 1) % max_val + 1
                                            else:
                                                c = t_num - R
                                                if is_cyclic:
                                                    c = c % max_val
                                                    if c <= 0: c += max_val
                                            raw_set.add(c)
                                        raw_diffs.append((raw_set, R))
    
                                if broken or len(raw_diffs) < max(3, effective_min_streak + 1):
                                    continue
    
                                set1, _ = raw_diffs[1]
                                set2, _ = raw_diffs[2]
                                derived_pairs = set()
                                for c1 in set1:
                                    for c2 in set2:
                                        # N 定義為「越往回看,實際命中值比基準多出多少」:
                                        # k=1(最近一次)的offset是 c0+N,k=2(再往前一次)是 c0+2N,
                                        # 所以由兩點反推 N = c2-c1,c0 = c1-N。
                                        # 這樣 N 才會跟畫面上「-30 再加3」的直覺方向一致(N=+3),
                                        # 而不是反過來變成往未來遞減的負數。
                                        n_val = c2 - c1
                                        if n_val == 0:
                                            continue
                                        c0 = c1 - n_val
                                        derived_pairs.add((c0, n_val))
    
                                derived_pairs = _guard_candidate_c_lists(list(derived_pairs))
                                for c0, n_val in derived_pairs:
                                    streak = 0
                                    for k in range(1, len(raw_diffs)):
                                        raw_set_k, _ = raw_diffs[k]
                                        if (c0 + k * n_val) in raw_set_k:
                                            streak += 1
                                        else:
                                            break
    
                                    if streak >= effective_min_streak:
                                        c_tuple = (c0,)
                                        curr_P = P_or_offset
                                        l = processed_data[latest_ref_idx]['list']
                                        curr_R = l[curr_P]
                                        pred_nums = self.get_pred_nums(curr_R, c_tuple, max_val, is_sum, is_cyclic, False, False)
    
                                        if not verify_miss(pred_nums): continue
    
                                        trigger_dates =[processed_data[latest_ref_idx - k * interval]['date'] for k in range(streak + 1)]
    
                                        results_list.append({
                                            'mode': 7,
                                            'pred_range': pred_range,
                                            'streak': streak, 'X': curr_R, 'P_X': curr_P, 'N': 0, 'P': curr_P, 'M': M,
                                            'interval': interval,
                                            'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                            'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                            'latest_occ': latest_ref_idx, 'latest_pred_nums': pred_nums,
                                            'trigger_dates': trigger_dates,
                                            'is_staircase': False,
                                            'stair_offset': 0,
                                            'is_step_advance': False,
                                            'step_val': 0,
                                            'is_incremental_n': True,
                                            'incremental_n_val': n_val,
                                            'is_tail_match': False,
                                            'is_tail_drag': False,
                                            'is_non_hit': is_non_hit
                                        })
                                continue
    
                            for step_val in step_values:
                                history_diffs =[]
                                broken = False
    
                                for k in range(total_periods):
                                    t_idx = latest_target_idx - k * interval
                                    r_idx = latest_ref_idx - k * interval
    
                                    if r_idx < 0:
                                        break
    
                                    if is_staircase:
                                        P_k = cycle[(P_or_offset + k) % len(cycle)]
                                    else:
                                        P_k = P_or_offset
    
                                    R = processed_data[r_idx]['list'][P_k]
    
                                    if k == 0:
                                        history_diffs.append("PENDING")
                                    else:
                                        if t_idx < 0 or t_idx >= total_periods:
                                            broken = True; break
    
                                        t_set = helper_get_target_set(t_idx, 0)
                                        if t_set is None:
                                            broken = True; break
    
                                        if special_tiandi_mode:
                                            win = _special_tiandi_window(t_idx, 0)
                                            if win is None:
                                                broken = True; break
                                            history_diffs.append(_special_tiandi_c_window_with_step(R, win, k * step_val))
                                        elif is_tail_drag:
                                            history_diffs.append((R, t_set, k))
                                        elif is_tail_match:
                                            history_diffs.append((R, {x % 10 for x in t_set}, k))
                                        else:
                                            valid_c_set = set()
                                            for t_num in t_set:
                                                if is_sum:
                                                    c = R + t_num
                                                    if is_cyclic: c = (c - 1) % max_val + 1
                                                    c = c + k * step_val
                                                    valid_c_set.add(c)
                                                else:
                                                    c = t_num - R
                                                    if is_cyclic:
                                                        c = c % max_val
                                                        if c <= 0: c += max_val
                                                    c = c + k * step_val
                                                    valid_c_set.add(c)
                                            history_diffs.append((valid_c_set, k))
    
                                if broken or len(history_diffs) < effective_min_streak:
                                    continue
    
                                if len(history_diffs) > 1:
                                    if special_tiandi_mode:
                                        first_cwin = history_diffs[1]
                                        candidate_c_lists = []
                                        for tup in valid_c_lists:
                                            ok, _ = _special_tiandi_success_for_c_tuple(tup, first_cwin)
                                            if ok:
                                                candidate_c_lists.append(tup)
                                    elif is_tail_drag:
                                        R_1, draw_set_1, k_1 = history_diffs[1]
                                        candidate_c_lists =[]
                                        for tup in valid_c_lists:
                                            c_k_list =[tup[0] - k_1 * step_val] + list(tup[1:]) if is_step_advance else tup
                                            p_nums = self.get_pred_nums(R_1, c_k_list, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                            hits_val = sum(1 for p in p_nums if p in draw_set_1)
                                            if is_non_hit:
                                                if hits_val == 0: candidate_c_lists.append(tup)
                                            else:
                                                if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                    elif is_tail_match:
                                        R_1, draw_tails_1, k_1 = history_diffs[1]
                                        candidate_c_lists =[]
                                        for tup in valid_c_lists:
                                            p_nums =[]
                                            for c in tup:
                                                actual_c = c - k_1 * step_val
                                                if is_sum: p = actual_c - R_1
                                                else: p = R_1 + actual_c
                                                p_nums.append(p)
                                            combo_tails = {x % 10 for x in p_nums}
                                            hits_val = len(combo_tails & draw_tails_1)
                                            if is_non_hit:
                                                if hits_val == 0: candidate_c_lists.append(tup)
                                            else:
                                                if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                    else:
                                        first_h_cs, k_1 = history_diffs[1]
                                        candidate_c_lists =[]
                                        for tup in valid_c_lists:
                                            hits_val = sum(1 for c in tup if c in first_h_cs)
                                            if is_non_hit:
                                                if hits_val == 0: candidate_c_lists.append(tup)
                                            else:
                                                if hits_val >= min_hit_req: candidate_c_lists.append(tup)
                                else:
                                    candidate_c_lists = valid_c_lists
    
                                candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                                for c_tuple in candidate_c_lists:
                                    if is_alternate or is_alternate_vip:
                                        if is_tail_drag and len(c_tuple) != 3: continue
                                        elif not is_tail_drag and len(c_tuple) != 2: continue
    
                                    streak = 0
                                    hit_history_c =[]
    
                                    for k_idx in range(1, len(history_diffs)):
                                        if special_tiandi_mode:
                                            success, valid_cs_in_draw = _special_tiandi_success_for_c_tuple(c_tuple, history_diffs[k_idx])
                                            if success:
                                                streak += 1
                                                hit_history_c.append(valid_cs_in_draw)
                                            else:
                                                break
                                        elif is_tail_drag:
                                            R_k, draw_set_k, act_k = history_diffs[k_idx]
                                            c_k_list =[c_tuple[0] - act_k * step_val] + list(c_tuple[1:]) if is_step_advance else c_tuple
                                            p_nums = self.get_pred_nums(R_k, c_k_list, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                            valid_cs_in_draw =[p for p in p_nums if p in draw_set_k]
                                            success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                            if success:
                                                streak += 1
                                                hit_history_c.append(list(c_tuple) if is_non_hit else[p // 10 for p in valid_cs_in_draw])
                                            else:
                                                break
                                        elif is_tail_match:
                                            R_k, draw_tails_k, act_k = history_diffs[k_idx]
                                            p_nums =[]
                                            for c in c_tuple:
                                                actual_c = c - act_k * step_val
                                                if is_sum: p = actual_c - R_k
                                                else: p = R_k + actual_c
                                                p_nums.append(p)
    
                                            valid_cs_in_draw =[]
                                            for c in c_tuple:
                                                actual_c = c - act_k * step_val
                                                if is_sum: p = actual_c - R_k
                                                else: p = R_k + actual_c
                                                if p % 10 in draw_tails_k:
                                                    valid_cs_in_draw.append(c)
    
                                            combo_tails = {x % 10 for x in p_nums}
                                            success = (len(combo_tails & draw_tails_k) == 0) if is_non_hit else (len(combo_tails & draw_tails_k) >= min_hit_req)
                                            if success:
                                                streak += 1
                                                hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                            else:
                                                break
                                        else:
                                            valid_cs_set, act_k = history_diffs[k_idx]
                                            valid_cs_in_draw =[c for c in c_tuple if c in valid_cs_set]
                                            success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                            if success:
                                                streak += 1
                                                hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                            else:
                                                break
    
                                    if streak >= effective_min_streak:
                                        if is_alternate or is_alternate_vip:
                                            if streak < 4:
                                                continue
    
                                            if is_tail_drag:
                                                c1_val, c2_val = c_tuple[1], c_tuple[2]
                                            else:
                                                c1_val, c2_val = c_tuple[0], c_tuple[1]
    
                                            if is_alternate_vip:
                                                valid_streak = 0
                                                for length in range(streak, 3, -1):
                                                    if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                        valid_streak = length
                                                        break
                                                if valid_streak < max(4, effective_min_streak):
                                                    continue
                                                streak = valid_streak
                                            elif is_alternate:
                                                if not check_alt_any(hit_history_c, c1_val, c2_val):
                                                    continue
    
                                        if is_staircase:
                                            curr_P = cycle[(P_or_offset + 0) % len(cycle)]
                                        else:
                                            curr_P = P_or_offset
    
                                        l = processed_data[latest_ref_idx]['list']
                                        curr_R = l[curr_P]
                                        pred_nums = self.get_pred_nums(curr_R, c_tuple, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
    
                                        if not verify_miss(pred_nums): continue
    
    
                                        trigger_dates =[processed_data[latest_ref_idx - k * interval]['date'] for k in range(streak + 1)]
    
                                        latest_pred_nums_to_save = pred_nums
                                        if is_tail_match and not is_tail_drag:
                                            latest_pred_nums_to_save = expand_tails(latest_pred_nums_to_save, max_val)
    
                                        results_list.append({
                                            'mode': 7,
                                            'pred_range': pred_range,
                                            'streak': streak, 'X': curr_R, 'P_X': curr_P, 'N': 0, 'P': curr_P, 'M': M,
                                            'interval': interval,
                                            'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                            'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                            'latest_occ': latest_ref_idx, 'latest_pred_nums': latest_pred_nums_to_save,
                                            'trigger_dates': trigger_dates,
                                            'is_staircase': is_staircase,
                                            'stair_offset': P_or_offset if is_staircase else 0,
                                            'is_step_advance': is_step_advance,
                                            'step_val': step_val,
                                            'is_tail_match': is_tail_match,
                                            'is_tail_drag': is_tail_drag,
                                            'is_non_hit': is_non_hit
                                        })
            elif analysis_mode == 12:
                step_vals_to_test =[-1, 1] if is_step_advance else[0]
                t_start = max(0, total_periods - 300)
                max_px = balls_cnt + (1 if params['has_special'] else 0)
                interval_list = params.get('interval_list',[params.get('interval_step', 1)])
                is_double_trigger = params.get('is_double_trigger', True)
    
                pos_pairs =[]
                if is_double_trigger:
                    for p1 in range(max_px):
                        for p2 in range(p1+1, max_px):
                            pos_pairs.append((p1, p2, p1, p2))
                else:
                    for p1 in range(max_px):
                        pos_pairs.append((p1, -1, p1, -1))
    
                for pl1, pl2, pr1, pr2 in pos_pairs:
                    if progress_callback: progress_callback(0.5)
                    for c_tuple in valid_c_lists:
                        for interval in interval_list:
                            for M in range(1, 16):
                                if pred_range == 3 and M < 2: continue
                                if pred_range == 4 and M < 3: continue
    
                                for s_val in step_vals_to_test:
                                    streak = 0
                                    hit_history_c =[]
                                    trigger_dates =[]
    
                                    latest_trigger_idx = total_periods - M
                                    if pred_range == 3: latest_trigger_idx = total_periods - 1 - M
                                    elif pred_range == 4: latest_trigger_idx = total_periods - 2 - M
    
                                    if latest_trigger_idx < 0: continue
    
                                    for k in range(total_periods):
                                        curr_t = latest_trigger_idx - k * interval
                                        if curr_t < 0: break
    
                                        prev_t = curr_t - CHART_ROWS
                                        if prev_t < 0: break
    
                                        l_right = processed_data[curr_t]['list']
                                        l_left = processed_data[prev_t]['list']
    
                                        if is_double_trigger:
                                            if max(pr1, pr2) >= len(l_right): break
                                            if max(pl1, pl2) >= len(l_left): break
                                            diff_l = abs(l_left[pl1] - l_left[pl2])
                                            diff_r = abs(l_right[pr1] - l_right[pr2])
                                            base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                        else:
                                            if pr1 >= len(l_right): break
                                            if pl1 >= len(l_left): break
                                            val_l1 = l_left[pl1]
                                            val_r1 = l_right[pr1]
                                            base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)
    
                                        if k == 0:
                                            trigger_dates.append(processed_data[curr_t]['date'])
                                            continue
    
                                        t_set = helper_get_target_set(curr_t, M)
                                        if t_set is None: break
    
                                        valid_cs_in_draw =[]
                                        if is_tail_drag:
                                            c_tail = c_tuple[0]
                                            act_c_tail = c_tail + k * s_val if is_step_advance else c_tail
                                            tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                            heads = c_tuple[1:]
                                            for h in heads:
                                                p_num = h * 10 + tail
                                                if p_num in t_set:
                                                    valid_cs_in_draw.append(h)
                                        else:
                                            for c in c_tuple:
                                                act_c = c + k * s_val if is_step_advance else c
                                                p_num = mode12_pred_value(base_val, act_c, is_sum, is_cyclic, max_val)
    
                                                if is_tail_match:
                                                    if any(p_num % 10 == tn % 10 for tn in t_set):
                                                        valid_cs_in_draw.append(c)
                                                else:
                                                    if p_num in t_set:
                                                        valid_cs_in_draw.append(c)
    
                                        success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                        if success:
                                            streak += 1
                                            trigger_dates.append(processed_data[curr_t]['date'])
                                            hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                        else:
                                            break
    
                                    if streak >= effective_min_streak:
                                        if is_alternate or is_alternate_vip:
                                            if streak < 4: continue
                                            c1_val, c2_val = c_tuple[0], c_tuple[1]
                                            if is_alternate_vip:
                                                valid_streak = 0
                                                for length in range(streak, 3, -1):
                                                    if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                        valid_streak = length
                                                        break
                                                if valid_streak < max(4, effective_min_streak): continue
                                                streak = valid_streak
                                            elif is_alternate:
                                                if not check_alt_any(hit_history_c, c1_val, c2_val): continue
    
                                        l_right = processed_data[latest_trigger_idx]['list']
                                        l_left = processed_data[latest_trigger_idx - CHART_ROWS]['list']
    
                                        if is_double_trigger:
                                            diff_l = abs(l_left[pl1] - l_left[pl2])
                                            diff_r = abs(l_right[pr1] - l_right[pr2])
                                            base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                        else:
                                            val_l1 = l_left[pl1]
                                            val_r1 = l_right[pr1]
                                            base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)
    
                                        pred_nums =[]
                                        if is_tail_drag:
                                            c_tail = c_tuple[0]
                                            act_c_tail = c_tail
                                            tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                            heads = c_tuple[1:]
                                            for h in heads:
                                                p = h * 10 + tail
                                                if 1 <= p <= max_val:
                                                    pred_nums.append(p)
                                        else:
                                            for c in c_tuple:
                                                p = mode12_pred_value(base_val, c, is_sum, is_cyclic, max_val)
                                                pred_nums.append(p)
    
                                            if is_tail_match and not is_tail_drag:
                                                pred_nums = expand_tails(pred_nums, max_val)
    
                                        if not verify_miss(pred_nums): continue
    
    
                                        results_list.append({
                                            'mode': 12,
                                            'pred_range': pred_range,
                                            'streak': streak,
                                            'pl1': pl1, 'pl2': pl2, 'pr1': pr1, 'pr2': pr2,
                                            'X': base_val, 'M': M, 'N': 0, 'P': 0, 'P_X': -1,
                                            'interval': interval,
                                            'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                            'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                            'latest_occ': latest_trigger_idx, 'latest_pred_nums': sorted(list(set(pred_nums))),
                                            'trigger_dates': trigger_dates[::-1],
                                            'is_tail_match': is_tail_match, 'is_tail_drag': is_tail_drag,
                                            'is_step_advance': is_step_advance, 'step_val': -s_val if is_step_advance else 0,
                                            'is_double_trigger': is_double_trigger,
                                            'same_period_pair_mode': params.get('same_period_pair_mode', None),
                                            'is_non_hit': is_non_hit
                                        })
            elif analysis_mode == 11:
                # N次週牌(深層分析版):不再只        elif analysis_mode == 11:
                # N次週牌:
                # 一般模式:照單一候選號碼回推固定間隔。
                # 順子牌型:只看 01↔11↔21↔31 這條 10 進位序列,並且只限 1 隻。
                pick_count_n11 = max(1, int(params.get('pick_count', 1) or 1))
                seq10_mode_n11 = bool(params.get('is_consec', False))
    
                if seq10_mode_n11:
                    pick_count_n11 = 1
                    is_step_interval_n11 = bool(params.get('is_step_interval', False))
    
                    # 順子牌型(修改2):同尾數、頭數固定每次 +10 / -10。
                    # 開頭一定要是 0頭或 3頭開始,1頭、2頭開頭不使用:
                    #   0頭(升冪):頭0→頭1→頭2(錨點/最近一次),預測頭3。
                    #             例如 05→15→25,預測 35。
                    #   3頭(降冪):頭3→頭2→頭1(錨點/最近一次),預測頭0。
                    #             例如 36→26→16,預測 06。
                    # check_chain 內部驗證順序固定「錨點(最近一次)在前、越舊在
                    # 後」,沿用原本 anchor_idx/interval 往回推的邏輯;預測號碼
                    # 用 pred 另外記錄,不再取陣列最後一格。display_chain 則是
                    # 「舊到新、含預測」的完整順序,對應使用者由左到右閱讀
                    # 「05再來15再來25預測35」的說法,顯示與候選格畫圖都直接沿用。
                    seq_chains_n11 = []
                    for tail_n11 in range(0, 10):
                        head0_num = tail_n11
                        head1_num = tail_n11 + 10
                        head2_num = tail_n11 + 20
                        head3_num = tail_n11 + 30
                        if head0_num < 1 or head3_num > max_val:
                            # 頭0(head0_num)是尾數本身,539沒有00,故頭0不存在的
                            # 尾數(只有尾0)整組跳過;頭3超出遊戲最大號碼也跳過。
                            continue
    
                        seq_chains_n11.append({
                            'check_chain': [head2_num, head1_num, head0_num],
                            'pred': head3_num,
                            'display_chain': (head0_num, head1_num, head2_num, head3_num),
                            'dir': 'asc',
                        })
                        seq_chains_n11.append({
                            'check_chain': [head1_num, head2_num, head3_num],
                            'pred': head0_num,
                            'display_chain': (head3_num, head2_num, head1_num, head0_num),
                            'dir': 'desc',
                        })
    
                    draw_checks_n11 = []
                    for item in processed_data:
                        s = item['set']
                        draw_checks_n11.append({x % 10 for x in s} if is_tail_match else s)
    
                    target_future_idx = total_periods
                    target_future_date = next_draw_data[0][0] if next_draw_data else None
    
                    total_work_n11 = max(1, len(seq_chains_n11) * max(1, total_periods))
                    done_work_n11 = 0
                    if progress_callback:
                        progress_callback(0.03)
    
                    for seq_item_n11 in seq_chains_n11:
                        chain_nums_n11 = seq_item_n11['check_chain']
                        pred_num_n11 = seq_item_n11['pred']
                        display_chain_n11 = seq_item_n11['display_chain']
                        seq_dir_n11 = seq_item_n11['dir']
                        if not chain_nums_n11:
                            continue
    
                        for anchor_idx in range(total_periods - 1, -1, -1):
                            done_work_n11 += 1
                            if progress_callback and (done_work_n11 % 200 == 0 or done_work_n11 == total_work_n11):
                                progress_callback(min(0.98, 0.03 + (done_work_n11 / float(total_work_n11)) * 0.94))
    
                            if chain_nums_n11[0] not in draw_checks_n11[anchor_idx]:
                                continue
    
                            interval = target_future_idx - anchor_idx
                            if interval <= 0:
                                continue
    
                            streak = 1
                            matched_indices_n11 = [anchor_idx]
    
                            if is_step_interval_n11:
                                # 步步間隔+順子牌型:錨點→未來的間隔(interval)是
                                # 這條序列最新的一步,越往回推間隔越小(每步少1,
                                # 例如 3.4.5⋯),跟一般候選模式的步步間隔邏輯一致。
                                cur_idx_n11 = anchor_idx
                                gap_n11 = interval - 1
                                for step_idx in range(1, len(chain_nums_n11)):
                                    if gap_n11 < 1:
                                        break
                                    check_idx = cur_idx_n11 - gap_n11
                                    if check_idx < 0:
                                        break
                                    if chain_nums_n11[step_idx] in draw_checks_n11[check_idx]:
                                        streak += 1
                                        matched_indices_n11.append(check_idx)
                                        cur_idx_n11 = check_idx
                                        gap_n11 -= 1
                                    else:
                                        break
                            else:
                                for step_idx in range(1, len(chain_nums_n11)):
                                    check_idx = anchor_idx - step_idx * interval
                                    if check_idx < 0:
                                        break
                                    if chain_nums_n11[step_idx] in draw_checks_n11[check_idx]:
                                        streak += 1
                                        matched_indices_n11.append(check_idx)
                                    else:
                                        break
    
                            if streak < effective_min_streak:
                                continue
    
                            # 順子牌型(0頭/3頭固定版):不論這次驗證中了幾格
                            # (streak深淺),預測目標都固定是這個方向本來就定義
                            # 好的下一個頭數(0頭→頭3,3頭→頭0),不會因為streak
                            # 而改變。
                            pred_nums_n11 = [pred_num_n11]
    
                            if not verify_miss(pred_nums_n11):
                                continue
    
                            trigger_dates_n11 = [processed_data[i]['date'] for i in matched_indices_n11]
    
                            results_list.append({
                                'mode': 11,
                                'pred_range': pred_range,
                                'streak': streak,
                                'C_list': display_chain_n11,
                                'interval': interval,
                                'N': 0, 'P': 0, 'M': interval,
                                'is_step_interval': is_step_interval_n11,
                                'max_val': max_val,
                                'min_hit_req': min_hit_req,
                                'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                                'latest_occ': anchor_idx,
                                'latest_pred_nums': pred_nums_n11,
                                'trigger_dates': trigger_dates_n11,
                                'predict_date': target_future_date,
                                'predict_index': target_future_idx,
                                'is_tail_match': is_tail_match,
                                'is_non_hit': is_non_hit,
                                'is_seq10': True,
                                'seq_direction': seq_dir_n11,
                                'seq_chain': display_chain_n11,
                                'pillar_counts': [pick_count_n11, 0, 0, 0, 0]
                            })
                else:
                    # N次週牌(深層分析版):不再只依照「最近一次命中→下一期」反推出單一間隔,
                    # 而是把每一個歷史命中位置都當成一次候選錨點,各自反推對應的間隔期數,
                    # 逐一往回驗證連莊次數。同一組候選號碼若同時存在多種週期
                    # (例如每3期一次、每17期一次...),每一種都會被個別挖出來、各自成一條版路,
                    # 而不是只挖到「最近一次命中」推出的那一條。10期、30期甚至更長的間隔一樣直接跑。
                    pick_count_n11 = max(1, int(params.get('pick_count', 1) or 1))
                    is_step_interval_n11 = bool(params.get('is_step_interval', False))
                    is_alternate_vip_n11 = bool(params.get('is_alternate_vip', False))
                    is_alternate_n11 = bool(params.get('is_alternate', False)) and not is_alternate_vip_n11
                    if is_alternate_n11 or is_alternate_vip_n11:
                        pick_count_n11 = 2
    
                    if is_tail_match:
                        c_pool_n11 = list(range(0, 10))
                    else:
                        c_pool_n11 = list(range(1, max_val + 1))
                    pick_count_n11 = min(pick_count_n11, len(c_pool_n11))
    
                    draw_checks_n11 = []
                    for item in processed_data:
                        s = item['set']
                        draw_checks_n11.append({x % 10 for x in s} if is_tail_match else s)
    
                    combo_iter_n11 = combinations(c_pool_n11, pick_count_n11)
                    candidate_list_n11 = list(islice(combo_iter_n11, 20000))
    
                    # processed_data 長度就是「下一期」的 index;若 history 到 7/26,下一期 7/27 就是 total_periods。
                    target_future_idx = total_periods
                    target_future_date = next_draw_data[0][0] if next_draw_data else None
    
                    total_work_n11 = max(1, len(candidate_list_n11))
                    done_work_n11 = 0
                    if progress_callback:
                        progress_callback(0.03)
    
                    for c_tuple in candidate_list_n11:
                        done_work_n11 += 1
                        if progress_callback and (done_work_n11 % 200 == 0 or done_work_n11 == total_work_n11):
                            progress_callback(min(0.98, 0.03 + (done_work_n11 / float(total_work_n11)) * 0.94))
    
                        hit_indices_n11 = []
                        for idx in range(total_periods - 1, -1, -1):
                            dc = draw_checks_n11[idx]
                            hits = sum(1 for c in c_tuple if c in dc)
                            success = (hits >= min_hit_req) if not is_non_hit else (hits < min_hit_req)
                            if success:
                                hit_indices_n11.append(idx)
    
                        if not hit_indices_n11:
                            continue
    
                        # 預測號碼與「提前中」檢查只跟候選本身有關,跟用哪個錨點/間隔無關,
                        # 所以拉到錨點迴圈外面算一次就好,不用每個錨點都重算一次。
                        if is_tail_match:
                            pred_nums_n11 = [n for n in range(1, max_val + 1) if n % 10 in c_tuple]
                        else:
                            pred_nums_n11 = list(c_tuple)
    
                        if not verify_miss(pred_nums_n11):
                            continue
    
                        hit_set_n11 = set(hit_indices_n11)
    
                        # 深層分析核心:每一個歷史命中位置都當成一次獨立錨點,
                        # 反推「錨點 -> 下一期」的間隔,再各自往回驗證連莊次數。
                        # 同一組候選號碼常常同時符合好幾種週期(例如每3期一次、
                        # 每17期一次...),這裡會把每一種都個別挖出來、各自成一條版路,
                        # 而不是只認「最近一次命中」推出的那一個間隔。
                        for anchor_idx in hit_indices_n11:
                            interval = target_future_idx - anchor_idx
                            if interval <= 0:
                                continue
    
                            if is_step_interval_n11:
                                # 步步間隔:不是固定同一個間隔反覆跑,而是每往回推一步,
                                # 間隔就自動少1(等於未來方向每往前一步,間隔自動+1,
                                # 例如 2.3.4.5⋯)。anchor→未來的間隔(interval)就是這條
                                # 序列最新的一步;往回推時間隔遞減,減到0就不能再驗證。
                                streak = 1
                                matched_idx_n11 = [anchor_idx]
                                cur_idx = anchor_idx
                                gap = interval - 1
                                while gap >= 1:
                                    expect_idx = cur_idx - gap
                                    if expect_idx not in hit_set_n11:
                                        break
                                    streak += 1
                                    matched_idx_n11.append(expect_idx)
                                    cur_idx = expect_idx
                                    gap -= 1
    
                                if streak < effective_min_streak:
                                    continue
    
                                trigger_dates_n11 = [processed_data[i]['date'] for i in matched_idx_n11]
                            else:
                                streak = 1
                                matched_idx_n11 = [anchor_idx]
                                expect_idx = anchor_idx - interval
                                while expect_idx in hit_set_n11:
                                    streak += 1
                                    matched_idx_n11.append(expect_idx)
                                    expect_idx -= interval
    
                                if streak < effective_min_streak:
                                    continue
    
                                trigger_dates_n11 = [processed_data[i]['date'] for i in matched_idx_n11]
    
                            if is_alternate_n11 or is_alternate_vip_n11:
                                # 輪流模式/嚴格輪流:限雙號候選,檢查兩顆號碼是否
                                # 一次一次輪流出現(A,B,A,B...),而不是隨便誰中都算。
                                if len(c_tuple) != 2 or streak < 4:
                                    continue
                                c1_val_n11, c2_val_n11 = c_tuple[0], c_tuple[1]
                                hit_history_n11 = [[c for c in c_tuple if c in draw_checks_n11[i]] for i in matched_idx_n11]
                                if is_alternate_vip_n11:
                                    valid_streak_n11 = 0
                                    for length_n11 in range(streak, 3, -1):
                                        if check_alt_vip(hit_history_n11[:length_n11], c1_val_n11, c2_val_n11):
                                            valid_streak_n11 = length_n11
                                            break
                                    if valid_streak_n11 < max(4, effective_min_streak):
                                        continue
                                    streak = valid_streak_n11
                                    matched_idx_n11 = matched_idx_n11[:valid_streak_n11]
                                    trigger_dates_n11 = trigger_dates_n11[:valid_streak_n11]
                                else:
                                    if not check_alt_any(hit_history_n11, c1_val_n11, c2_val_n11):
                                        continue
    
                            results_list.append({
                                'mode': 11,
                                'pred_range': pred_range,
                                'streak': streak,
                                'C_list': c_tuple,
                                'interval': interval,
                                'N': 0, 'P': 0, 'M': interval,
                                'is_step_interval': is_step_interval_n11,
                                'is_alternate': is_alternate_n11,
                                'is_alternate_vip': is_alternate_vip_n11,
                                'max_val': max_val,
                                'min_hit_req': min_hit_req,
                                'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                                'latest_occ': anchor_idx,
                                'latest_pred_nums': pred_nums_n11,
                                'trigger_dates': trigger_dates_n11,
                                'predict_date': target_future_date,
                                'predict_index': target_future_idx,
                                'is_tail_match': is_tail_match,
                                'is_non_hit': is_non_hit,
                                'pillar_counts': [pick_count_n11, 0, 0, 0, 0]
                            })
    
                step_vals_to_test =[-1, 1] if is_step_advance else[0]
                t_start = max(0, total_periods - 300)
                max_px = balls_cnt + (1 if params['has_special'] else 0)
                interval_list = params.get('interval_list',[params.get('interval_step', 1)])
                is_double_trigger = params.get('is_double_trigger', True)
    
                pos_pairs =[]
                if is_double_trigger:
                    for p1 in range(max_px):
                        for p2 in range(p1+1, max_px):
                            pos_pairs.append((p1, p2, p1, p2))
                else:
                    for p1 in range(max_px):
                        pos_pairs.append((p1, -1, p1, -1))
    
                for pl1, pl2, pr1, pr2 in pos_pairs:
                    if progress_callback: progress_callback(0.5)
                    for c_tuple in valid_c_lists:
                        for interval in interval_list:
                            for M in range(1, 16):
                                if pred_range == 3 and M < 2: continue
                                if pred_range == 4 and M < 3: continue
    
                                for s_val in step_vals_to_test:
                                    streak = 0
                                    hit_history_c =[]
                                    trigger_dates =[]
    
                                    latest_trigger_idx = total_periods - M
                                    if pred_range == 3: latest_trigger_idx = total_periods - 1 - M
                                    elif pred_range == 4: latest_trigger_idx = total_periods - 2 - M
    
                                    if latest_trigger_idx < 0: continue
    
                                    for k in range(total_periods):
                                        curr_t = latest_trigger_idx - k * interval
                                        if curr_t < 0: break
    
                                        prev_t = curr_t - CHART_ROWS
                                        if prev_t < 0: break
    
                                        l_right = processed_data[curr_t]['list']
                                        l_left = processed_data[prev_t]['list']
    
                                        if is_double_trigger:
                                            if max(pr1, pr2) >= len(l_right): break
                                            if max(pl1, pl2) >= len(l_left): break
                                            diff_l = abs(l_left[pl1] - l_left[pl2])
                                            diff_r = abs(l_right[pr1] - l_right[pr2])
                                            base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                        else:
                                            if pr1 >= len(l_right): break
                                            if pl1 >= len(l_left): break
                                            val_l1 = l_left[pl1]
                                            val_r1 = l_right[pr1]
                                            base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)
    
                                        if k == 0:
                                            trigger_dates.append(processed_data[curr_t]['date'])
                                            continue
    
                                        t_set = helper_get_target_set(curr_t, M)
                                        if t_set is None: break
    
                                        valid_cs_in_draw =[]
                                        if is_tail_drag:
                                            c_tail = c_tuple[0]
                                            act_c_tail = c_tail + k * s_val if is_step_advance else c_tail
                                            tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                            heads = c_tuple[1:]
                                            for h in heads:
                                                p_num = h * 10 + tail
                                                if p_num in t_set:
                                                    valid_cs_in_draw.append(h)
                                        else:
                                            for c in c_tuple:
                                                act_c = c + k * s_val if is_step_advance else c
                                                p_num = mode12_pred_value(base_val, act_c, is_sum, is_cyclic, max_val)
    
                                                if is_tail_match:
                                                    if any(p_num % 10 == tn % 10 for tn in t_set):
                                                        valid_cs_in_draw.append(c)
                                                else:
                                                    if p_num in t_set:
                                                        valid_cs_in_draw.append(c)
    
                                        success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                        if success:
                                            streak += 1
                                            trigger_dates.append(processed_data[curr_t]['date'])
                                            hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                        else:
                                            break
    
                                    if streak >= effective_min_streak:
                                        if is_alternate or is_alternate_vip:
                                            if streak < 4: continue
                                            c1_val, c2_val = c_tuple[0], c_tuple[1]
                                            if is_alternate_vip:
                                                valid_streak = 0
                                                for length in range(streak, 3, -1):
                                                    if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                        valid_streak = length
                                                        break
                                                if valid_streak < max(4, effective_min_streak): continue
                                                streak = valid_streak
                                            elif is_alternate:
                                                if not check_alt_any(hit_history_c, c1_val, c2_val): continue
    
                                        l_right = processed_data[latest_trigger_idx]['list']
                                        l_left = processed_data[latest_trigger_idx - CHART_ROWS]['list']
    
                                        if is_double_trigger:
                                            diff_l = abs(l_left[pl1] - l_left[pl2])
                                            diff_r = abs(l_right[pr1] - l_right[pr2])
                                            base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                        else:
                                            val_l1 = l_left[pl1]
                                            val_r1 = l_right[pr1]
                                            base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)
    
                                        pred_nums =[]
                                        if is_tail_drag:
                                            c_tail = c_tuple[0]
                                            act_c_tail = c_tail
                                            tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                            heads = c_tuple[1:]
                                            for h in heads:
                                                p = h * 10 + tail
                                                if 1 <= p <= max_val:
                                                    pred_nums.append(p)
                                        else:
                                            for c in c_tuple:
                                                p = mode12_pred_value(base_val, c, is_sum, is_cyclic, max_val)
                                                pred_nums.append(p)
    
                                            if is_tail_match and not is_tail_drag:
                                                pred_nums = expand_tails(pred_nums, max_val)
    
                                        if not verify_miss(pred_nums): continue
    
    
                                        results_list.append({
                                            'mode': 12,
                                            'pred_range': pred_range,
                                            'streak': streak,
                                            'pl1': pl1, 'pl2': pl2, 'pr1': pr1, 'pr2': pr2,
                                            'X': base_val, 'M': M, 'N': 0, 'P': 0, 'P_X': -1,
                                            'interval': interval,
                                            'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                            'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                            'latest_occ': latest_trigger_idx, 'latest_pred_nums': sorted(list(set(pred_nums))),
                                            'trigger_dates': trigger_dates[::-1],
                                            'is_tail_match': is_tail_match, 'is_tail_drag': is_tail_drag,
                                            'is_step_advance': is_step_advance, 'step_val': -s_val if is_step_advance else 0,
                                            'is_double_trigger': is_double_trigger,
                                            'same_period_pair_mode': params.get('same_period_pair_mode', None),
                                            'is_non_hit': is_non_hit
                                        })
        elif analysis_mode == 14:


            interval_list = params.get('interval_list', [params.get('interval_step', 1)])
            is_alternate = params.get('is_alternate', False)
            is_alternate_vip = params.get('is_alternate_vip', False)
            is_step_advance = params.get('is_step_advance', False)
            max_M = 150
            P1 = 1
            P2 = 4
            step_values = [1, -1, 10, -10] if is_step_advance else [0]

            if balls_cnt <= max(P1, P2):
                return [], next_draw_data

            for interval in interval_list:
                for M in range(1, max_M):
                    if progress_callback and M % 10 == 0:
                        progress_callback(M / float(max_M))

                    if pred_range == 3:
                        latest_target_idx = total_periods - 1
                        if M < 2:
                            continue
                    elif pred_range == 4:
                        latest_target_idx = total_periods - 2
                        if M < 3:
                            continue
                    else:
                        latest_target_idx = total_periods

                    latest_ref2_idx = latest_target_idx - M
                    latest_ref1_idx = latest_ref2_idx - 1
                    if latest_ref1_idx < 0 or latest_ref2_idx < 0 or latest_ref2_idx >= total_periods:
                        continue
                    if latest_target_idx - (effective_min_streak - 1) * interval < 0:
                        break

                    for step_val in step_values:
                        history_diffs = []
                        broken = False

                        for k in range(total_periods):
                            t_idx = latest_target_idx - k * interval
                            r2_idx = t_idx - M
                            r1_idx = r2_idx - 1
                            if r1_idx < 0 or r2_idx < 0:
                                break
                            if r2_idx >= total_periods:
                                broken = True
                                break

                            l1 = processed_data[r1_idx]['list']
                            l2 = processed_data[r2_idx]['list']
                            if P1 >= len(l1) or P2 >= len(l2):
                                broken = True
                                break
                            R = abs(l2[P2] - l1[P1])

                            if k == 0:
                                history_diffs.append('PENDING')
                            else:
                                if t_idx < 0 or t_idx >= total_periods:
                                    broken = True
                                    break
                                t_set = helper_get_target_set(t_idx, 0)
                                if t_set is None:
                                    broken = True
                                    break

                                if special_tiandi_mode:
                                    win = _special_tiandi_window(t_idx, 0)
                                    if win is None:
                                        broken = True
                                        break
                                    history_diffs.append(_special_tiandi_c_window_with_step(R, win, k * step_val))
                                elif is_tail_drag:
                                    history_diffs.append((R, t_set, k))
                                elif is_tail_match:
                                    history_diffs.append((R, {x % 10 for x in t_set}, k))
                                else:
                                    valid_c_set = set()
                                    for t_num in t_set:
                                        if is_sum:
                                            c = R + t_num
                                            if is_cyclic:
                                                c = (c - 1) % max_val + 1
                                            c = c + k * step_val
                                            valid_c_set.add(c)
                                        else:
                                            c = t_num - R
                                            if is_cyclic:
                                                c = c % max_val
                                                if c <= 0:
                                                    c += max_val
                                            c = c + k * step_val
                                            valid_c_set.add(c)
                                    history_diffs.append((valid_c_set, k))

                        if broken or len(history_diffs) < effective_min_streak:
                            continue

                        if len(history_diffs) > 1:
                            if special_tiandi_mode:
                                first_cwin = history_diffs[1]
                                candidate_c_lists = []
                                for tup in valid_c_lists:
                                    ok, _ = _special_tiandi_success_for_c_tuple(tup, first_cwin)
                                    if ok:
                                        candidate_c_lists.append(tup)
                            elif is_tail_drag:
                                R_1, draw_set_1, k_1 = history_diffs[1]
                                candidate_c_lists = []
                                for tup in valid_c_lists:
                                    c_k_list = [tup[0] - k_1 * step_val] + list(tup[1:]) if is_step_advance else tup
                                    p_nums = self.get_pred_nums(R_1, c_k_list, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                    hits_val = sum(1 for p in p_nums if p in draw_set_1)
                                    if is_non_hit:
                                        if hits_val == 0:
                                            candidate_c_lists.append(tup)
                                    else:
                                        if hits_val >= min_hit_req:
                                            candidate_c_lists.append(tup)
                            elif is_tail_match:
                                R_1, draw_tails_1, k_1 = history_diffs[1]
                                candidate_c_lists = []
                                for tup in valid_c_lists:
                                    p_nums = []
                                    for c in tup:
                                        actual_c = c - k_1 * step_val
                                        p = actual_c - R_1 if is_sum else R_1 + actual_c
                                        p_nums.append(p)
                                    combo_tails = {x % 10 for x in p_nums}
                                    hits_val = len(combo_tails & draw_tails_1)
                                    if is_non_hit:
                                        if hits_val == 0:
                                            candidate_c_lists.append(tup)
                                    else:
                                        if hits_val >= min_hit_req:
                                            candidate_c_lists.append(tup)
                            else:
                                first_h_cs, k_1 = history_diffs[1]
                                candidate_c_lists = []
                                for tup in valid_c_lists:
                                    hits_val = sum(1 for c in tup if c in first_h_cs)
                                    if is_non_hit:
                                        if hits_val == 0:
                                            candidate_c_lists.append(tup)
                                    else:
                                        if hits_val >= min_hit_req:
                                            candidate_c_lists.append(tup)
                        else:
                            candidate_c_lists = valid_c_lists

                        candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                        for c_tuple in candidate_c_lists:


                            weekly_single_core = (not is_tail_drag and len(c_tuple) < 2)
                            if (is_alternate or is_alternate_vip) and not weekly_single_core:
                                if is_tail_drag and len(c_tuple) != 3:
                                    continue
                                elif not is_tail_drag and len(c_tuple) != 2:
                                    continue

                            streak = 0
                            hit_history_c = []
                            for k_idx in range(1, len(history_diffs)):
                                if special_tiandi_mode:
                                    success, valid_cs_in_draw = _special_tiandi_success_for_c_tuple(c_tuple, history_diffs[k_idx])
                                    if success:
                                        streak += 1
                                        hit_history_c.append(valid_cs_in_draw)
                                    else:
                                        break
                                elif is_tail_drag:
                                    R_k, draw_set_k, act_k = history_diffs[k_idx]
                                    c_k_list = [c_tuple[0] - act_k * step_val] + list(c_tuple[1:]) if is_step_advance else c_tuple
                                    p_nums = self.get_pred_nums(R_k, c_k_list, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                    valid_cs_in_draw = [p for p in p_nums if p in draw_set_k]
                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                    if success:
                                        streak += 1
                                        hit_history_c.append(list(c_tuple) if is_non_hit else [p // 10 for p in valid_cs_in_draw])
                                    else:
                                        break
                                elif is_tail_match:
                                    R_k, draw_tails_k, act_k = history_diffs[k_idx]
                                    p_nums = []
                                    valid_cs_in_draw = []
                                    for c in c_tuple:
                                        actual_c = c - act_k * step_val
                                        p = actual_c - R_k if is_sum else R_k + actual_c
                                        p_nums.append(p)
                                        if p % 10 in draw_tails_k:
                                            valid_cs_in_draw.append(c)
                                    combo_tails = {x % 10 for x in p_nums}
                                    success = (len(combo_tails & draw_tails_k) == 0) if is_non_hit else (len(combo_tails & draw_tails_k) >= min_hit_req)
                                    if success:
                                        streak += 1
                                        hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                    else:
                                        break
                                else:
                                    valid_cs_set, act_k = history_diffs[k_idx]
                                    valid_cs_in_draw = [c for c in c_tuple if c in valid_cs_set]
                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                    if success:
                                        streak += 1
                                        hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                    else:
                                        break

                            if streak >= effective_min_streak:
                                if (is_alternate or is_alternate_vip) and not weekly_single_core:
                                    if streak < 4:
                                        continue
                                    if is_tail_drag:
                                        c1_val, c2_val = c_tuple[1], c_tuple[2]
                                    else:
                                        c1_val, c2_val = c_tuple[0], c_tuple[1]
                                    if is_alternate_vip:
                                        valid_streak = 0
                                        for length in range(streak, 3, -1):
                                            if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                valid_streak = length
                                                break
                                        if valid_streak < max(4, effective_min_streak):
                                            continue
                                        streak = valid_streak
                                    elif is_alternate:
                                        if not check_alt_any(hit_history_c, c1_val, c2_val):
                                            continue

                                l1_latest = processed_data[latest_ref1_idx]['list']
                                l2_latest = processed_data[latest_ref2_idx]['list']
                                curr_R = abs(l2_latest[P2] - l1_latest[P1])
                                pred_nums = self.get_pred_nums(curr_R, c_tuple, max_val, is_sum, is_cyclic, is_tail_match, is_tail_drag)
                                if is_tail_match and not is_tail_drag:
                                    pred_nums = expand_tails(pred_nums, max_val)
                                else:

                                    expected_pred_count = pick_count
                                    if len(set(pred_nums)) < expected_pred_count:
                                        continue
                                if not verify_miss(pred_nums):
                                    continue

                                trigger_dates = []
                                for k in range(streak + 1):
                                    ref2 = latest_ref2_idx - k * interval
                                    if 0 <= ref2 < total_periods:
                                        trigger_dates.append(processed_data[ref2]['date'])

                                results_list.append({
                                    'mode': 14,
                                    'pred_range': pred_range,
                                    'streak': streak,
                                    'X': curr_R, 'P_X': -1, 'N': 0, 'P': P2, 'M': M,
                                    'P1': P1, 'P2': P2,
                                    'interval': interval,
                                    'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                    'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                    'latest_occ': latest_ref2_idx, 'latest_pred_nums': sorted(list(set(pred_nums))),
                                    'trigger_dates': trigger_dates,
                                    'is_step_advance': is_step_advance,
                                    'step_val': step_val,
                                    'is_tail_match': is_tail_match,
                                    'is_tail_drag': is_tail_drag,
                                    'is_non_hit': is_non_hit,
                                    'weekly_double_core': tuple(c_tuple) == (0,)
                                })

        elif analysis_mode == 11:
            # N次週牌(深層分析版):不再只        elif analysis_mode == 11:
            # N次週牌:
            # 一般模式:照單一候選號碼回推固定間隔。
            # 順子牌型:只看 01↔11↔21↔31 這條 10 進位序列,並且只限 1 隻。
            pick_count_n11 = max(1, int(params.get('pick_count', 1) or 1))
            seq10_mode_n11 = bool(params.get('is_consec', False))

            if seq10_mode_n11:
                pick_count_n11 = 1
                is_step_interval_n11 = bool(params.get('is_step_interval', False))

                # 順子牌型(修改2):同尾數、頭數固定每次 +10 / -10。
                # 開頭一定要是 0頭或 3頭開始,1頭、2頭開頭不使用:
                #   0頭(升冪):頭0→頭1→頭2(錨點/最近一次),預測頭3。
                #             例如 05→15→25,預測 35。
                #   3頭(降冪):頭3→頭2→頭1(錨點/最近一次),預測頭0。
                #             例如 36→26→16,預測 06。
                # check_chain 內部驗證順序固定「錨點(最近一次)在前、越舊在
                # 後」,沿用原本 anchor_idx/interval 往回推的邏輯;預測號碼
                # 用 pred 另外記錄,不再取陣列最後一格。display_chain 則是
                # 「舊到新、含預測」的完整順序,對應使用者由左到右閱讀
                # 「05再來15再來25預測35」的說法,顯示與候選格畫圖都直接沿用。
                seq_chains_n11 = []
                for tail_n11 in range(0, 10):
                    head0_num = tail_n11
                    head1_num = tail_n11 + 10
                    head2_num = tail_n11 + 20
                    head3_num = tail_n11 + 30
                    if head0_num < 1 or head3_num > max_val:
                        # 頭0(head0_num)是尾數本身,539沒有00,故頭0不存在的
                        # 尾數(只有尾0)整組跳過;頭3超出遊戲最大號碼也跳過。
                        continue

                    seq_chains_n11.append({
                        'check_chain': [head2_num, head1_num, head0_num],
                        'pred': head3_num,
                        'display_chain': (head0_num, head1_num, head2_num, head3_num),
                        'dir': 'asc',
                    })
                    seq_chains_n11.append({
                        'check_chain': [head1_num, head2_num, head3_num],
                        'pred': head0_num,
                        'display_chain': (head3_num, head2_num, head1_num, head0_num),
                        'dir': 'desc',
                    })

                draw_checks_n11 = []
                for item in processed_data:
                    s = item['set']
                    draw_checks_n11.append({x % 10 for x in s} if is_tail_match else s)

                target_future_idx = total_periods
                target_future_date = next_draw_data[0][0] if next_draw_data else None

                total_work_n11 = max(1, len(seq_chains_n11) * max(1, total_periods))
                done_work_n11 = 0
                if progress_callback:
                    progress_callback(0.03)

                for seq_item_n11 in seq_chains_n11:
                    chain_nums_n11 = seq_item_n11['check_chain']
                    pred_num_n11 = seq_item_n11['pred']
                    display_chain_n11 = seq_item_n11['display_chain']
                    seq_dir_n11 = seq_item_n11['dir']
                    if not chain_nums_n11:
                        continue

                    for anchor_idx in range(total_periods - 1, -1, -1):
                        done_work_n11 += 1
                        if progress_callback and (done_work_n11 % 200 == 0 or done_work_n11 == total_work_n11):
                            progress_callback(min(0.98, 0.03 + (done_work_n11 / float(total_work_n11)) * 0.94))

                        if chain_nums_n11[0] not in draw_checks_n11[anchor_idx]:
                            continue

                        interval = target_future_idx - anchor_idx
                        if interval <= 0:
                            continue

                        streak = 1
                        matched_indices_n11 = [anchor_idx]

                        if is_step_interval_n11:
                            # 步步間隔+順子牌型:錨點→未來的間隔(interval)是
                            # 這條序列最新的一步,越往回推間隔越小(每步少1,
                            # 例如 3.4.5⋯),跟一般候選模式的步步間隔邏輯一致。
                            cur_idx_n11 = anchor_idx
                            gap_n11 = interval - 1
                            for step_idx in range(1, len(chain_nums_n11)):
                                if gap_n11 < 1:
                                    break
                                check_idx = cur_idx_n11 - gap_n11
                                if check_idx < 0:
                                    break
                                if chain_nums_n11[step_idx] in draw_checks_n11[check_idx]:
                                    streak += 1
                                    matched_indices_n11.append(check_idx)
                                    cur_idx_n11 = check_idx
                                    gap_n11 -= 1
                                else:
                                    break
                        else:
                            for step_idx in range(1, len(chain_nums_n11)):
                                check_idx = anchor_idx - step_idx * interval
                                if check_idx < 0:
                                    break
                                if chain_nums_n11[step_idx] in draw_checks_n11[check_idx]:
                                    streak += 1
                                    matched_indices_n11.append(check_idx)
                                else:
                                    break

                        if streak < effective_min_streak:
                            continue

                        # 順子牌型(0頭/3頭固定版):不論這次驗證中了幾格
                        # (streak深淺),預測目標都固定是這個方向本來就定義
                        # 好的下一個頭數(0頭→頭3,3頭→頭0),不會因為streak
                        # 而改變。
                        pred_nums_n11 = [pred_num_n11]

                        if not verify_miss(pred_nums_n11):
                            continue

                        trigger_dates_n11 = [processed_data[i]['date'] for i in matched_indices_n11]

                        results_list.append({
                            'mode': 11,
                            'pred_range': pred_range,
                            'streak': streak,
                            'C_list': display_chain_n11,
                            'interval': interval,
                            'N': 0, 'P': 0, 'M': interval,
                            'is_step_interval': is_step_interval_n11,
                            'max_val': max_val,
                            'min_hit_req': min_hit_req,
                            'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                            'latest_occ': anchor_idx,
                            'latest_pred_nums': pred_nums_n11,
                            'trigger_dates': trigger_dates_n11,
                            'predict_date': target_future_date,
                            'predict_index': target_future_idx,
                            'is_tail_match': is_tail_match,
                            'is_non_hit': is_non_hit,
                            'is_seq10': True,
                            'seq_direction': seq_dir_n11,
                            'seq_chain': display_chain_n11,
                            'pillar_counts': [pick_count_n11, 0, 0, 0, 0]
                        })
            else:
                # N次週牌(深層分析版):不再只依照「最近一次命中→下一期」反推出單一間隔,
                # 而是把每一個歷史命中位置都當成一次候選錨點,各自反推對應的間隔期數,
                # 逐一往回驗證連莊次數。同一組候選號碼若同時存在多種週期
                # (例如每3期一次、每17期一次...),每一種都會被個別挖出來、各自成一條版路,
                # 而不是只挖到「最近一次命中」推出的那一條。10期、30期甚至更長的間隔一樣直接跑。
                pick_count_n11 = max(1, int(params.get('pick_count', 1) or 1))
                is_step_interval_n11 = bool(params.get('is_step_interval', False))
                is_alternate_vip_n11 = bool(params.get('is_alternate_vip', False))
                is_alternate_n11 = bool(params.get('is_alternate', False)) and not is_alternate_vip_n11
                if is_alternate_n11 or is_alternate_vip_n11:
                    pick_count_n11 = 2

                if is_tail_match:
                    c_pool_n11 = list(range(0, 10))
                else:
                    c_pool_n11 = list(range(1, max_val + 1))
                pick_count_n11 = min(pick_count_n11, len(c_pool_n11))

                draw_checks_n11 = []
                for item in processed_data:
                    s = item['set']
                    draw_checks_n11.append({x % 10 for x in s} if is_tail_match else s)

                combo_iter_n11 = combinations(c_pool_n11, pick_count_n11)
                candidate_list_n11 = list(islice(combo_iter_n11, 20000))

                # processed_data 長度就是「下一期」的 index;若 history 到 7/26,下一期 7/27 就是 total_periods。
                target_future_idx = total_periods
                target_future_date = next_draw_data[0][0] if next_draw_data else None

                total_work_n11 = max(1, len(candidate_list_n11))
                done_work_n11 = 0
                if progress_callback:
                    progress_callback(0.03)

                for c_tuple in candidate_list_n11:
                    done_work_n11 += 1
                    if progress_callback and (done_work_n11 % 200 == 0 or done_work_n11 == total_work_n11):
                        progress_callback(min(0.98, 0.03 + (done_work_n11 / float(total_work_n11)) * 0.94))

                    hit_indices_n11 = []
                    for idx in range(total_periods - 1, -1, -1):
                        dc = draw_checks_n11[idx]
                        hits = sum(1 for c in c_tuple if c in dc)
                        success = (hits >= min_hit_req) if not is_non_hit else (hits < min_hit_req)
                        if success:
                            hit_indices_n11.append(idx)

                    if not hit_indices_n11:
                        continue

                    # 預測號碼與「提前中」檢查只跟候選本身有關,跟用哪個錨點/間隔無關,
                    # 所以拉到錨點迴圈外面算一次就好,不用每個錨點都重算一次。
                    if is_tail_match:
                        pred_nums_n11 = [n for n in range(1, max_val + 1) if n % 10 in c_tuple]
                    else:
                        pred_nums_n11 = list(c_tuple)

                    if not verify_miss(pred_nums_n11):
                        continue

                    hit_set_n11 = set(hit_indices_n11)

                    # 深層分析核心:每一個歷史命中位置都當成一次獨立錨點,
                    # 反推「錨點 -> 下一期」的間隔,再各自往回驗證連莊次數。
                    # 同一組候選號碼常常同時符合好幾種週期(例如每3期一次、
                    # 每17期一次...),這裡會把每一種都個別挖出來、各自成一條版路,
                    # 而不是只認「最近一次命中」推出的那一個間隔。
                    for anchor_idx in hit_indices_n11:
                        interval = target_future_idx - anchor_idx
                        if interval <= 0:
                            continue

                        if is_step_interval_n11:
                            # 步步間隔:不是固定同一個間隔反覆跑,而是每往回推一步,
                            # 間隔就自動少1(等於未來方向每往前一步,間隔自動+1,
                            # 例如 2.3.4.5⋯)。anchor→未來的間隔(interval)就是這條
                            # 序列最新的一步;往回推時間隔遞減,減到0就不能再驗證。
                            streak = 1
                            matched_idx_n11 = [anchor_idx]
                            cur_idx = anchor_idx
                            gap = interval - 1
                            while gap >= 1:
                                expect_idx = cur_idx - gap
                                if expect_idx not in hit_set_n11:
                                    break
                                streak += 1
                                matched_idx_n11.append(expect_idx)
                                cur_idx = expect_idx
                                gap -= 1

                            if streak < effective_min_streak:
                                continue

                            trigger_dates_n11 = [processed_data[i]['date'] for i in matched_idx_n11]
                        else:
                            streak = 1
                            matched_idx_n11 = [anchor_idx]
                            expect_idx = anchor_idx - interval
                            while expect_idx in hit_set_n11:
                                streak += 1
                                matched_idx_n11.append(expect_idx)
                                expect_idx -= interval

                            if streak < effective_min_streak:
                                continue

                            trigger_dates_n11 = [processed_data[i]['date'] for i in matched_idx_n11]

                        if is_alternate_n11 or is_alternate_vip_n11:
                            # 輪流模式/嚴格輪流:限雙號候選,檢查兩顆號碼是否
                            # 一次一次輪流出現(A,B,A,B...),而不是隨便誰中都算。
                            if len(c_tuple) != 2 or streak < 4:
                                continue
                            c1_val_n11, c2_val_n11 = c_tuple[0], c_tuple[1]
                            hit_history_n11 = [[c for c in c_tuple if c in draw_checks_n11[i]] for i in matched_idx_n11]
                            if is_alternate_vip_n11:
                                valid_streak_n11 = 0
                                for length_n11 in range(streak, 3, -1):
                                    if check_alt_vip(hit_history_n11[:length_n11], c1_val_n11, c2_val_n11):
                                        valid_streak_n11 = length_n11
                                        break
                                if valid_streak_n11 < max(4, effective_min_streak):
                                    continue
                                streak = valid_streak_n11
                                matched_idx_n11 = matched_idx_n11[:valid_streak_n11]
                                trigger_dates_n11 = trigger_dates_n11[:valid_streak_n11]
                            else:
                                if not check_alt_any(hit_history_n11, c1_val_n11, c2_val_n11):
                                    continue

                        results_list.append({
                            'mode': 11,
                            'pred_range': pred_range,
                            'streak': streak,
                            'C_list': c_tuple,
                            'interval': interval,
                            'N': 0, 'P': 0, 'M': interval,
                            'is_step_interval': is_step_interval_n11,
                            'is_alternate': is_alternate_n11,
                            'is_alternate_vip': is_alternate_vip_n11,
                            'max_val': max_val,
                            'min_hit_req': min_hit_req,
                            'sum_mode': False, 'cyclic': False, 'ref_dir': 0,
                            'latest_occ': anchor_idx,
                            'latest_pred_nums': pred_nums_n11,
                            'trigger_dates': trigger_dates_n11,
                            'predict_date': target_future_date,
                            'predict_index': target_future_idx,
                            'is_tail_match': is_tail_match,
                            'is_non_hit': is_non_hit,
                            'pillar_counts': [pick_count_n11, 0, 0, 0, 0]
                        })

            step_vals_to_test =[-1, 1] if is_step_advance else[0]
            t_start = max(0, total_periods - 300)
            max_px = balls_cnt + (1 if params['has_special'] else 0)
            interval_list = params.get('interval_list',[params.get('interval_step', 1)])
            is_double_trigger = params.get('is_double_trigger', True)

            pos_pairs =[]
            if is_double_trigger:
                for p1 in range(max_px):
                    for p2 in range(p1+1, max_px):
                        pos_pairs.append((p1, p2, p1, p2))
            else:
                for p1 in range(max_px):
                    pos_pairs.append((p1, -1, p1, -1))

            for pl1, pl2, pr1, pr2 in pos_pairs:
                if progress_callback: progress_callback(0.5)
                for c_tuple in valid_c_lists:
                    for interval in interval_list:
                        for M in range(1, 16):
                            if pred_range == 3 and M < 2: continue
                            if pred_range == 4 and M < 3: continue

                            for s_val in step_vals_to_test:
                                streak = 0
                                hit_history_c =[]
                                trigger_dates =[]

                                latest_trigger_idx = total_periods - M
                                if pred_range == 3: latest_trigger_idx = total_periods - 1 - M
                                elif pred_range == 4: latest_trigger_idx = total_periods - 2 - M

                                if latest_trigger_idx < 0: continue

                                for k in range(total_periods):
                                    curr_t = latest_trigger_idx - k * interval
                                    if curr_t < 0: break

                                    prev_t = curr_t - CHART_ROWS
                                    if prev_t < 0: break

                                    l_right = processed_data[curr_t]['list']
                                    l_left = processed_data[prev_t]['list']

                                    if is_double_trigger:
                                        if max(pr1, pr2) >= len(l_right): break
                                        if max(pl1, pl2) >= len(l_left): break
                                        diff_l = abs(l_left[pl1] - l_left[pl2])
                                        diff_r = abs(l_right[pr1] - l_right[pr2])
                                        base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                    else:
                                        if pr1 >= len(l_right): break
                                        if pl1 >= len(l_left): break
                                        val_l1 = l_left[pl1]
                                        val_r1 = l_right[pr1]
                                        base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)

                                    if k == 0:
                                        trigger_dates.append(processed_data[curr_t]['date'])
                                        continue

                                    t_set = helper_get_target_set(curr_t, M)
                                    if t_set is None: break

                                    valid_cs_in_draw =[]
                                    if is_tail_drag:
                                        c_tail = c_tuple[0]
                                        act_c_tail = c_tail + k * s_val if is_step_advance else c_tail
                                        tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                        heads = c_tuple[1:]
                                        for h in heads:
                                            p_num = h * 10 + tail
                                            if p_num in t_set:
                                                valid_cs_in_draw.append(h)
                                    else:
                                        for c in c_tuple:
                                            act_c = c + k * s_val if is_step_advance else c
                                            p_num = mode12_pred_value(base_val, act_c, is_sum, is_cyclic, max_val)

                                            if is_tail_match:
                                                if any(p_num % 10 == tn % 10 for tn in t_set):
                                                    valid_cs_in_draw.append(c)
                                            else:
                                                if p_num in t_set:
                                                    valid_cs_in_draw.append(c)

                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                    if success:
                                        streak += 1
                                        trigger_dates.append(processed_data[curr_t]['date'])
                                        hit_history_c.append(list(c_tuple) if is_non_hit else valid_cs_in_draw)
                                    else:
                                        break

                                if streak >= effective_min_streak:
                                    if is_alternate or is_alternate_vip:
                                        if streak < 4: continue
                                        c1_val, c2_val = c_tuple[0], c_tuple[1]
                                        if is_alternate_vip:
                                            valid_streak = 0
                                            for length in range(streak, 3, -1):
                                                if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                    valid_streak = length
                                                    break
                                            if valid_streak < max(4, effective_min_streak): continue
                                            streak = valid_streak
                                        elif is_alternate:
                                            if not check_alt_any(hit_history_c, c1_val, c2_val): continue

                                    l_right = processed_data[latest_trigger_idx]['list']
                                    l_left = processed_data[latest_trigger_idx - CHART_ROWS]['list']

                                    if is_double_trigger:
                                        diff_l = abs(l_left[pl1] - l_left[pl2])
                                        diff_r = abs(l_right[pr1] - l_right[pr2])
                                        base_val = diff_l + diff_r if is_sum else abs(diff_r - diff_l)
                                    else:
                                        val_l1 = l_left[pl1]
                                        val_r1 = l_right[pr1]
                                        base_val = val_l1 + val_r1 if is_sum else abs(val_r1 - val_l1)

                                    pred_nums =[]
                                    if is_tail_drag:
                                        c_tail = c_tuple[0]
                                        act_c_tail = c_tail
                                        tail = mode12_tail_value(base_val, act_c_tail, is_sum)
                                        heads = c_tuple[1:]
                                        for h in heads:
                                            p = h * 10 + tail
                                            if 1 <= p <= max_val:
                                                pred_nums.append(p)
                                    else:
                                        for c in c_tuple:
                                            p = mode12_pred_value(base_val, c, is_sum, is_cyclic, max_val)
                                            pred_nums.append(p)

                                        if is_tail_match and not is_tail_drag:
                                            pred_nums = expand_tails(pred_nums, max_val)

                                    if not verify_miss(pred_nums): continue


                                    results_list.append({
                                        'mode': 12,
                                        'pred_range': pred_range,
                                        'streak': streak,
                                        'pl1': pl1, 'pl2': pl2, 'pr1': pr1, 'pr2': pr2,
                                        'X': base_val, 'M': M, 'N': 0, 'P': 0, 'P_X': -1,
                                        'interval': interval,
                                        'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                        'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                        'latest_occ': latest_trigger_idx, 'latest_pred_nums': sorted(list(set(pred_nums))),
                                        'trigger_dates': trigger_dates[::-1],
                                        'is_tail_match': is_tail_match, 'is_tail_drag': is_tail_drag,
                                        'is_step_advance': is_step_advance, 'step_val': -s_val if is_step_advance else 0,
                                        'is_double_trigger': is_double_trigger,
                                        'same_period_pair_mode': params.get('same_period_pair_mode', None),
                                        'is_non_hit': is_non_hit
                                    })
        elif analysis_mode == 13:
            interval_list = params.get('interval_list', [params.get('interval_step', 1)])
            shape_index = params.get('shape_index', 0)
            seen_mode13_keys = set()

            if shape_index not in (0, 1, 2, 3, 4, 6):
                return[], next_draw_data

            for X_val in range(1, max_val + 1):
                if progress_callback: progress_callback(X_val / max_val)

                max_px = balls_cnt + (1 if params['has_special'] else 0)

                if shape_index in (1, 4):
                    px_list = [2]
                elif shape_index in (2, 3, 6):
                    px_list = [0]
                else:
                    px_list = range(max_px) if is_fixed_pos else [-1]

                for P_X_val in px_list:
                    if shape_index == 4:
                        occurrences = get_occurrences_by_pos(2, X_val)
                    elif shape_index == 1:
                        occurrences = get_occurrences_by_pos(2, X_val)
                    elif shape_index in (2, 3, 6):
                        occurrences = get_occurrences_by_pos(0, X_val)
                    elif P_X_val == -1:
                        occurrences = get_occurrences_by_set(X_val)
                    else:
                        occurrences = get_occurrences_by_pos(P_X_val, X_val)

                    if len(occurrences) < effective_min_streak: continue

                    for latest_occ_idx in range(len(occurrences)-1, -1, -1):
                        if latest_occ_idx + 1 < effective_min_streak: break

                        latest_occ = occurrences[latest_occ_idx]
                        if pred_range == 3: M = total_periods - 1 - latest_occ
                        elif pred_range == 4: M = total_periods - 2 - latest_occ
                        else: M = total_periods - latest_occ

                        if M < 1 or M > 15: continue
                        if pred_range == 3 and M < 2: continue
                        if pred_range == 4 and M < 3: continue

                        history_diffs =[]
                        broken_by_pending = False

                        for i in range(latest_occ_idx, -1, -1):
                            t_idx = occurrences[i]

                            idx_center = t_idx
                            idx_top = idx_center - 1
                            idx_bottom = idx_center + 1

                            if idx_top < 0 or idx_bottom >= total_periods:
                                break

                            l_top = processed_data[idx_top]['list']
                            l_center = processed_data[idx_center]['list']
                            l_bottom = processed_data[idx_bottom]['list']

                            if shape_index == 1:
                                idx_up3 = t_idx - 3
                                idx_up2 = t_idx - 2
                                idx_down2 = t_idx + 2
                                idx_down3 = t_idx + 3
                                if idx_up3 < 0 or idx_up2 < 0 or idx_down2 >= total_periods or idx_down3 >= total_periods:
                                    break

                                up3_list = processed_data[idx_up3]['list']
                                up2_list = processed_data[idx_up2]['list']
                                down2_list = processed_data[idx_down2]['list']
                                down3_list = processed_data[idx_down3]['list']
                                if len(up3_list) <= 2 or len(up2_list) <= 4 or len(down2_list) <= 4 or len(down3_list) <= 2:
                                    break

                                a_val = up3_list[2] % 10
                                b1_val = up2_list[0] % 10
                                b2_val = up2_list[4] % 10
                                c1_val = down2_list[0] % 10
                                c2_val = down2_list[4] % 10
                                d_val = down3_list[2] % 10
                                line_sum = a_val + b1_val + b2_val + c1_val + c2_val + d_val
                            elif shape_index == 2:
                                idx_next = t_idx + 1
                                idx_down2 = t_idx + 2
                                idx_down3 = t_idx + 3
                                if idx_next >= total_periods or idx_down2 >= total_periods or idx_down3 >= total_periods:
                                    break

                                cur_list = processed_data[t_idx]['list']
                                next_list = processed_data[idx_next]['list']
                                down2_list = processed_data[idx_down2]['list']
                                down3_list = processed_data[idx_down3]['list']
                                if len(cur_list) <= 2 or len(next_list) <= 2 or len(down2_list) <= 1 or len(down3_list) <= 1:
                                    break

                                a_val = abs(cur_list[0] - next_list[0])
                                b_val = abs(cur_list[2] - next_list[2])
                                c_val = abs(down2_list[1] - down3_list[1])
                                line_sum = a_val + b_val + c_val
                            elif shape_index == 3:
                                idx_next = t_idx + 1
                                idx_up1 = t_idx - 1
                                idx_up2 = t_idx - 2
                                if idx_next >= total_periods or idx_up1 < 0 or idx_up2 < 0:
                                    break

                                cur_list = processed_data[t_idx]['list']
                                next_list = processed_data[idx_next]['list']
                                up1_list = processed_data[idx_up1]['list']
                                up2_list = processed_data[idx_up2]['list']
                                if len(cur_list) <= 2 or len(next_list) <= 2 or len(up1_list) <= 1 or len(up2_list) <= 1:
                                    break

                                a_val = abs(cur_list[0] - next_list[0])
                                b_val = abs(cur_list[2] - next_list[2])
                                c_val = abs(up1_list[1] - up2_list[1])
                                line_sum = a_val + b_val + c_val
                            elif shape_index == 4:
                                idx_up3 = t_idx - 3
                                idx_up1 = t_idx - 1
                                idx_down2 = t_idx + 2
                                if idx_up3 < 0 or idx_up1 < 0 or idx_down2 >= total_periods:
                                    break

                                up3_list = processed_data[idx_up3]['list']
                                up1_list = processed_data[idx_up1]['list']
                                down2_list = processed_data[idx_down2]['list']
                                if len(up3_list) <= 2 or len(up1_list) <= 4 or len(down2_list) <= 4:
                                    break

                                a_val = up3_list[2] % 10
                                b_val = (up1_list[0] % 10 + up1_list[4] % 10) % 10
                                c_val = down2_list[0] % 10 + down2_list[4] % 10
                                line_sum = a_val + b_val + c_val
                            elif shape_index == 6:
                                idx_up5 = t_idx - 5
                                idx_down3 = t_idx + 3
                                idx_down6 = t_idx + 6
                                if idx_up5 < 0 or idx_down3 >= total_periods or idx_down6 >= total_periods:
                                    break

                                cur_list = processed_data[t_idx]['list']
                                up5_list = processed_data[idx_up5]['list']
                                down3_list = processed_data[idx_down3]['list']
                                down6_list = processed_data[idx_down6]['list']
                                if len(cur_list) <= 0 or len(up5_list) <= 4 or len(down3_list) <= 4 or len(down6_list) <= 0:
                                    break

                                a_val = up5_list[4] % 10
                                b_val = down3_list[4] % 10
                                c_val = down6_list[0] % 10
                                line_sum = a_val + b_val + c_val
                            else:
                                if P_X_val == -1:
                                    p_x_act = l_center.index(X_val) if X_val in l_center else -1
                                else:
                                    p_x_act = P_X_val

                                if p_x_act <= 0 or p_x_act >= len(l_center) - 1:
                                    break

                                if p_x_act >= len(l_top) or p_x_act >= len(l_bottom):
                                    break

                                v_top = l_top[p_x_act]
                                v_left = l_center[p_x_act - 1]
                                v_right = l_center[p_x_act + 1]
                                v_bottom = l_bottom[p_x_act]

                                line_sum = (v_top % 10) + (v_left % 10) + (v_right % 10) + (v_bottom % 10)

                            if i == latest_occ_idx:
                                history_diffs.append(("PENDING", line_sum))
                            else:
                                t_set = helper_get_target_set(t_idx, M)
                                if t_set is None:
                                    broken_by_pending = True
                                    break

                                if is_tail_drag:
                                    history_diffs.append((line_sum, t_set))
                                else:
                                    valid_c_set = set()
                                    for t_num in t_set:
                                        if is_sum:
                                            c = line_sum + t_num
                                            if is_cyclic:
                                                c = (c - 1) % max_val + 1
                                            valid_c_set.add(c)
                                        else:
                                            c = t_num - line_sum
                                            if is_cyclic:
                                                c = c % max_val
                                                if c <= 0:
                                                    c += max_val
                                            valid_c_set.add(c)
                                    history_diffs.append(valid_c_set)

                        if broken_by_pending or len(history_diffs) < effective_min_streak:
                            continue

                        if len(history_diffs) > 1:
                            candidate_c_lists =[]
                            if is_tail_drag:
                                D_sum_1, draw_set_1 = history_diffs[1]
                                for tup in valid_c_lists:
                                    tail = mode12_tail_value(D_sum_1, tup[0], is_sum)
                                    p_nums =[h * 10 + tail for h in tup[1:] if 1 <= h * 10 + tail <= max_val]
                                    hits_val = sum(1 for p in p_nums if p in draw_set_1)
                                    if is_non_hit:
                                        if hits_val == 0:
                                            candidate_c_lists.append(tup)
                                    else:
                                        if hits_val >= min_hit_req:
                                            candidate_c_lists.append(tup)
                            else:
                                first_h_cs = history_diffs[1]
                                for tup in valid_c_lists:
                                    hits_val = sum(1 for c in tup if c in first_h_cs)
                                    if is_non_hit:
                                        if hits_val == 0:
                                            candidate_c_lists.append(tup)
                                    else:
                                        if hits_val >= min_hit_req:
                                            candidate_c_lists.append(tup)
                        else:
                            candidate_c_lists = valid_c_lists

                        candidate_c_lists = _guard_candidate_c_lists(candidate_c_lists)
                        for c_tuple in candidate_c_lists:
                            if is_alternate or is_alternate_vip:
                                if is_tail_drag and len(c_tuple) != 3:
                                    continue
                                elif not is_tail_drag and len(c_tuple) != 2:
                                    continue

                            streak = 0
                            hit_history_c =[]

                            for k_idx in range(1, len(history_diffs)):
                                if is_tail_drag:
                                    D_sum_k, draw_set_k = history_diffs[k_idx]
                                    tail = mode12_tail_value(D_sum_k, c_tuple[0], is_sum)
                                    p_nums =[h * 10 + tail for h in c_tuple[1:] if 1 <= h * 10 + tail <= max_val]
                                    valid_cs_in_draw =[p for p in p_nums if p in draw_set_k]
                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                    run_piece = list(c_tuple) if is_non_hit else[p // 10 for p in valid_cs_in_draw]
                                else:
                                    valid_cs_set = history_diffs[k_idx]
                                    valid_cs_in_draw =[c for c in c_tuple if c in valid_cs_set]
                                    success = (len(valid_cs_in_draw) == 0) if is_non_hit else (len(valid_cs_in_draw) >= min_hit_req)
                                    run_piece = list(c_tuple) if is_non_hit else valid_cs_in_draw

                                if success:
                                    streak += 1
                                    hit_history_c.append(run_piece)
                                else:
                                    break

                            if streak >= effective_min_streak:
                                if is_alternate or is_alternate_vip:
                                    if streak < 4:
                                        continue
                                    if is_tail_drag:
                                        c1_val, c2_val = c_tuple[1], c_tuple[2]
                                    else:
                                        c1_val, c2_val = c_tuple[0], c_tuple[1]
                                    if is_alternate_vip:
                                        valid_streak = 0
                                        for length in range(streak, 3, -1):
                                            if check_alt_vip(hit_history_c[:length], c1_val, c2_val):
                                                valid_streak = length
                                                break
                                        if valid_streak < max(4, effective_min_streak):
                                            continue
                                        streak = valid_streak
                                    elif is_alternate:
                                        if not check_alt_any(hit_history_c, c1_val, c2_val):
                                            continue

                                latest_D_sum = history_diffs[0][1]
                                pred_nums =[]
                                if is_tail_drag:
                                    tail = mode12_tail_value(latest_D_sum, c_tuple[0], is_sum)
                                    pred_nums =[h * 10 + tail for h in c_tuple[1:] if 1 <= h * 10 + tail <= max_val]
                                else:
                                    pred_nums =[mode12_pred_value(latest_D_sum, c, is_sum, is_cyclic, max_val) for c in c_tuple]

                                if not verify_miss(pred_nums):
                                    continue


                                trigger_dates =[processed_data[occurrences[latest_occ_idx - k]]['date'] for k in range(streak + 1)]

                                result_key = (
                                    13,
                                    shape_index,
                                    pred_range,
                                    X_val,
                                    P_X_val,
                                    streak,
                                    M,
                                    latest_D_sum,
                                    tuple(c_tuple),
                                    tuple(sorted(set(pred_nums))),
                                    is_sum,
                                    is_cyclic,
                                    is_tail_drag,
                                    is_non_hit,
                                )
                                if result_key in seen_mode13_keys:
                                    continue
                                seen_mode13_keys.add(result_key)

                                results_list.append({
                                    'mode': 13,
                                    'pred_range': pred_range,
                                    'streak': streak,
                                    'X': X_val, 'P_X': P_X_val, 'N': 0, 'P': 0, 'M': M,
                                    'D_sum': latest_D_sum,
                                    'C_list': c_tuple, 'max_val': max_val, 'min_hit_req': min_hit_req,
                                    'sum_mode': is_sum, 'cyclic': is_cyclic, 'ref_dir': 0,
                                    'latest_occ': latest_occ,
                                    'latest_pred_nums': sorted(list(set(pred_nums))),
                                    'trigger_dates': trigger_dates[::-1],
                                    'shape_index': shape_index,
                                    'is_tail': False,
                                    'is_tail_match': False,
                                    'is_tail_drag': is_tail_drag,
                                    'is_non_hit': is_non_hit
                                })
        if lock_special:
            for _res in results_list:
                _res['lock_special'] = True
                if special_tiandi_mode:
                    _res['special_tiandi_mode'] = True

        _prune_results_for_biglotto_guard(force=True)
        t_search_end = time.perf_counter()
        results_list.sort(
            key=lambda x: (
                x['streak'],
                1 if x.get('weekly_double_core') else 0,
                x.get('three_star_count', 0)
            ),
            reverse=True
        )
        if min_streak_input == 0:
            results_list = [r for r in results_list if int(r.get('streak', 0) or 0) > 1]

        # 熱門立柱 2期/3期已改成跟熱門拖牌同邏輯,不再用最新開獎列硬性過濾。
        t_sort_end = time.perf_counter()

        profile = {
            'cache_hit': False,
            'preprocess_sec': t_preprocess_end - t_total_start,
            'occurrence_sec': t_occurrence_end - t_preprocess_end,
            'search_sec': t_search_end - t_occurrence_end,
            'sort_sec': t_sort_end - t_search_end,
            'total_sec': t_sort_end - t_total_start,
            'result_count': min(len(results_list), 1000),
            'combo_guard': combo_guard_was_used,
            'combo_guard_limit': combo_candidate_limit if combo_guard_was_used else None,
        }
        self._analysis_last_profile = profile

        result_top = [dict(r) for r in results_list[:1000]]
        result_next = list(next_draw_data)

        cache_store = getattr(self, '_analysis_result_cache', None)
        if cache_store is not None:
            if len(cache_store) > 24:
                cache_store.clear()
            cache_store[cache_key] = {
                'top': result_top,
                'next': result_next,
                'profile': profile,
            }

        return result_top, result_next




# ---------------------------------------------------------------------------
# 智能彩引：歷史回測評分 / 冠軍嚴選 / 下期驗證
# ---------------------------------------------------------------------------
def _smart_next_draws(eng, eval_date):
    rows = [r for r in eng.data if r[0] > eval_date]
    return rows


def _smart_evaluate_hit(eng, r, next_draws):
    """網頁版等價於原始 App evaluate_hit() 的純運算版本。"""
    if not next_draws:
        return False, [], [], True

    pred_range = r.get('pred_range', 0)
    mode = r.get('mode', 0)
    draws = list(next_draws)
    if mode == 15:
        wd = r.get('weekday')
        if isinstance(wd, int) and 0 <= wd <= 6:
            draws = [row for row in draws if row[0].weekday() == wd]

    try:
        date_route_eval_count = int(r.get('date_route_eval_count', 0) or 0)
    except Exception:
        date_route_eval_count = 0
    if mode == 16 and date_route_eval_count > 0:
        check_count = date_route_eval_count
    else:
        check_count = 1 if pred_range in (3, 4) else get_pred_range_count(pred_range)

    valid_draws = list(draws[:check_count])
    is_pending = len(valid_draws) < check_count
    if not valid_draws:
        return False, [], [], True

    has_special = bool(eng.has_special.get(eng.lotto_type, False))
    lock_special = bool(r.get('lock_special', False) and has_special)
    special_tiandi_mode = bool(
        r.get('special_tiandi_mode', False)
        or (lock_special and int(r.get('min_hit_req', 1) or 1) >= 2
            and not r.get('is_tail_match', False)
            and not r.get('is_tail_drag', False)
            and not r.get('is_non_hit', False))
    )

    def draw_nums(row):
        if lock_special and not special_tiandi_mode:
            return {row[2]} if row[2] is not None else set()
        out = set(row[1])
        if has_special and row[2] is not None:
            out.add(row[2])
        return out

    req = int(r.get('min_hit_req', 1) or 1)
    is_non_hit = bool(r.get('is_non_hit', False))
    is_tail = bool(r.get('is_tail_match', False))

    if special_tiandi_mode:
        pred_set = set(r.get('latest_pred_nums', []) or [])
        for nd in valid_draws:
            sp = nd[2] if has_special else None
            inner = sorted(set(nd[1]) & pred_set)
            special_hit = sp is not None and sp in pred_set
            need_inner = max(1, req - 1)
            hits = ([sp] if special_hit else []) + inner
            if special_hit and len(inner) >= need_inner:
                return True, sorted(set(hits)), valid_draws, is_pending
        return False, [], valid_draws, is_pending

    # 立柱熱門 / 每月週牌 / 日期版路：星數是命中的柱數
    if mode in (9, 10, 16):
        pillars = r.get('pillars', []) or []
        pillar_sets = []
        pillar_tail_sets = []
        for pillar in pillars:
            if not pillar:
                continue
            if is_tail:
                pillar_tail_sets.append({int(n) % 10 for n in pillar})
            else:
                pillar_sets.append(set(int(n) for n in pillar))
        all_nums = set().union(*pillar_sets) if pillar_sets else set()
        all_tails = set().union(*pillar_tail_sets) if pillar_tail_sets else set()
        broken = False
        for nd in valid_draws:
            nums = draw_nums(nd)
            if is_tail:
                draw_tails = {n % 10 for n in nums}
                hit_nums = sorted(n for n in nums if n % 10 in all_tails)
                stars = sum(1 for pset in pillar_tail_sets if pset and (draw_tails & pset))
            else:
                hit_nums = sorted(n for n in nums if n in all_nums)
                stars = sum(1 for pset in pillar_sets if pset and (nums & pset))
            if is_non_hit:
                if stars > 0:
                    broken = True
                    break
            elif stars >= req:
                return True, sorted(set(hit_nums)), valid_draws, False
        return (not broken) if is_non_hit else False, [], valid_draws, is_pending

    pred_nums = tuple(int(x) for x in (r.get('latest_pred_nums', []) or []))
    pred_set = set(pred_nums)
    pred_tails = {x % 10 for x in pred_nums}
    broken = False
    for nd in valid_draws:
        nums = draw_nums(nd)
        if is_tail:
            hits = sorted(n for n in nums if n % 10 in pred_tails)
            hit_count = len({n % 10 for n in nums} & pred_tails)
        else:
            hits = sorted(n for n in nums if n in pred_set)
            hit_count = len(nums & pred_set)
        if is_non_hit:
            if hit_count > 0:
                broken = True
                break
        elif hit_count >= req:
            return True, sorted(set(hits)), valid_draws, False
    return (not broken) if is_non_hit else False, [], valid_draws, is_pending


def _smart_reason(st):
    if st['current_miss'] >= st['max_miss'] and st['max_miss'] > 0:
        return '⚠️ 已達歷史連漏極限，看好強烈反彈!'
    if st['current_miss'] == 0:
        return '🔥 版路正熱，順勢乘勝追擊!'
    if st['current_miss'] >= st['avg_interval']:
        return '📈 已超過平均週期，隨時準備爆發!'
    return f"⭐ 綜合評分優異，整體勝率達 {st['hit_rate_pct']:.1f}%!"


def run_smart_recommendation(eng, current_top, params, limit_date, lookback=20, target_count=5):
    """依原 App 冠軍分析邏輯做純 Python 網頁版回測，避免 UI/iOS 依賴。"""
    current_top = list(current_top or [])
    if not current_top:
        return {'ok': True, 'lookback': 0, 'recommendations': [], 'champions': [], 'nextDraws': []}

    try:
        lookback = max(5, min(50, int(lookback or 20)))
    except Exception:
        lookback = 20
    try:
        target_count = max(1, min(5, int(target_count or 5)))
    except Exception:
        target_count = 5

    eval_dates = []
    for row in reversed(eng.data):
        if row[0] <= limit_date:
            eval_dates.append(row[0])
            if len(eval_dates) >= lookback:
                break
    # 最新基準日不拿自己做歷史命中統計
    historical_dates = eval_dates[1:]

    bt_results = []
    for eval_date in historical_dates:
        try:
            hist_top, _ = eng.execute_analysis_for_date(eval_date, True, params, progress_callback=None)
        except Exception:
            hist_top = []
        bt_results.append((eval_date, hist_top))

    num_routes = len(current_top)
    stats = {i: {'total': 0, 'hits': 0, 'current_miss': 0, 'max_miss': 0} for i in range(num_routes)}

    for eval_date, top in reversed(bt_results):
        if not top:
            continue
        nd = _smart_next_draws(eng, eval_date)
        for i in range(num_routes):
            if i >= len(top):
                continue
            try:
                is_hit, _, valid_draws, is_pending = _smart_evaluate_hit(eng, top[i], nd)
            except Exception:
                continue
            if not valid_draws or is_pending:
                continue
            st = stats[i]
            st['total'] += 1
            if is_hit:
                st['hits'] += 1
                st['current_miss'] = 0
            else:
                st['current_miss'] += 1
                st['max_miss'] = max(st['max_miss'], st['current_miss'])

    scored = []
    for i in range(num_routes):
        st = stats[i]
        if st['total'] <= 0:
            continue
        hit_rate = st['hits'] / st['total']
        avg_interval = st['total'] / st['hits'] if st['hits'] > 0 else st['total']
        score_rate = min(40.0, (hit_rate / 0.4) * 40.0)
        score_stable = max(0.0, 30.0 - (st['max_miss'] * 2.5))
        miss_ratio = st['current_miss'] / max(1, st['max_miss'])
        score_urgency = min(30.0, miss_ratio * 30.0)
        if st['current_miss'] >= st['max_miss'] and st['max_miss'] > 0:
            score_urgency += 10.0
        score = score_rate + score_stable + score_urgency
        st['score'] = score
        st['avg_interval'] = avg_interval
        st['hit_rate_pct'] = hit_rate * 100.0
        scored.append((i, score, st))
    scored.sort(key=lambda x: (x[1], x[2]['hit_rate_pct']), reverse=True)

    score_map = {i: (score, st) for i, score, st in scored}
    ranked = []
    for route_idx, score, st in scored[:target_count]:
        r = current_top[route_idx]
        ranked.append({
            'rank': len(ranked) + 1,
            'routeIndex': route_idx + 1,
            'score': round(score, 1),
            'hitRatePct': round(st['hit_rate_pct'], 1),
            'avgInterval': round(st['avg_interval'], 1),
            'currentMiss': int(st['current_miss']),
            'maxMiss': int(st['max_miss']),
            'reason': _smart_reason(st),
            'predNums': [int(x) for x in (r.get('latest_pred_nums') or [])],
            'isNonHit': bool(r.get('is_non_hit', False)),
            'isTail': bool(r.get('is_tail_match', False)),
        })

    champions = []
    for route_idx in range(min(5, len(current_top))):
        if route_idx not in score_map:
            continue
        score, st = score_map[route_idx]
        r = current_top[route_idx]
        champions.append({
            'rank': len(champions) + 1,
            'routeIndex': route_idx + 1,
            'score': round(score, 1),
            'hitRatePct': round(st['hit_rate_pct'], 1),
            'avgInterval': round(st['avg_interval'], 1),
            'currentMiss': int(st['current_miss']),
            'maxMiss': int(st['max_miss']),
            'predNums': [int(x) for x in (r.get('latest_pred_nums') or [])],
            'isNonHit': bool(r.get('is_non_hit', False)),
            'isTail': bool(r.get('is_tail_match', False)),
        })

    next_draws = _smart_next_draws(eng, limit_date)
    verification = []
    for item in ranked:
        route_idx = item['routeIndex'] - 1
        r = current_top[route_idx]
        is_hit, hit_nums, valid_draws, is_pending = _smart_evaluate_hit(eng, r, next_draws)
        verification.append({
            'routeIndex': item['routeIndex'],
            'status': 'pending' if is_pending else ('hit' if is_hit else 'miss'),
            'hitNums': [int(x) for x in hit_nums],
            'dates': [d[0].isoformat() for d in valid_draws],
        })

    return {
        'ok': True,
        'lookback': len(historical_dates),
        'recommendations': ranked,
        'champions': champions,
        'verification': verification,
        'nextDraws': [
            {'date': row[0].isoformat(), 'numbers': [int(x) for x in row[1]], 'special': row[2]}
            for row in next_draws[:3]
        ],
    }

import json as _json

def run_analysis_json(payload_json):
    """給網頁版 Pyodide 呼叫的單一入口:吃 JSON 字串、回傳 JSON 字串。
    這樣 JS 端不需要處理 Pyodide 的型別轉換細節,只要傳字串、收字串。
    """
    try:
        payload = _json.loads(payload_json)
        eng = LottoEngine(lotto_type=payload['lottoType'])
        rows = [(r[0], r[1], r[2]) for r in payload['rows']]
        eng.set_data(rows)

        mode_id = payload['modeId']
        eng.current_analysis_mode = mode_id
        base_settings = eng.get_default_mode_settings()
        custom_settings = payload.get('modeSettings') or {}
        base_settings.update(custom_settings)
        eng.mode_settings = {mode_id: base_settings}
        eng.pred_range_index = payload.get('predRangeIndex', 0)
        eng.data_limit_index = payload.get('dataLimitIndex', 2)

        params = eng.get_analysis_params()

        from datetime import date as _date
        y, m, d = [int(x) for x in payload['limitDateISO'].split('-')]
        limit_date = _date(y, m, d)
        exclude_today = bool(payload.get('excludeToday', False))

        top_list, next_list = eng.execute_analysis_for_date(
            limit_date, exclude_today, params, progress_callback=None
        )

        def serialize(idx, item):
            try:
                text = eng.format_rule_text(idx, item, params)
            except Exception as e:
                text = f"(顯示文字產生失敗:{type(e).__name__}: {e})"
            pred = item.get('latest_pred_nums') or []
            return {
                'text': text,
                'predNums': [int(x) for x in pred],
                'streak': item.get('streak'),
            }

        MAX_RESULTS = 30
        results = [serialize(i, it) for i, it in enumerate(top_list[:MAX_RESULTS])]
        next_results = [serialize(i, it) for i, it in enumerate(next_list[:MAX_RESULTS])]

        smart = {'ok': True, 'recommendations': [], 'champions': [], 'verification': [], 'nextDraws': [], 'lookback': 0}
        if payload.get('smartEnabled', True):
            try:
                smart = run_smart_recommendation(
                    eng, top_list, params, limit_date,
                    lookback=payload.get('smartLookback', 20),
                    target_count=payload.get('smartTargetCount', 5),
                )
            except Exception as smart_err:
                smart = {'ok': False, 'error': f'{type(smart_err).__name__}: {smart_err}', 'recommendations': [], 'champions': [], 'verification': [], 'nextDraws': [], 'lookback': 0}

        return _json.dumps({
            'ok': True,
            'results': results,
            'nextResults': next_results,
            'totalTop': len(top_list),
            'totalNext': len(next_list),
            'smart': smart,
        }, ensure_ascii=False)
    except Exception as e:
        import traceback
        return _json.dumps({
            'ok': False,
            'error': f'{type(e).__name__}: {e}',
            'trace': traceback.format_exc()[-2000:],
        }, ensure_ascii=False)
