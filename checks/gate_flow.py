"""閘門 ①｜資料流可控：東西有沒有照同一個方向流。

它在擋什麼：
  最省事的做法永遠是「就近取用」——版面缺一個數字，就直接去讀原始檔；
  或是新增了一份中間檔，卻沒有任何一頁用到它。兩種都會讓資料悄悄分岔：
  同一個數字在兩個地方各算一次，其中一邊漏更新就開始說不一樣的話。

規定的方向（AGENTS.md §1）：

    data_TW/ 、 data/sources/  →  prep_*.py  →  data/tw_*.json  →  build.py  →  dist/

怎麼自己跑：  python3 checks/gate_flow.py
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'
DATA = ROOT / 'data'
SRC = ROOT / 'src'
EXCEPTIONS = pathlib.Path(__file__).resolve().parent / 'traceable_exceptions.json'


def _scripts():
    return sorted(p for p in SCRIPTS.glob('*.py') if '__pycache__' not in str(p))


def _producers(name):
    """哪幾支腳本產生這份中間檔。認的是 `OUT = ROOT / 'data' / '<檔名>'` 這個慣例。"""
    pat = re.compile(r"(OUT\w*\s*=|--out'?,?\s*default=).*" + re.escape(name))
    return [p.name for p in _scripts()
            if any(pat.search(line) for line in p.read_text(encoding='utf-8').splitlines())]


def _consumers(name):
    """哪幾支腳本或哪一頁用到這份中間檔（產生它的那一支不算）。"""
    out = []
    for p in _scripts():
        text = p.read_text(encoding='utf-8')
        if name in text and p.name not in _producers(name):
            out.append(p.name)
    return out


def _template_numbers():
    """版面文字裡出現的統計數字（去掉樣式、程式與標籤屬性，只留文字）。"""
    found = {}
    for tpl in sorted(SRC.glob('*.template.html')):
        text = re.sub(r'<style>.*?</style>|<script[^>]*>.*?</script>', '',
                      tpl.read_text(encoding='utf-8'), flags=re.S)
        text = re.sub(r'<[^>]+>', ' ', text)      # 屬性裡的數字是座標，不是統計
        for lit in re.findall(r'\d[\d,]*\.?\d*', text):
            # 沒有小數點也沒有千分位的兩位數以內，多半是編號或年份片段
            if float(lit.replace(',', '')) < 100 and ',' not in lit and '.' not in lit:
                continue
            found.setdefault(tpl.name, set()).add(lit)
    return found


def _data_numbers():
    """data/ 裡出現過的所有數字，含常見的四捨五入與換算形。"""
    pool = set()

    def grab(o):
        if isinstance(o, dict):
            [grab(v) for v in o.values()]
        elif isinstance(o, list):
            [grab(v) for v in o]
        elif isinstance(o, bool):
            pass
        elif isinstance(o, (int, float)):
            pool.add(round(float(o), 6))
        elif isinstance(o, str):
            for m in re.findall(r'-?\d+\.?\d*', o):
                try:
                    pool.add(round(float(m), 6))
                except ValueError:
                    pass

    for p in sorted(DATA.glob('*.json')):
        grab(json.loads(p.read_text(encoding='utf-8')))
    # 版面會四捨五入、會換成萬與千，這些都算「找得到出處」
    derived = set(pool)
    for v in pool:
        for nd in (0, 1, 2):
            derived |= {round(v, nd), round(v * 100, nd), round(v / 100, nd),
                        round(v / 1000, nd), round(v / 10000, nd)}
    return derived


def run():
    problems = []

    # ── 方向：版面不准碰原始檔，解析程式不准回頭碰產出 ──
    build = SCRIPTS / 'build.py'
    if not build.exists():
        problems.append('找不到 scripts/build.py')
    elif 'data_TW' in build.read_text(encoding='utf-8'):
        problems.append('scripts/build.py 直接碰了 data_TW/：版面只能讀 data/*.json')
    for p in sorted(SCRIPTS.glob('prep_*.py')):
        if re.search(r"['\"]dist['\"]|/ *dist", p.read_text(encoding='utf-8')):
            problems.append(f'scripts/{p.name} 碰到了 dist/：解析程式不准回頭改產出')

    # ── 每一份中間檔都要有人產生、也要有人用 ──
    for path in sorted(DATA.glob('tw_*.json')):
        made, used = _producers(path.name), _consumers(path.name)
        if not made:
            problems.append(f'data/{path.name} 沒有任何 prep 腳本產生它——'
                            f'手工檔會在來源更新的那天靜靜過期')
        if len(made) > 1:
            problems.append(f'data/{path.name} 有兩支以上的腳本在寫：{made}')
        if not used:
            problems.append(f'data/{path.name} 沒有任何一頁或腳本用到它——'
                            f'不是忘了接上頁面，就是該刪掉')

    # ── 版面要的 token 與 build.py 的對照表要對得起來 ──
    build_src = build.read_text(encoding='utf-8') if build.exists() else ''
    for tpl in sorted(SRC.glob('*.template.html')):
        for token in set(re.findall(r'__[A-Z0-9_]+__', tpl.read_text(encoding='utf-8'))):
            if token not in build_src:
                problems.append(f'src/{tpl.name} 要 {token}，但 build.py 沒有定義它')

    # ── 版面上的每一個統計數字都要在 data/ 裡找得到 ──
    allowed = {}
    if EXCEPTIONS.exists():
        for e in json.loads(EXCEPTIONS.read_text(encoding='utf-8'))['exceptions']:
            allowed.setdefault(e['file'], set()).add(e['value'])
    pool = _data_numbers()
    for fname, lits in sorted(_template_numbers().items()):
        for lit in sorted(lits):
            if lit in allowed.get(fname, ()):
                continue
            if round(float(lit.replace(',', '')), 6) not in pool:
                problems.append(f'src/{fname} 印了 {lit}，但 data/ 裡找不到這個數字——'
                                f'手寫的統計會在來源更新的那天變成錯的')
    return problems


HINT = ('數字一律從 data/tw_*.json 讀，不要寫死在版面上。'
        '真的不是統計數字（例如圖形簡化的容差）就登記到 checks/traceable_exceptions.json，'
        '那是受保護檔案，等於留下一筆人為決定的紀錄。')

if __name__ == '__main__':
    found = run()
    if found:
        print('閘門 ① 資料流可控：✗')
        for line in found:
            print('   ', line)
        print('   提示：', HINT)
        raise SystemExit(1)
    print('閘門 ① 資料流可控：✓')
