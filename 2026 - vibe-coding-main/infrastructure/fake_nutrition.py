"""假電器（Fake）。不連網、不用金鑰、不花錢、答案固定。

★ 為什麼「答案固定」這件事這麼重要：
  真的 AI 服務同一張圖跑三次，答案可能不一樣。
  那樣就沒辦法寫「這樣算對、那樣算錯」的檢查——因為對錯本身在飄。
  所以：**確定性的假插頭是自動檢查的唯一合法對象。**

★ 這個假電器測不出什麼（很重要，別誤會它的能力）：
  它是照規則答題的，不會犯真 AI 那種「看到『病』就緊張」的語意誤判。
  「判得準不準」必須換真的服務、用一批貼近真實的樣本量一次（golden dataset，本課只帶過）。

規則（刻意設計成可預測，讓全班拿到同一組答案）：
  · 位元組長度是奇數      → 不是餐點
  · 位元組長度 < 32       → 只拍到局部（confidence 0.55、limitations 非空）
  · 其他                  → 正常餐點（confidence 0.88）
"""
from __future__ import annotations

from domain.entities import MealAnalysis

CROPPED_THRESHOLD_BYTES = 32


class FakeNutritionGateway:
    """符合 NutritionGateway 插座規格的假插頭。"""

    def estimate(self, image: bytes) -> MealAnalysis:
        if len(image) % 2 == 1:
            # 不是餐點：這裡「不拋錯」。要不要拒絕是做事流程的判斷（AC-1）。
            return MealAnalysis(
                calories_kcal=0,
                protein_g=0.0,
                is_food=False,
                confidence=0.95,
                limitations=(),
                rejected_reason="看起來不是餐點，請重新拍攝您的餐點",
            )

        if len(image) < CROPPED_THRESHOLD_BYTES:
            # 只拍到局部：誠實降低信心並招認看不到的部分（AC-2）
            return MealAnalysis(
                calories_kcal=520,
                protein_g=28.5,
                is_food=True,
                confidence=0.55,
                limitations=("影像只拍到局部，湯碗內容物未列入估算",),
                rejected_reason=None,
            )

        return MealAnalysis(
            calories_kcal=520,
            protein_g=28.5,
            is_food=True,
            confidence=0.88,
            limitations=(),
            rejected_reason=None,
        )


# ── 三個固定樣本：全班的檢查都用這三個，結果才可比較 ──────────────────
SAMPLE_FOOD = b"x" * 64        # 偶數且 >= 32 → 正常餐點
SAMPLE_CROPPED = b"x" * 16     # 偶數且 < 32  → 只拍到局部
SAMPLE_NOT_FOOD = b"x" * 65    # 奇數         → 不是餐點（例如一張汽車照片）
