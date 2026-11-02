"""閘門 ③｜對錯可控：行為有沒有符合 SPEC.md 的驗收標準。

一條 AC ＝ 一個斷言。SPEC.md 寫得出來，這裡就查得到。
如果哪一條 AC 你沒辦法在這裡寫成斷言，那條 AC 就寫得不夠好，回去改 SPEC。

怎麼自己跑：  python3 checks/gate_acceptance.py
"""
from __future__ import annotations

from typing import List

from application.use_cases.analyze_meal import MAX_IMAGE_BYTES, AnalyzeMeal
from domain.exceptions import ImageTooLargeError, NotFoodError
from infrastructure.fake_nutrition import (SAMPLE_CROPPED, SAMPLE_FOOD,
                                           SAMPLE_NOT_FOOD,
                                           FakeNutritionGateway)


def _uc() -> AnalyzeMeal:
    return AnalyzeMeal(FakeNutritionGateway())


def run() -> List[str]:
    problems: List[str] = []

    # ── AC-1：不是餐點 → 拋 NotFoodError，且訊息要用得上模型給的說明 ──
    try:
        _uc().execute(SAMPLE_NOT_FOOD)
        problems.append("AC-1 沒過：不是餐點的照片竟然回傳了結果（應該拋 NotFoodError）")
    except NotFoodError as exc:
        if not str(exc).strip():
            problems.append("AC-1 沒過：NotFoodError 沒有帶友善說明")
    except NotImplementedError:
        problems.append("AC-1 沒過：AnalyzeMeal.execute 還沒實作（這就是上機 ① 要做的）")
    except Exception as exc:
        problems.append(f"AC-1 沒過：拋出的是 {type(exc).__name__}，應該是 NotFoodError")

    # ── AC-2：只拍到局部 → confidence < 0.6 且 limitations 非空 ──
    try:
        result = _uc().execute(SAMPLE_CROPPED)
        if result.confidence >= 0.6:
            problems.append(f"AC-2 沒過：局部影像的 confidence 應該 < 0.6，實際 {result.confidence}")
        if not result.limitations:
            problems.append("AC-2 沒過：局部影像必須在 limitations 招認看不到的部分")
    except NotImplementedError:
        problems.append("AC-2 沒過：AnalyzeMeal.execute 還沒實作")
    except Exception as exc:
        problems.append(f"AC-2 沒過：{type(exc).__name__}: {exc}")

    # ── AC-3：同一輸入連續 3 次 → 結果完全相同（這一條在測「可控」本身）──
    try:
        runs = [_uc().execute(SAMPLE_FOOD).to_dict() for _ in range(3)]
        if not (runs[0] == runs[1] == runs[2]):
            problems.append("AC-3 沒過：同一張照片跑三次結果不一樣（不確定＝不可控）")
    except NotImplementedError:
        problems.append("AC-3 沒過：AnalyzeMeal.execute 還沒實作")
    except Exception as exc:
        problems.append(f"AC-3 沒過：{type(exc).__name__}: {exc}")

    # ── AC-4：型別與範圍 ──
    try:
        r = _uc().execute(SAMPLE_FOOD)
        if not isinstance(r.calories_kcal, int) or isinstance(r.calories_kcal, bool):
            problems.append("AC-4 沒過：calories_kcal 必須是整數")
        if not (0 <= r.calories_kcal <= 5000):
            problems.append(f"AC-4 沒過：calories_kcal 超出範圍（{r.calories_kcal}）")
        if not (0.0 <= r.confidence <= 1.0):
            problems.append(f"AC-4 沒過：confidence 超出 0～1（{r.confidence}）")
    except NotImplementedError:
        problems.append("AC-4 沒過：AnalyzeMeal.execute 還沒實作")
    except Exception as exc:
        problems.append(f"AC-4 沒過：{type(exc).__name__}: {exc}")

    # ── 額外：超大影像要在呼叫插座「之前」就被擋（零成本快速失敗）──
    try:
        _uc().execute(b"x" * (MAX_IMAGE_BYTES + 2))
        problems.append("額外沒過：超過上限的影像應該拋 ImageTooLargeError")
    except ImageTooLargeError:
        pass
    except NotImplementedError:
        pass  # 上一批已經回報過了，不重複洗版
    except Exception as exc:
        problems.append(f"額外沒過：超大影像拋出的是 {type(exc).__name__}，"
                        f"應該是 ImageTooLargeError")

    return problems


HINT = ("閘門過不了就修產品，不是修閘門。"
        "不准放寬斷言、不准 mock 掉正要驗的東西、不准硬編碼樣例答案。")

if __name__ == "__main__":
    found = run()
    if found:
        print("閘門 ③ 對錯可控：✗")
        for line in found:
            print("   ", line)
        print("   提示：", HINT)
        raise SystemExit(1)
    print("閘門 ③ 對錯可控：✓")
