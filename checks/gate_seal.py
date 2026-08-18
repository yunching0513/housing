"""閘門 ⑤｜規則可控：有沒有人（多半是 AI）把規則或已發布的數字改掉了。

★ 這是最容易被忽略、卻最重要的一道。

AI 收到的目標是「讓檢查通過」，不是「讓結果正確」。
而讓檢查通過最快的方式，永遠是**把檢查改掉**。這個專案有實際案例：
`scripts/prep_pop_series.py` 的總數對帳曾經擋下來（109 年差 2,000），
處理方式是把容差放寬。理由是真的（來源以千人為單位），
但那次改動的性質就是「遇到紅燈，改了檢查而不是改資料」。

所以這一道封兩種東西：

  A. 規則檔案：AGENTS.md、schemas/、checks/、run_gates.py 的 SHA-256。
     改一個字就紅。

  B. 已發布的數字：報告與頁面上引用的關鍵數字（空屋率、社宅完工戶數、
     房價所得比、租金中位數…）。這些數字本來就會隨資料更新而變，
     但**必須是人明確決定要更新**，不能是某支解析程式被改了之後
     悄悄變成另一個值。

刻意要改的時候（人類決定，不是 AI 順手）：

    python3 checks/seal.py        ← 重新封印，並在 README 或提交訊息說明改了什麼

怎麼自己跑：  python3 checks/gate_seal.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HERE = pathlib.Path(__file__).resolve().parent
SEAL_FILE = HERE / 'protected.sha256'
FIG_FILE = HERE / 'figures.json'

# ── A. 受保護的規則檔案 ────────────────────────────────────────────────
PROTECTED_GLOBS = ['AGENTS.md', 'CLAUDE.md', 'run_gates.py',
                   'schemas/*.json', 'checks/*.py', 'checks/*.json']

# ── B. 已發布的數字。格式：檔名:欄位路徑 ────────────────────────────────
# 選的原則：這個數字有沒有被寫進報告、簡報或頁面的標題。
# 會被引用的數字才需要封印；中間過程的數字改了不影響任何人。
FIGURES = [
    ('tw_housing.json:national.houses', '住宅總數'),
    ('tw_housing.json:national.households', '家戶總數'),
    ('tw_housing.json:national.idle', '普查認定沒在使用的住宅'),
    ('tw_housing.json:national.vacancy', '普查空屋率'),
    ('tw_moi_series.json:national.rates.-1', '最新一期用電低度使用率'),
    ('tw_social_build.json:national.total.done', '社宅已完工戶數'),
    ('tw_social_build.json:national.total.total', '社宅總計戶數'),
    ('tw_social_build.json:national.donePer1000', '社宅每千戶完工數'),
    ('tw_social_housing.json:national.matched', '包租代管累計媒合'),
    ('tw_social_housing.json:national.live', '包租代管仍有效契約'),
    ('tw_affordability.json:national.pir', '全國房價所得比'),
    ('tw_affordability.json:national.burden', '全國房貸負擔率'),
    ('tw_pop_series.json:national.-1', '最新一年常住人口'),
    ('tw_rent.json:national.rent', '全國月租金中位數'),
    ('tw_rent.json:national.grid.whole.social.ping', '社宅包租代管整戶每坪租金'),
    ('tw_rent.json:national.grid.whole.nonSocial.ping', '非社宅整戶每坪租金'),
]


def protected_files():
    out = []
    for pattern in PROTECTED_GLOBS:
        if '*' in pattern:
            out += sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
        else:
            out.append(pattern)
    return sorted(set(out))


def dig(blob, path):
    """照 'national.rates.-1' 這種路徑取值。取不到就回 None，由呼叫端報告。"""
    node = blob
    for part in path.split('.'):
        if isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(node, dict):
            if part not in node:
                return None
            node = node[part]
        else:
            return None
    return node


def current_figures():
    out = {}
    for ref, label in FIGURES:
        name, _, path = ref.partition(':')
        f = ROOT / 'data' / name
        out[ref] = {'label': label,
                    'value': dig(json.loads(f.read_text(encoding='utf-8')), path)
                    if f.exists() else '（檔案不存在）'}
    return out


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_hashes():
    out = {}
    for rel in protected_files():
        p = ROOT / rel
        # 封印檔自己不封自己，否則寫檔的當下就對不上
        if p.name in ('protected.sha256',):
            continue
        out[rel] = digest(p) if p.exists() else 'MISSING'
    return out


def stored_hashes():
    if not SEAL_FILE.exists():
        return {}
    out = {}
    for line in SEAL_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        sha, _, rel = line.partition('  ')
        out[rel.strip()] = sha.strip()
    return out


def write_seal():
    FIG_FILE.write_text(json.dumps(current_figures(), ensure_ascii=False, indent=1) + '\n',
                        encoding='utf-8')
    lines = ['# 受保護檔案的封印。要改規則請人類決定，改完跑 python3 checks/seal.py，',
             '# 並在提交訊息裡寫清楚改了什麼、為什麼。']
    lines += [f'{sha}  {rel}' for rel, sha in current_hashes().items()]
    SEAL_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def run():
    problems = []
    want = stored_hashes()
    if not want:
        return ['找不到封印檔 checks/protected.sha256——先跑 python3 checks/seal.py']

    have = current_hashes()
    for rel, sha in want.items():
        actual = have.get(rel)
        if actual is None:
            problems.append(f'受保護的檔案被刪掉了：{rel}')
        elif actual == 'MISSING':
            problems.append(f'受保護的檔案不見了：{rel}')
        elif actual != sha:
            problems.append(f'受保護的檔案被改了：{rel}')
    for rel in have:
        if rel not in want:
            problems.append(f'封印檔沒有涵蓋 {rel}——跑 python3 checks/seal.py 補上')

    if not FIG_FILE.exists():
        problems.append('找不到 checks/figures.json——先跑 python3 checks/seal.py')
        return problems
    sealed = json.loads(FIG_FILE.read_text(encoding='utf-8'))
    now = current_figures()
    for ref, rec in now.items():
        old = sealed.get(ref)
        if old is None:
            problems.append(f'已發布數字「{rec["label"]}」是新的，封印檔還沒有它')
        elif old['value'] != rec['value']:
            problems.append(f'已發布的數字變了：{rec["label"]}（{ref}）'
                            f'{old["value"]} → {rec["value"]}')
    for ref in sealed:
        if ref not in now:
            problems.append(f'封印檔裡的「{sealed[ref]["label"]}」已經不在 FIGURES 清單裡')
    return problems


HINT = ('如果這是你自己有意識改的（換了新一期資料、改了口徑）：'
        '跑 python3 checks/seal.py 重新封印，並在提交訊息說明。'
        '如果不是你改的——那就是有人為了讓紅燈消失動了規則或動了數字，'
        '用 git diff 看改了什麼，還原它，然後回去修資料。')

if __name__ == '__main__':
    found = run()
    if found:
        print('閘門 ⑤ 規則可控：✗')
        for line in found:
            print('   ', line)
        print('   提示：', HINT)
        raise SystemExit(1)
    print('閘門 ⑤ 規則可控：✓')
