"""插座規格（Port）。

★ 這個檔案是受保護的，不要改。它是「可控」的支點：
  - 上面（use case）只認識這個介面，不認識任何一家廠牌
  - 下面（adapter / fake）照這個介面各做一個插頭，可以隨時互換

刻意不寫的東西（抽象洩漏檢查清單）：
  ✗ temperature / max_tokens / model="gpt-..."   ← 某一家的概念
  ✗ api_key / base_url                          ← 某一家的設定
  ✗ prompt                                       ← 那是插頭內部的事
只要上面任何一個出現在這裡，換第二家的時候就會發現插座只有那一家插得進去。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.entities import MealAnalysis


@runtime_checkable
class NutritionGateway(Protocol):
    """把一張餐點照片，變成一份符合契約的結構化結果。

    實作方必須負責：
      1. 回傳的 MealAnalysis 一定通過 schemas/meal_analysis.schema.json
      2. 不是餐點時，`is_food=False` 並附上 `rejected_reason`
         （**不要在這裡拋錯**——「要不要拒絕」是做事流程的判斷，不是插頭的判斷）
      3. 看不清楚時降低 `confidence` 並填 `limitations`，不要硬掰數字
    """

    def estimate(self, image: bytes) -> MealAnalysis:
        ...
