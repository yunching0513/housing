"""閘門 ①｜位置可控：東西有沒有放在對的樓層。

它在擋什麼：
  AI 最省事的做法是「就近堆疊」——看到哪裡有現成的檔案就往那裡塞。
  這支檔案掃過每一個 .py，看有沒有人在地基（domain）或辦公室（application）
  裡偷接外面的東西，或是反過來依賴外牆。

怎麼自己跑：  python3 checks/gate_architecture.py
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set

ROOT = Path(__file__).resolve().parent.parent

# 「外面的東西」＝框架、SDK、網路、資料庫。地基與辦公室都不准碰。
FORBIDDEN_EXTERNAL = {
    "requests", "httpx", "urllib", "urllib3", "http", "socket",
    "openai", "anthropic", "google", "boto3", "cohere", "mistralai",
    "sqlalchemy", "psycopg", "sqlite3", "redis", "pymongo",
    "fastapi", "flask", "django", "starlette", "uvicorn",
}
# 反向依賴：內層不准知道外層的存在
FORBIDDEN_OUTER = {"adapter", "infrastructure", "entrypoints"}

GUARDED_LAYERS = ("domain", "application")


def _top_level_imports(py_file: Path) -> Set[str]:
    """收集這個檔案 import 的頂層模組名（含函式內部的 import）。

    刻意走進 FunctionDef——把 import 藏在函式裡是最常見的規避手法。
    """
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
    return mods


def _dynamic_import_calls(py_file: Path) -> Set[str]:
    """抓 importlib.import_module("openai") 這種用字串繞過的寫法。"""
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    found: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id
        if name not in ("import_module", "__import__"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.add(arg.value.split(".")[0])
    return found


def run() -> List[str]:
    """回傳違規清單。空清單＝通過。"""
    problems: List[str] = []
    for layer in GUARDED_LAYERS:
        base = ROOT / layer
        if not base.exists():
            problems.append(f"找不到 {layer}/ 資料夾——樓層結構被改掉了")
            continue
        for py in sorted(base.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            rel = py.relative_to(ROOT)
            imported = _top_level_imports(py) | _dynamic_import_calls(py)
            bad = imported & (FORBIDDEN_EXTERNAL | FORBIDDEN_OUTER)
            if layer == "domain":
                bad |= imported & {"application"}
            if bad:
                problems.append(f"{rel} 依賴了不該依賴的東西：{sorted(bad)}")

    # 樓層本身要存在（AI 有時候會「整理」掉空資料夾）
    for layer in ("domain", "application", "adapter", "infrastructure", "entrypoints"):
        if not (ROOT / layer).is_dir():
            problems.append(f"樓層 {layer}/ 不見了")
    return problems


HINT = (
    "正解不是把 import 移到別的地方，是在 application/ports/ 定義插座（Protocol），"
    "把實作搬到 adapter/。"
)

if __name__ == "__main__":
    found = run()
    if found:
        print("閘門 ① 位置可控：✗")
        for line in found:
            print("   ", line)
        print("   提示：", HINT)
        raise SystemExit(1)
    print("閘門 ① 位置可控：✓")
