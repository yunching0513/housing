"""地基：回傳的東西長什麼樣。

規矩：這一層不 import 任何外部套件（連 HTTP、連 AI 服務的 SDK 都不行）。
理由：地基被外面的東西污染之後，就沒辦法在 CLI / 排程 / 測試裡重用同一段邏輯。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class MealAnalysis:
    """一次餐點分析的結果。

    欄位的權威定義在 schemas/meal_analysis.schema.json。
    這裡是同一份契約的 Python 形狀——兩邊要一致，由契約閘門把關。
    """

    calories_kcal: int
    protein_g: float
    is_food: bool
    confidence: float
    limitations: Tuple[str, ...] = ()
    rejected_reason: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        """轉成契約規定的形狀。欄位順序與 schema 一致，方便人眼比對。"""
        return {
            "calories_kcal": int(self.calories_kcal),
            "protein_g": float(self.protein_g),
            "is_food": bool(self.is_food),
            "confidence": float(self.confidence),
            "limitations": list(self.limitations),
            "rejected_reason": self.rejected_reason,
        }

    @property
    def is_uncertain(self) -> bool:
        """信心不足的判斷收斂在這裡，不要讓每個呼叫端各寫一份 0.6。

        （這是 LESSONS.md L32 的教訓：同一個特例被三處各實作一次，
        其中一處漏改就會悄悄壞掉。）
        """
        return self.confidence < UNCERTAIN_THRESHOLD


# 門檻是領域規則，不是魔術數字。要改就改這裡，全站一起變。
UNCERTAIN_THRESHOLD = 0.6
