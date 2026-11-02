"""五道閘門，一行跑完，印一張計分板。

    python3 run_gates.py

沒有任何安裝步驟、不需要金鑰、不需要網路。
全班在同一個起點跑出來的結果應該一模一樣——那就是「可控」的第一個證據。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from checks import (gate_acceptance, gate_architecture, gate_contract,  # noqa: E402
                    gate_offline, gate_seal)

GATES = [
    ("①", "位置可控", "架構閘門", gate_architecture),
    ("②", "形狀可控", "契約閘門", gate_contract),
    ("③", "對錯可控", "驗收閘門", gate_acceptance),
    ("④", "依賴可控", "離線閘門", gate_offline),
    ("⑤", "規則可控", "封印閘門", gate_seal),
]

BAR = "─" * 66


def main() -> int:
    print()
    print("  可控度計分板".ljust(30) + "python3 run_gates.py")
    print("  " + BAR)

    passed = 0
    details = []
    for num, switch, name, mod in GATES:
        try:
            problems = mod.run()
        except Exception as exc:  # 閘門自己壞掉也要看得見，不要靜靜跳過
            problems = [f"閘門執行失敗：{type(exc).__name__}: {exc}"]
        mark = "✓" if not problems else "✗"
        if not problems:
            passed += 1
        print(f"  {num}  {switch}   {name} {'.' * (14 - len(name) * 2 // 2)}. {mark}")
        if problems:
            details.append((num, switch, name, problems, getattr(mod, "HINT", "")))

    print("  " + BAR)
    print(f"  {passed} / {len(GATES)}")

    if details:
        print()
        for num, switch, name, problems, hint in details:
            print(f"  {num} {switch}（{name}）沒過：")
            for line in problems:
                print(f"      · {line}")
            if hint:
                print(f"      提示：{hint}")
            print()

    for note in gate_offline.notes():
        print(f"  ⚠ 提醒：{note}")

    if passed == len(GATES):
        print()
        print("  五個都綠了。接下來的重點不是你自己綠——")
        print("  是問你旁邊的人：你們的檔案結構、欄位名稱、回傳形狀是不是一樣的？")
    print()
    return 0 if passed == len(GATES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
