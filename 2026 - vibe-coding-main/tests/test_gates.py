"""pytest 橋接（選用）。

為什麼要有這個檔案：
  多數團隊的自動化測試跑在 pytest 上。這裡把同樣的五道閘門包成 pytest，
  讓這些閘門可以直接被你既有的測試流程與 CI 撿走用。

★ 關鍵設計：這裡**不重寫任何檢查邏輯**，只是呼叫 checks/ 裡的同一個 run()。
  一份規則一個實作點——同一個判斷寫兩份，遲早會不一致，而不一致就是不可控。
  （這是 LESSONS.md L32 的教訓：同一個特例被多處重複實作。）

用法（有裝 pytest 才需要；沒有的話用 python3 run_gates.py 就夠了）：
    python3 -m pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from checks import (gate_acceptance, gate_architecture, gate_contract,  # noqa: E402
                    gate_offline, gate_seal)

GATES = [
    ("①位置可控", gate_architecture),
    ("②形狀可控", gate_contract),
    ("③對錯可控", gate_acceptance),
    ("④依賴可控", gate_offline),
    ("⑤規則可控", gate_seal),
]


@pytest.mark.parametrize("name,module", GATES, ids=[g[0] for g in GATES])
def test_gate(name: str, module) -> None:
    problems = module.run()
    assert not problems, f"{name} 沒過：\n" + "\n".join("  · " + p for p in problems)
