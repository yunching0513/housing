# 施工圖：餐點照片分析

> 這份檔案就是原始碼。程式碼是照著它蓋出來的結果。
> 要改行為 → 改這份 → 重新生成 → 看 diff。**不要直接改程式碼繞過這裡。**

---

## 入口

```
AnalyzeMeal(gateway).execute(image: bytes) -> MealAnalysis
```

- `gateway` 是插座（`application/ports/nutrition_gateway.py`）。
  真的插頭放 `adapter/`，假的插頭放 `infrastructure/`。
- 這個功能**不對外開 HTTP**。要走一遍流程用 `python3 -m entrypoints.cli`。

---

## 回傳長什麼樣（樣本 JSON，不是欄位描述）

正常情況：

```json
{
  "calories_kcal": 520,
  "protein_g": 28.5,
  "is_food": true,
  "confidence": 0.88,
  "limitations": [],
  "rejected_reason": null
}
```

拍到的東西看不清楚時：

```json
{
  "calories_kcal": 520,
  "protein_g": 28.5,
  "is_food": true,
  "confidence": 0.55,
  "limitations": ["影像只拍到局部，湯碗內容物未列入估算"],
  "rejected_reason": null
}
```

不是餐點時（這一份**不會被回傳**，會變成錯誤，見 AC-1）：

```json
{
  "calories_kcal": 0,
  "protein_g": 0.0,
  "is_food": false,
  "confidence": 0.95,
  "limitations": [],
  "rejected_reason": "看起來不是餐點，請重新拍攝"
}
```

**欄位的權威定義在 `schemas/meal_analysis.schema.json`。**
上面的樣本必須通過那份 schema；schema 沒寫的欄位不准出現。

---

## 驗收標準（每一條都要能變成一行斷言）

| # | 驗收 | 怎麼判斷過了 |
|---|---|---|
| **AC-1** | 不是餐點的照片 → **拋出 `NotFoodError`**，不回傳結果 | `pytest.raises` / `try-except`；並且錯誤訊息要用得上模型給的 `rejected_reason` |
| **AC-2** | 只拍到局部的照片 → `confidence < 0.6` **且** `limitations` 不是空的 | 兩個條件都要成立，缺一不算過 |
| **AC-3** | 同一張照片連續分析 3 次 → 三次結果**完全相同** | 三次 `to_dict()` 逐欄位相等 |
| **AC-4** | `calories_kcal` 必為整數且 `0 ≤ x ≤ 5000`；`confidence` 必為 `0 ≤ x ≤ 1` | 型別 ＋ 範圍都查 |

**AC-3 為什麼重要**：這一條在測「可控」本身。
真的 AI 服務同一張圖跑三次答案可能不同——所以確定性的假插頭是**測試的唯一合法對象**，
而「真的準不準」要另外用一批貼近真實的樣本去量（業界叫 golden dataset，本課只帶過）。

---

## 明確的非目標

- 不做 HTTP API、不做前端、不做資料庫。
- 不做使用者登入。
- 不呼叫真的 AI 服務（`adapter/` 只寫到「呼叫的形狀」為止，不放金鑰）。
- 不處理影片、不處理多張照片。

> 寫下非目標是可控的一部分。沒有寫，AI 就會自己加。

---

## 變更紀錄

| 版本 | 改了什麼 | 為什麼 |
|---|---|---|
| v1 | 初版 | — |

> 上機 ③ 會在這裡加一列。**改 SPEC 要留紀錄，這樣 diff 才有上下文。**
