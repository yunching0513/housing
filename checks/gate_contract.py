"""閘門 ②｜形狀可控：data/tw_*.json 的欄位、型別、數量有沒有跑掉。

它在擋什麼：
  順手多一個欄位、把 vacancy 從百分比改成小數、把 counties 從 22 筆變成 21 筆。
  每一個單獨看都很合理，合起來就是頁面靜靜地少畫一格、或畫出一個錯的數字。

★ 雙向驗證（缺一邊等於裝飾品）：
  正向：現有的 14 份資料一定要過   → 契約不會誤殺
  反向：已知壞掉的形狀一定要被擋   → 契約真的有牙齒

怎麼自己跑：  python3 checks/gate_contract.py
"""
from __future__ import annotations

import json
import pathlib

from checks.minischema import SchemaError, validate

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SCHEMAS = ROOT / 'schemas'

# ── 反向樣本：每一個都是真的會發生的走樣 ──────────────────────────────
BAD = [
    ({'name': '臺北市', 'houses': 1000}, 'tw_housing.json',
     '拿一筆縣市紀錄當成整份檔案（少了 period、national…）'),
    ('不是物件', 'tw_housing.json', '整份變成字串'),
]


def _bad_variants(good, schema):
    """從真資料衍生三種走樣，證明契約擋得住。

    直接改真資料而不是手寫假資料：手寫的假資料會跟真的結構脫節，
    脫節之後它擋得住的東西就跟真實情況無關了。
    """
    out = []
    if isinstance(good.get('counties'), list) and len(good['counties']) > 1:
        drop = dict(good, counties=good['counties'][:-1])
        out.append((drop, '少了一個縣市'))
        first = dict(good['counties'][0])
        first['notes'] = '順手多給的欄位'
        out.append((dict(good, counties=[first] + good['counties'][1:]),
                    '縣市紀錄多了契約沒定義的欄位'))
        first2 = dict(good['counties'][0])
        for k, v in first2.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                first2[k] = str(v)
                out.append((dict(good, counties=[first2] + good['counties'][1:]),
                            f'{k} 從數字變成字串'))
                break
    return out


def run():
    problems = []
    schemas = sorted(SCHEMAS.glob('tw_*.json'))
    if not schemas:
        return ['schemas/ 裡一份契約都沒有']

    for spath in schemas:
        dpath = DATA / spath.name
        if not dpath.exists():
            problems.append(f'契約 schemas/{spath.name} 找不到對應的 data/{spath.name}')
            continue
        schema = json.loads(spath.read_text(encoding='utf-8'))
        data = json.loads(dpath.read_text(encoding='utf-8'))
        try:
            validate(data, schema)
        except SchemaError as exc:
            problems.append(f'data/{spath.name} 不符合契約：{exc}')
            continue
        # 反向：這份資料的已知走樣版本必須被擋下來
        for bad, why in _bad_variants(data, schema):
            try:
                validate(bad, schema)
            except SchemaError:
                continue
            problems.append(f'契約沒有牙齒：data/{spath.name} 的「{why}」竟然通過')

    for payload, name, why in BAD:
        schema = json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
        try:
            validate(payload, schema)
        except SchemaError:
            continue
        problems.append(f'契約沒有牙齒：{name} 的「{why}」竟然通過')

    # 有資料卻沒有契約，等於這份資料沒人管
    have = {p.name for p in DATA.glob('tw_*.json')}
    for name in sorted(have - {p.name for p in schemas}):
        problems.append(f'data/{name} 沒有對應的契約——在 schemas/ 補一份')
    return problems


HINT = ('契約是版面唯一的事實來源。輸出不合就改產出資料的那支 prep 程式，'
        '不要改 schemas/。真的要改契約：那是規則變更，跑 python3 checks/seal.py 重新封印。')

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    found = run()
    if found:
        print('閘門 ② 形狀可控：✗')
        for line in found:
            print('   ', line)
        print('   提示：', HINT)
        raise SystemExit(1)
    print('閘門 ② 形狀可控：✓')
