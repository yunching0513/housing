"""閘門 ④｜依賴可控：沒有金鑰、沒有網路、沒有安裝任何套件，整套跑得起來嗎。

它在擋什麼：
  AI 很自然會寫出「要先設 OPENAI_API_KEY 才能跑」的東西。
  一旦這樣，40 個人裡就有 35 個卡在第一步，而且 CI 也跑不動。

三件事一起查：
  1. 完整流程能用假插頭跑完（三個固定樣本）
  2. 沒有任何第三方套件被 import（只准內建函式庫）
  3. 沒有任何金鑰被寫死在程式碼裡

怎麼自己跑：  python3 checks/gate_offline.py
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path
from typing import List, Set

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv"}

# Python 內建與本專案自己的模組 → 允許
LOCAL_PACKAGES = {"domain", "application", "adapter", "infrastructure",
                  "entrypoints", "checks", "tests", "schemas"}

# 看起來像金鑰的字串（寫死在程式碼裡就是洩漏）
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]"),
]


def _py_files() -> List[Path]:
    out = []
    for p in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def _third_party_imports(py: Path) -> Set[str]:
    tree = ast.parse(py.read_text(encoding="utf-8"))
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods.add(node.module.split(".")[0])
    if hasattr(sys, "stdlib_module_names"):          # Python 3.10+
        builtin = set(sys.stdlib_module_names)
    else:                                            # 3.9 保守名單
        builtin = {"__future__", "ast", "dataclasses", "json", "os", "re", "sys",
                   "typing", "pathlib", "hashlib", "argparse", "textwrap",
                   "importlib", "unittest", "collections", "functools", "enum"}
    return {m for m in mods if m not in builtin and m not in LOCAL_PACKAGES}


def run() -> List[str]:
    problems: List[str] = []

    # 1. 完整流程用假插頭跑完
    try:
        from application.use_cases.analyze_meal import AnalyzeMeal
        from domain.exceptions import NotFoodError
        from infrastructure.fake_nutrition import (SAMPLE_CROPPED, SAMPLE_FOOD,
                                                   SAMPLE_NOT_FOOD,
                                                   FakeNutritionGateway)
        uc = AnalyzeMeal(FakeNutritionGateway())
        uc.execute(SAMPLE_FOOD)
        uc.execute(SAMPLE_CROPPED)
        try:
            uc.execute(SAMPLE_NOT_FOOD)
        except NotFoodError:
            pass
    except NotImplementedError:
        problems.append("流程還跑不完：AnalyzeMeal.execute 還沒實作（上機 ① 要做的）")
    except Exception as exc:
        problems.append(f"離線流程失敗：{type(exc).__name__}: {exc}")

    # 2. 不准有第三方套件
    for py in _py_files():
        extra = _third_party_imports(py)
        # pytest 只出現在 tests/ 是可以的（選用；接既有 CI 時會用到）
        if py.parts[-2] == "tests":
            extra -= {"pytest"}
        if extra:
            problems.append(f"{py.relative_to(ROOT)} import 了需要安裝的套件：{sorted(extra)}")

    # 3. 不准把金鑰寫死
    for py in _py_files():
        text = py.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                problems.append(f"{py.relative_to(ROOT)} 疑似把金鑰寫死在程式碼裡")
                break

    return problems


def notes() -> List[str]:
    """不影響紅綠燈的提醒。（刻意不算違規——否則有設金鑰的人起點就跟別人不同。）"""
    out = []
    if os.environ.get("OPENAI_API_KEY"):
        out.append("你的環境有 OPENAI_API_KEY。這個閘門不該用到它——"
                   "把它 unset 再跑一次，結果必須一樣。")
    return out


HINT = ("需要安裝、需要金鑰才能跑的閘門，等於沒有閘門。"
        "真的要呼叫外部服務就寫在 adapter/，並保證 fake 那條路徑仍然單獨跑得完。")

if __name__ == "__main__":
    found = run()
    if found:
        print("閘門 ④ 依賴可控：✗")
        for line in found:
            print("   ", line)
        print("   提示：", HINT)
        raise SystemExit(1)
    print("閘門 ④ 依賴可控：✓")
