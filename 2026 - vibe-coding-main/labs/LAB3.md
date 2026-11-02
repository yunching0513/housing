# 上機 ③　畫施工圖：讓「改需求」變成一張比對表

> 30 分鐘（要壓時間就三段各 8 分鐘）
> 前提：上機 ①② 都是 5 / 5。這一段**不需要跑任何服務**，只需要 Git。

---

## 前 10 分鐘：先把現在的狀態存成基準點

```bash
cd starter-kit
git init                      # 如果還沒有
git add -A
git commit -m "baseline: 5/5 gates green"
```

然後打開 `SPEC.md`，只讀三個地方：

1. **入口**——一行，說清楚呼叫的形狀
2. **回傳長什麼樣**——是**樣本 JSON**，不是欄位描述
3. **驗收標準**——四條，每一條都可以打勾

### 一個問題：為什麼是樣本 JSON，不是欄位描述？

因為這是真的踩過的坑。兩組人（或兩個 AI）各拿一份「文字說明」平行開工：

```
這一邊叫 access_token          那一邊叫 token
這一邊叫 fields                那一邊叫 field_schema
這一邊是「包起來的」            那一邊是「攤平的」

兩邊自己檢查都合格 ✓✓          接起來直接壞 ✗
```

**兩份都「合理」，合起來就是壞的。合理不等於一致。**
不要說「大概這麼寬」，直接畫一張標好尺寸的圖。

---

## 中 10 分鐘：只改施工圖一行，然後重新生成

在 `SPEC.md` 裡做**一個**改動。二選一：

### 選項 A（簡單）：多要一個欄位

```diff
  ## 回傳長什麼樣
  {
    "calories_kcal": 520,
    "protein_g": 28.5,
+   "carbs_g": 62.0,
    "is_food": true,
    ...
  }
```

### 選項 B（推薦，會看到更有趣的 diff）：改一條驗收

```diff
- | **AC-2** | 只拍到局部的照片 → `confidence < 0.6` 且 `limitations` 不是空的 |
+ | **AC-2** | 只拍到局部的照片 → `confidence < 0.6`、`limitations` 不是空的，
+             **且 `calories_kcal` 必須為 0**（看不清楚就不要給數字） |
```

改完之後**先跑封印閘門**：

```bash
python3 run_gates.py
```

**⑤ 規則可控會紅**——因為 `SPEC.md` 是受保護檔案。這是對的：
**規格改動必須是人類的明確決定。** 所以你要自己確認一次：

```bash
python3 checks/seal.py          # 我確定要改這條規格
```

並在 `SPEC.md` 最下面的「變更紀錄」加一列：

| 版本 | 改了什麼 | 為什麼 |
|---|---|---|
| v2 | AC-2 加上「看不清楚時熱量必須為 0」 | 不要在看不清楚的情況下給一個假數字 |

然後叫 AI：

```
SPEC.md 改了（見 git diff SPEC.md）。請照新版 spec 調整實作。
規則：minimal diff——只改必要的檔案與行數，不要順手改別的。
做完跑 python3 run_gates.py，五個都要綠。
```

---

## 後 10 分鐘：看那張比對表（本上機的重點）

```bash
git diff --stat
git diff
```

### 三個問題

**Q1：它動的範圍符合你的預期嗎？**

選項 B 的合理範圍是：

```
應該動：schemas/…json（如果選 A）、infrastructure/fake_nutrition.py、
        checks/gate_acceptance.py（新增 AC-2 的斷言）
不該動：application/ports/、domain/entities.py 的欄位、
        其他 use case、README、任何無關的格式
```

如果它順手改了不相干的檔案 → 那就是 `AGENTS.md §5「改動要小」` 沒有被遵守。
把 `git diff --stat` 貼給它，問「這幾個檔案為什麼要動」。

**Q2：如果沒有 `SPEC.md`，你要怎麼跟它說「只改這裡，其他不要碰」？**

你會發現你在對話裡**重新描述了一次整個功能**。而且下次還要再描述一次。

**Q3：這次改動要交給人審，該看程式碼還是看施工圖？**

看 `git diff SPEC.md`——**3 行**。
程式碼的 diff 只需要確認一件事：**有沒有超出 spec 的範圍**。

> ### 這就是 spec 驅動最大的槓桿
> **review 的對象從「程式碼」變成「意圖」。**
>
> 有施工圖，改動是一張比對表。
> 沒有施工圖，每次都要重講一遍整棟樓。

---

## 加分題：連續生成兩次，比較 diff

```bash
git add -A && git commit -m "spec v2"
# 把實作檔案刪掉，讓 AI 完全從 SPEC.md 重新生成
rm application/use_cases/analyze_meal.py
# 叫 AI：照 SPEC.md 與 AGENTS.md 重新生成 application/use_cases/analyze_meal.py
git diff
```

**如果 spec 寫得夠緊，重生出來的東西應該幾乎一樣。**
diff 很大 → 代表 spec 還有解讀空間，回去把那個空間補掉。

這是「可控」最硬的測試：**同一份輸入，兩次輸出要一致。**

---

## 你剛剛裝好的可控開關

```
② 形狀可控   回傳的欄位、型別、範圍被釘死          （schema）
③ 對錯可控   「什麼叫做對了」在生成之前就定義好      （Acceptance Criteria）
```

而且順帶發現：**⑤ 規則可控也保護了 SPEC.md**——
規格不是 AI 可以順手改的東西，改它要留紀錄。

---

## 填完計分表

回到 `SCORECARD.md`，把上機 ③ 與最後的「全班一致性」填完。

> 下一步（本課只帶過）：把 `SPEC.md` 那四條 AC 收成一本「考古題庫」（golden dataset），
> 每改一次 AI 的指令就整本重考一次，考不過不准上線。
> **你今天多寫一句可以打勾的驗收，之後就少一個上線後才爆掉的坑。**
