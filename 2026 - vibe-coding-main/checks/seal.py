"""重新封印受保護檔案。

**這是人類的指令，不是 AI 的。**

什麼時候該跑：
  你自己決定要改規則（改了 SPEC.md 的驗收、改了 schema 的欄位、
  改了架構閘門的 FORBIDDEN 清單…），改完之後跑這一支，讓封印跟上。

什麼時候不該跑：
  閘門紅了、你不知道為什麼、就想讓它變綠——那是在關掉安全網。
  先看紅燈訊息說哪個檔案被改了，用 git diff 看改了什麼。

用法：
    python3 checks/seal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from checks.gate_seal import PROTECTED, SEAL_FILE, current, write_seal  # noqa: E402

if __name__ == "__main__":
    before = SEAL_FILE.exists()
    write_seal()
    print(f"已封印 {len(PROTECTED)} 個受保護檔案 → {SEAL_FILE.name}")
    if before:
        print("提醒：記得在 SPEC.md 的「變更紀錄」加一列，寫下改了什麼、為什麼。")
    for rel, sha in current().items():
        mark = "  (檔案不存在)" if sha == "MISSING" else ""
        print(f"  {sha[:12]}…  {rel}{mark}")
