"""做事流程：分析一張餐點照片。

★★★ 上機 ① 要填的就是這個檔案。★★★

規矩（AGENTS.md §1）：
  - 業務判斷寫在這裡，不要寫在 entrypoints/，也不要寫在 adapter/
  - 這一層不 import 任何外部套件（不 import requests / openai / …）
  - 需要外部能力就用插座（NutritionGateway），不要直接呼叫

驗收（SPEC.md）：
  AC-1  不是餐點 → 拋 NotFoodError（訊息用模型給的 rejected_reason）
  AC-2  只拍到局部 → confidence < 0.6 且 limitations 非空（由插頭負責，這裡不動它）
  AC-3  同一輸入連續 3 次 → 結果完全相同
  AC-4  數值型別與範圍正確
"""
from __future__ import annotations

from application.ports.nutrition_gateway import NutritionGateway
from domain.entities import MealAnalysis
from domain.exceptions import ImageTooLargeError, NotFoodError

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB：在呼叫 AI 之前就擋＝零成本快速失敗


class AnalyzeMeal:
    """把一張照片變成一份可信的營養估算，或明確地拒絕它。"""

    def __init__(self, gateway: NutritionGateway) -> None:
        self._gateway = gateway

    def execute(self, image: bytes) -> MealAnalysis:
        # ─────────────────────────────────────────────────────────────
        # TODO（上機 ①）
        #
        # 把下面三步寫出來。可以自己寫，也可以叫 AI 寫——
        # 但寫完一定要跑 `python3 run_gates.py`，五個閘門都要綠。
        #
        #   1. 影像超過 MAX_IMAGE_BYTES → raise ImageTooLargeError
        #      （在呼叫插座「之前」，這樣不會浪費一次 AI 呼叫）
        #   2. result = self._gateway.estimate(image)
        #   3. 如果 result.is_food 是 False → raise NotFoodError(...)
        #      訊息用 result.rejected_reason（沒有的話用預設）
        #      → 這一步就是 AC-1，也是「不落地、不算成功」的實體閘門
        #   4. 回傳 result
        #
        # 提示：不要在這裡「修正」confidence 或 limitations。
        #      那是插頭該誠實回報的東西，這一層只做判斷與拒絕。
        # ─────────────────────────────────────────────────────────────
        raise NotImplementedError(
            "上機 ① 要實作這個方法。步驟見上方 TODO 與 SPEC.md 的 AC-1。"
        )
