"""重新封印受保護檔案與已發布的數字。

**這是人類的指令，不是 AI 的。**

什麼時候該跑：
  你自己決定要改規則（改了契約、改了閘門、改了 AGENTS.md），
  或者換了新一期的資料、有意識地更新了會被引用的數字。改完跑這一支。

什麼時候不該跑：
  閘門紅了、你不知道為什麼、就想讓它變綠——那是在關掉安全網。
  先看紅燈訊息說哪個檔案或哪個數字變了，用 git diff 看改了什麼。

用法：
    python3 checks/seal.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from checks.gate_seal import (FIG_FILE, SEAL_FILE, current_figures,  # noqa: E402
                              current_hashes, write_seal)

if __name__ == '__main__':
    again = SEAL_FILE.exists()
    before = {}
    if again:
        import json
        if FIG_FILE.exists():
            before = json.loads(FIG_FILE.read_text(encoding='utf-8'))
    write_seal()
    files = current_hashes()
    print(f'已封印 {len(files)} 個規則檔案 → {SEAL_FILE.name}')
    for rel, sha in files.items():
        print(f'  {sha[:12]}…  {rel}')
    print(f'\n已封印 {len(current_figures())} 個發布數字 → {FIG_FILE.name}')
    for ref, rec in current_figures().items():
        old = before.get(ref, {}).get('value')
        mark = '' if not again or old == rec['value'] else f'   ← 原本 {old}'
        print(f'  {rec["label"]}：{rec["value"]}{mark}')
    if again:
        print('\n提醒：在提交訊息裡寫清楚改了什麼、為什麼。'
              '封印本身不是紀錄，說明才是。')
