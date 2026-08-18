#!/usr/bin/env python3
"""把版面文字改成本專案的中文排版規則。

    python3 scripts/fix_typography.py          # 只報告
    python3 scripts/fix_typography.py --write  # 實際改寫

兩條硬規則：

  1. 中文字與緊鄰的英文、數字之間不留空格。英文片語內部照常空格。
  2. 不使用破折號，一律改用冒號。數字區間的連接號與英文複合詞裡的連字號不動。

處理範圍分三種，因為同一條規則在不同語境的風險不一樣：

  HTML 文字   可以跨行收。瀏覽器會把換行算成一個空格，所以「中文\\n  數字」
              渲染出來一樣有空格，不接起來就改不掉。
  JavaScript  只收同一行的空格。跨行接會把「// 中文註解」跟下一行程式接在一起，
              整段變成註解。
  Python      同上，而且 docstring、註解、含檔案路徑的行整行不動：
              那些是寫給開發者看的中英混排，收掉空格會變成英文的錯字；
              而路徑裡的空格收掉就打不開檔案。
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CJK = r'一-鿿々〆豈-﫿'
ZH = CJK + r'、。，：；（）「」『』！？'
LATIN = r'0-9A-Za-z+'
INLINE = r'b|span|code|i|em|small|a|strong|sub|sup'
MINUS = '−'


def rules(ws):
    """ws 是「什麼算空白」：HTML 給的版本含換行，程式碼給的只含空格與 tab。"""
    return [
        (re.compile(r'—{1,2}'), '：'),
        (re.compile(f'([{ZH}]){ws}([{LATIN}])'), r'\1\2'),
        (re.compile(f'([{LATIN}%°\\)\\]]){ws}([{ZH}])'), r'\1\2'),
        (re.compile(f'(\\}}){ws}([{ZH}])'), r'\1\2'),
        (re.compile(f'([{ZH}]){ws}(\\$?\\{{)'), r'\1\2'),
        (re.compile(f'([{ZH}]){ws}([+{MINUS}-]\\d)'), r'\1\2'),
        # 數字被行內標籤包住時，空格夾在標籤外面。空標籤是等 JS 填數字的位置。
        (re.compile(f'([{ZH}]){ws}(<(?:{INLINE})\\b[^>]*>)'), r'\1\2'),
        (re.compile(f'([{ZH}]){ws}(</(?:{INLINE})>)'), r'\1\2'),
        (re.compile(f'(</(?:{INLINE})>){ws}([{ZH}])'), r'\1\2'),
        (re.compile(r'([0-9%年]) *– *([0-9])'), r'\1–\2'),
    ]


TEXT_RULES = rules(r'(?:[ \t]*\n[ \t]*|[ \t]+)')
# 字串邊界的空格：'…全國 ' + n + ' 元' 接起來就是「全國 8,993,149 元」。
# 只在程式碼裡處理；HTML 屬性值裡的引號不是字串邊界。
QUOTE_EDGE = [
    (re.compile(f'([\'"`])[ \t]+([{CJK}])'), r'\1\2'),
    (re.compile(f'([{CJK}])[ \t]+([\'"`])'), r'\1\2'),
]
# 樣板字串裡的換行在 HTML 會塌成一個空格，所以也要接起來。只認「中文換行 ${」
# 與「} 換行中文」這兩種：兩者都只可能出現在樣板字串內，不會誤傷中文註解。
LITERAL_WRAP = [
    (re.compile(f'([{ZH}])\n[ \t]*(\\$\\{{)'), r'\1\2'),
    (re.compile(f'(\\}})\n[ \t]*([{ZH}])'), r'\1\2'),
]
CODE_RULES = rules(r'[ \t]+') + QUOTE_EDGE + LITERAL_WRAP
CLEANUP = [(re.compile('：：'), '：'), (re.compile('：(?=[，。；、])'), '')]

# 檔案路徑裡的空格是路徑的一部分（data_TW/「99-115 不動產買賣及租賃」）
PATH_HINTS = ('data_TW', 'ROOT /', 'SRC =', 'PDF =', 'AREA_DIR',
              '.csv', '.xlsx', '.pdf', '.xml', '.json', '.ods', 'glob(', 'Path(')


def fix(text, rs):
    for pat, rep in rs:
        text = pat.sub(rep, text)
    for pat, rep in CLEANUP:
        text = pat.sub(rep, text)
    return text


def fix_py(src):
    quotes = (chr(34) * 3, chr(39) * 3)
    out, doc = [], None
    for line in src.split('\n'):
        bare = line.lstrip()
        if doc is not None:
            out.append(line)
            if doc in line:
                doc = None
            continue
        opened = next((q for q in quotes if bare.startswith(q)), None)
        if opened is not None:
            out.append(line)
            if line.count(opened) < 2:
                doc = opened
            continue
        if bare.startswith('#') or any(h in line for h in PATH_HINTS):
            out.append(line)
            continue
        code, sep, tail = line.partition('  # ')
        out.append(fix(code, CODE_RULES) + sep + tail)
    return '\n'.join(out)


SPLIT = re.compile(
    r'(<style>.*?</style>)'
    r'|(<script type="application/json"[^>]*>.*?</script>)'
    r'|(<script>.*?</script>)', re.S)


def fix_html(src):
    out, pos = [], 0
    for m in SPLIT.finditer(src):
        out.append(fix(src[pos:m.start()], TEXT_RULES))
        style, data, js = m.groups()
        out.append(fix(js, CODE_RULES) if js else m.group(0))
        pos = m.end()
    out.append(fix(src[pos:], TEXT_RULES))
    return ''.join(out)


def process(path):
    src = path.read_text(encoding='utf-8')
    return src, (fix_py(src) if path.suffix == '.py' else fix_html(src))


def main():
    write = '--write' in sys.argv
    targets = (sorted((ROOT / 'src').glob('*.template.html'))
               + sorted((ROOT / 'scripts').glob('prep_*.py')))
    total = 0
    for p in targets:
        old, new = process(p)
        if old == new:
            continue
        import difflib
        n = sum(1 for op in difflib.SequenceMatcher(None, old, new).get_opcodes()
                if op[0] != 'equal')
        total += n
        print(f'  {p.relative_to(ROOT)}：{n} 處')
        if write:
            p.write_text(new, encoding='utf-8')
    print(('已改寫' if write else '尚未寫入，加 --write 才會改') + f'　共 {total} 處')


if __name__ == '__main__':
    main()
