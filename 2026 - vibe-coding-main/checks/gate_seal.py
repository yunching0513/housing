"""閘門 ⑤｜規則可控：有沒有人（多半是 AI）把規則本身改掉了。

★ 這是最容易被忽略、卻最重要的一道。

AI 收到的目標是「讓檢查通過」，不是「讓產品正確」。
而讓檢查通過最快的方式，永遠是**把檢查刪掉**。實務上真的會看到：
  · 把 FORBIDDEN 清單裡的套件名字拿掉
  · 把斷言 `assert x < 0.6` 改成 `assert x < 1.0`
  · 直接改 SPEC.md 的驗收標準，讓現況剛好符合
  · 在 schema 加上 "additionalProperties": true

這支檔案的做法：把「規則類檔案」的 SHA-256 存下來（checks/protected.sha256），
每次跑閘門都比對一次。內容一改，這道就紅。

刻意要改規則的時候（人類決定，不是 AI 順手）：
    python3 checks/seal.py        ← 重新封印，並在 SPEC.md 變更紀錄留一列

怎麼自己跑：  python3 checks/gate_seal.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
SEAL_FILE = Path(__file__).resolve().parent / "protected.sha256"

# 受保護的檔案／資料夾（＝規則本身，不是實作）
PROTECTED: List[str] = [
    "AGENTS.md",
    "CLAUDE.md",
    "SPEC.md",
    "schemas/meal_analysis.schema.json",
    "application/ports/nutrition_gateway.py",
    "checks/minischema.py",
    "checks/gate_architecture.py",
    "checks/gate_contract.py",
    "checks/gate_acceptance.py",
    "checks/gate_offline.py",
    "checks/gate_seal.py",
    "run_gates.py",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for rel in PROTECTED:
        p = ROOT / rel
        out[rel] = digest(p) if p.exists() else "MISSING"
    return out


def stored() -> Dict[str, str]:
    if not SEAL_FILE.exists():
        return {}
    out: Dict[str, str] = {}
    for line in SEAL_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sha, _, rel = line.partition("  ")
        out[rel.strip()] = sha.strip()
    return out


def write_seal() -> None:
    lines = ["# 受保護檔案的封印。要改規則請人類決定，改完跑 python3 checks/seal.py",
             "# 並在 SPEC.md 的變更紀錄留一列，說明改了什麼、為什麼。"]
    for rel, sha in current().items():
        lines.append(f"{sha}  {rel}")
    SEAL_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> List[str]:
    problems: List[str] = []
    want = stored()
    if not want:
        problems.append("找不到封印檔 checks/protected.sha256——先跑 python3 checks/seal.py")
        return problems

    have = current()
    for rel, sha in want.items():
        actual = have.get(rel)
        if actual is None:
            continue
        if actual == "MISSING":
            problems.append(f"受保護的檔案被刪掉了：{rel}")
        elif actual != sha:
            problems.append(f"受保護的檔案被改了：{rel}")
    for rel in have:
        if rel not in want:
            problems.append(f"封印檔沒有涵蓋 {rel}——跑 python3 checks/seal.py 補上")
    return problems


HINT = ("如果這是你自己有意識改的：跑 python3 checks/seal.py 重新封印，"
        "並在 SPEC.md 變更紀錄留一列。如果不是你改的——那就是 AI 為了讓紅燈消失動了規則，"
        "把它還原（git checkout <檔案>），然後回去修產品。")

if __name__ == "__main__":
    found = run()
    if found:
        print("閘門 ⑤ 規則可控：✗")
        for line in found:
            print("   ", line)
        print("   提示：", HINT)
        raise SystemExit(1)
    print("閘門 ⑤ 規則可控：✓")
