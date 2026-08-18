"""閘門 ④｜依賴可控：沒有網路、沒有金鑰、沒有安裝任何套件，整套跑得起來嗎。

它在擋什麼：
  最自然的寫法永遠是「裝一個套件就好了」「從 CDN 拉一個圖表庫就好了」。
  一旦這樣，這份東西就只在寫它的那台機器上活著：
  斷網的會議室打不開、寄給同事打不開、放進 CI 也跑不動。

三件事一起查：
  1. scripts/ 與 checks/ 沒有任何需要安裝的套件
  2. dist/*.html 是單一檔案、零外部請求
  3. 沒有任何金鑰被寫死在程式碼裡

怎麼自己跑：  python3 checks/gate_offline.py
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
SITE = ROOT / 'site'
LOCAL = {'checks', 'scripts', 'domain'}
SKIP = {'__pycache__', '.git', '.venv', 'venv', 'node_modules'}

SECRETS = [
    re.compile(r'sk-[A-Za-z0-9]{16,}'),
    re.compile(r'AIza[A-Za-z0-9_\-]{20,}'),
    re.compile(r'(?i)(api[_-]?key|secret|password|token)\s*=\s*[\'"][^\'"]{12,}[\'"]'),
]
# dist 的頁面裡不該出現的東西。相對連結（href="town.html"）是刻意的，不算外部請求。
EXTERNAL = [
    (re.compile(r'(?:src|href)\s*=\s*[\'"]?(?:https?:)?//'), '連到外部網址的 src/href'),
    (re.compile(r'@import\s'), 'CSS @import'),
    (re.compile(r'\bfetch\s*\(|XMLHttpRequest|navigator\.sendBeacon'), '執行期的網路請求'),
    (re.compile(r'<link[^>]+rel\s*=\s*[\'"]?stylesheet'), '外部樣式表'),
]


def _py_files():
    out = []
    for base in ('scripts', 'checks'):
        for p in (ROOT / base).rglob('*.py'):
            if not any(part in SKIP for part in p.parts):
                out.append(p)
    out.append(ROOT / 'run_gates.py')
    return sorted(p for p in out if p.exists())


def _third_party(py):
    mods = set()
    for node in ast.walk(ast.parse(py.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            mods.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split('.')[0])
    builtin = set(getattr(sys, 'stdlib_module_names', ()))
    if not builtin:      # Python 3.9 的保守名單
        builtin = {'__future__', 'ast', 'collections', 'csv', 'dataclasses', 'datetime',
                   'hashlib', 'html', 'io', 'json', 'math', 'os', 'pathlib', 're',
                   'shutil', 'ssl', 'statistics', 'subprocess', 'sys', 'tempfile',
                   'time', 'typing', 'unicodedata', 'urllib', 'xml', 'zipfile',
                   'argparse', 'importlib', 'unittest', 'functools', 'enum'}
    return {m for m in mods if m not in builtin and m not in LOCAL}


def run():
    problems = []

    for py in _py_files():
        extra = _third_party(py)
        if extra:
            problems.append(f'{py.relative_to(ROOT)} import 了需要安裝的套件：{sorted(extra)}')
        text = py.read_text(encoding='utf-8')
        for pat in SECRETS:
            if pat.search(text):
                problems.append(f'{py.relative_to(ROOT)} 疑似把金鑰寫死在程式碼裡')
                break

    if not DIST.is_dir():
        problems.append('沒有 dist/：先跑 python3 scripts/build.py')
        return problems

    # 兩份輸出都要查：artifact 版與網站版是同一份內容的兩種包裝，
    # 只查其中一份，另一份混進外部請求時不會有人發現。
    pages = sorted(DIST.glob('*.html')) + sorted(SITE.glob('*.html'))
    if not pages:
        problems.append('dist/ 裡一頁都沒有')
    for page in pages:
        text = page.read_text(encoding='utf-8')
        for pat, why in EXTERNAL:
            m = pat.search(text)
            if m:
                snippet = text[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')
                problems.append(f'{page.parent.name}/{page.name} 有{why}：…{snippet}…')
        left = set(re.findall(r'__[A-Z0-9_]+__', text))
        if left:
            problems.append(f'{page.parent.name}/{page.name} 還留著沒被取代的 token：'
                            f'{sorted(left)}')
        for pat in SECRETS:
            if pat.search(text):
                problems.append(f'{page.parent.name}/{page.name} 疑似含有金鑰')
                break
    for page in sorted(SITE.glob('*.html')):
        head = page.read_text(encoding='utf-8')[:400].lower()
        for need in ('<!doctype html>', '<html lang="zh-hant">', '<meta charset="utf-8">'):
            if need not in head:
                problems.append(f'site/{page.name} 少了 {need}：'
                                f'網站版必須是完整文件，缺編碼宣告中文會變亂碼')
    return problems


def notes():
    """不影響紅綠燈的提醒。有沒有設環境變數不該改變起點，所以刻意不算違規。"""
    out = []
    for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY'):
        if os.environ.get(key):
            out.append(f'你的環境有 {key}。這一套完全不該用到它，'
                       f'unset 之後再跑一次，結果必須一模一樣。')
    if not (ROOT / 'data_TW').is_dir():
        out.append('沒有 data_TW/：閘門仍然可以跑（它們檢查的是 data/ 與 dist/），'
                   '但重新解析原始檔需要那個資料夾。')
    return out


HINT = ('需要安裝、需要連網才能用的東西，等於沒有人會用。'
        '資料一律內嵌進單一 HTML，字型用系統字型堆疊。')

if __name__ == '__main__':
    found = run()
    for n in notes():
        print('⚠ 提醒：', n)
    if found:
        print('閘門 ④ 依賴可控：✗')
        for line in found:
            print('   ', line)
        print('   提示：', HINT)
        raise SystemExit(1)
    print('閘門 ④ 依賴可控：✓')
