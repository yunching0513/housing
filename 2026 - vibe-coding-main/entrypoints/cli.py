"""啟動器：把東西接起來，走一遍完整流程。

規矩（AGENTS.md §1）：這裡不含任何業務判斷的 if。
它只做三件事：選一個插頭、餵一個樣本、把結果印出來。

用法：
    python3 -m entrypoints.cli                # 三個樣本都跑一遍
    python3 -m entrypoints.cli --case food
    python3 -m entrypoints.cli --case cropped
    python3 -m entrypoints.cli --case notfood
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from application.use_cases.analyze_meal import AnalyzeMeal  # noqa: E402
from domain.exceptions import DomainError  # noqa: E402
from infrastructure.fake_nutrition import (SAMPLE_CROPPED, SAMPLE_FOOD,  # noqa: E402
                                           SAMPLE_NOT_FOOD,
                                           FakeNutritionGateway)

CASES = {
    "food": ("正常餐點", SAMPLE_FOOD),
    "cropped": ("只拍到局部", SAMPLE_CROPPED),
    "notfood": ("不是餐點（例如一張汽車照片）", SAMPLE_NOT_FOOD),
}


def build_use_case() -> AnalyzeMeal:
    """上機 ② 之後，這裡是「換插頭」的唯一一個地方。

    要換成真的 AI 服務，就只改這一行：
        return AnalyzeMeal(OpenAINutritionGateway())
    牆（domain / application）完全不用動——這就是留插座的價值。
    """
    return AnalyzeMeal(FakeNutritionGateway())


def run_case(key: str) -> None:
    label, sample = CASES[key]
    print(f"── {key}：{label} ".ljust(60, "─"))
    try:
        result = build_use_case().execute(sample)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    except DomainError as exc:
        # 領域錯誤在這裡才被翻譯成「使用者看到的樣子」。
        # 如果這是 Web API，這裡就是 4xx 的映射點。
        print(f"被拒絕（{type(exc).__name__}）：{exc}")
    except NotImplementedError as exc:
        print(f"還沒實作：{exc}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="餐點分析：走一遍完整流程（離線、免金鑰）")
    ap.add_argument("--case", choices=sorted(CASES), help="只跑其中一個樣本")
    args = ap.parse_args()
    for key in ([args.case] if args.case else sorted(CASES)):
        run_case(key)


if __name__ == "__main__":
    main()
