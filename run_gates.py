"""五道閘門，一行跑完，印一張計分板。

    python3 run_gates.py

沒有安裝步驟、不需要金鑰、不需要網路。離開碼 0 是全綠、1 是有紅燈，
可以直接接進 CI 當守門員。

閘門的想法來自臺大計中 2026「從 Vibe Coding 到 Production Architecture」
的上機素材包（github.com/jeffhong824/vibe-coding），五道的內容依這個專案改寫：
那份教材防的是「AI 亂寫程式」，這裡防的是「數字悄悄變成錯的」。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from checks import (gate_contract, gate_flow, gate_offline,  # noqa: E402
                    gate_reconcile, gate_seal)

GATES = [
    ('①', '資料流可控', '流向閘門', gate_flow),
    ('②', '形狀可控', '契約閘門', gate_contract),
    ('③', '對帳可控', '對帳閘門', gate_reconcile),
    ('④', '依賴可控', '離線閘門', gate_offline),
    ('⑤', '規則可控', '封印閘門', gate_seal),
]
BAR = '─' * 60


def main() -> int:
    print()
    print('  可控度計分板'.ljust(30) + 'python3 run_gates.py')
    print('  ' + BAR)

    passed, details = 0, []
    for num, switch, name, mod in GATES:
        try:
            problems = mod.run()
        except Exception as exc:      # 閘門自己壞掉也要看得見，不要靜靜跳過
            problems = [f'閘門執行失敗：{type(exc).__name__}: {exc}']
        if problems:
            details.append((num, switch, name, problems, getattr(mod, 'HINT', '')))
        else:
            passed += 1
        dots = '.' * (26 - len(switch) * 2 - len(name) * 2)
        print(f'  {num}  {switch}   {name} {dots} {"✓" if not problems else "✗"}')

    print('  ' + BAR)
    print(f'  {passed} / {len(GATES)}')

    for num, switch, name, problems, hint in details:
        print()
        print(f'  {num} {switch}（{name}）沒過：')
        for line in problems[:12]:
            print(f'      · {line}')
        if len(problems) > 12:
            print(f'      · …另外還有 {len(problems) - 12} 項')
        if hint:
            print(f'      提示：{hint}')

    for note in gate_offline.notes():
        print(f'\n  ⚠ 提醒：{note}')
    print()
    return 0 if passed == len(GATES) else 1


if __name__ == '__main__':
    raise SystemExit(main())
