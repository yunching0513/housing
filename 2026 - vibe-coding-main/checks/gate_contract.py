"""閘門 ②｜形狀可控：回傳的東西有沒有多欄位、少欄位、型別錯、超出範圍。

它在擋什麼：
  AI 很喜歡「順手多給一點」——多一個 notes、把 calories 改成 float、
  把 limitations 從陣列改成字串。每一個單獨看都很合理，合起來就是接不上。

★ 雙向驗證（缺一邊等於裝飾品）：
  正向：好的樣本一定要過   → 契約不會誤殺
  反向：已知壞的樣本一定要被擋 → 契約真的有牙齒

怎麼自己跑：  python3 checks/gate_contract.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from checks.minischema import SchemaError, validate

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "meal_analysis.schema.json"


def load_schema() -> Dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ── 正向：這些一定要過 ────────────────────────────────────────────────
GOOD: List[Dict[str, Any]] = [
    {"calories_kcal": 520, "protein_g": 28.5, "is_food": True,
     "confidence": 0.88, "limitations": [], "rejected_reason": None},
    {"calories_kcal": 520, "protein_g": 28.5, "is_food": True,
     "confidence": 0.55, "limitations": ["影像只拍到局部，湯碗內容物未列入估算"],
     "rejected_reason": None},
    {"calories_kcal": 0, "protein_g": 0.0, "is_food": False,
     "confidence": 0.95, "limitations": [], "rejected_reason": "看起來不是餐點"},
]

# ── 反向：這些一定要被擋（每一個都是真的踩過的形狀）──────────────────
BAD: List[Dict[str, Any]] = [
    ({"calories_kcal": 520.5, "protein_g": 28.5, "is_food": True,
      "confidence": 0.88, "limitations": []}, "熱量給了小數（整數欄位）"),
    ({"calories_kcal": 520, "protein_g": 28.5, "is_food": True,
      "confidence": 0.88, "limitations": [], "notes": "順手多給的欄位"},
     "多了契約沒定義的欄位"),
    ({"calories_kcal": 520, "protein_g": 28.5, "is_food": True,
      "confidence": 1.4, "limitations": []}, "信心超過 1"),
    ({"calories_kcal": 520, "protein_g": 28.5, "is_food": True,
      "confidence": 0.88, "limitations": "沒看清楚"}, "limitations 變成字串（該是陣列）"),
    ({"calories_kcal": 520, "protein_g": 28.5,
      "confidence": 0.88, "limitations": []}, "少了 is_food"),
    ({"calories_kcal": -10, "protein_g": 28.5, "is_food": True,
      "confidence": 0.88, "limitations": []}, "熱量是負數"),
]


def run() -> List[str]:
    problems: List[str] = []
    schema = load_schema()

    for i, sample in enumerate(GOOD):
        try:
            validate(sample, schema)
        except SchemaError as exc:
            problems.append(f"正向樣本 #{i} 被誤殺了（契約太嚴）：{exc}")

    for payload, why in BAD:
        try:
            validate(payload, schema)
        except SchemaError:
            continue
        problems.append(f"反向樣本沒被擋下來（契約沒有牙齒）：{why}")

    # 讓假插頭的實際輸出也走一次契約——契約與程式碼不能各說各話
    try:
        from infrastructure.fake_nutrition import (SAMPLE_CROPPED, SAMPLE_FOOD,
                                                   SAMPLE_NOT_FOOD,
                                                   FakeNutritionGateway)
    except Exception as exc:  # pragma: no cover - 結構被改壞時的保護
        problems.append(f"載入假插頭失敗：{exc}")
        return problems

    gw = FakeNutritionGateway()
    for name, sample in (("正常餐點", SAMPLE_FOOD), ("只拍到局部", SAMPLE_CROPPED),
                         ("不是餐點", SAMPLE_NOT_FOOD)):
        try:
            validate(gw.estimate(sample).to_dict(), schema)
        except SchemaError as exc:
            problems.append(f"假插頭的「{name}」輸出不符合契約：{exc}")
    return problems


HINT = "契約是唯一的事實來源。輸出不合就改輸出，不要改 schema。"

if __name__ == "__main__":
    found = run()
    if found:
        print("閘門 ② 形狀可控：✗")
        for line in found:
            print("   ", line)
        print("   提示：", HINT)
        raise SystemExit(1)
    print("閘門 ② 形狀可控：✓")
