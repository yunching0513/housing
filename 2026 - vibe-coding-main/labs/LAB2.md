# 上機 ②　留插座：讓「換掉外部服務」變成改一個檔案

> 30 分鐘（要壓時間就三段各 8 分鐘）
> 前提：上機 ① 已經跑到 5 / 5。

---

## 前 10 分鐘：先讀插座規格，再判斷它為什麼這樣寫

打開 `application/ports/nutrition_gateway.py`。它只有一個方法：

```python
class NutritionGateway(Protocol):
    def estimate(self, image: bytes) -> MealAnalysis: ...
```

### 三個問題（自己先想，再看答案）

**Q1：為什麼裡面沒有 `temperature`、`model="gpt-…"`、`api_key`？**

因為那些是**某一家廠牌的概念**。一旦寫進插座，換第二家就會發現插座只有那一家插得進去。
這叫**抽象洩漏**——插座長得像某一個插頭。

**Q2：為什麼「不是餐點」的時候，插頭回傳 `is_food=False` 而不是直接拋錯？**

因為「要不要拒絕」是**做事流程的判斷**，不是插頭的判斷。
今天你拒絕，明天可能想「先存起來再問使用者」——那時候你不會想改每一個插頭。
插頭只負責**誠實回報**，判斷收在 use case 一個地方。

**Q3：為什麼 `confidence` 和 `limitations` 是必填欄位？**

因為**能力邊界要寫在型別裡，不要寫在 prompt 裡**。
寫在 prompt 會漂移、會被繞過、換模型就失效；寫在型別裡，驗證期就擋下來。

### 現場自我檢查：抽象洩漏清單

拿你自己專案的介面對一次：

```
□ 有沒有出現 temperature / max_tokens / top_p？
□ 有沒有出現 model="gpt-..." 或任何廠牌型號？
□ 有沒有出現 api_key / base_url / organization？
□ 有沒有把 prompt 當參數傳進來？
□ 回傳的是「該廠牌的 response 物件」，還是你自己的資料形狀？
```

勾到任何一個 → 那不是插座，那是那一家的轉接頭。

---

## 中 10 分鐘：讓 AI 生一個「真的插頭」

`adapter/` 現在是空的。讓 AI 生一個真的實作——**但不准放金鑰、不准讓離線那條路壞掉**。

貼這一段：

```
先讀 AGENTS.md。在 adapter/ 生一個 openai_nutrition.py，
實作 application/ports/nutrition_gateway.py 的 NutritionGateway 插座。

限制（AGENTS.md §4）：
· 不准 pip install。用 urllib.request 就好（只要寫出呼叫的形狀，不用真的通）。
· 金鑰只從環境變數 OPENAI_API_KEY 讀，預設空字串，沒有金鑰就 raise 一個清楚的錯誤。
· 不准修改 application/ports/ 和 infrastructure/ 的任何檔案。
· 回傳一定要是 domain.entities.MealAnalysis，並且通過
  schemas/meal_analysis.schema.json。

做完跑 python3 run_gates.py，五個閘門都要還是綠的。
```

跑完之後檢查兩件事：

```bash
python3 run_gates.py                       # 應該還是 5 / 5
python3 -m entrypoints.cli                 # 應該還是三個樣本都跑得完（用假插頭）
```

> **重點在這裡**：你剛剛加了一個會連外網的檔案，
> 但 `run_gates.py` 還是 5 / 5、`cli` 還是不需要金鑰。
> 這就是「依賴可控」——新增能力不會提高別人的執行門檻。

---

## 後 10 分鐘：驗證「換插頭時牆不用動」

打開 `entrypoints/cli.py`，找到這個函式：

```python
def build_use_case() -> AnalyzeMeal:
    return AnalyzeMeal(FakeNutritionGateway())
```

把它改成真的插頭（**只改這一行**）：

```python
def build_use_case() -> AnalyzeMeal:
    from adapter.openai_nutrition import OpenAINutritionGateway
    return AnalyzeMeal(OpenAINutritionGateway())
```

跑 `python3 -m entrypoints.cli --case food`。
沒有金鑰的話它會拋出你剛剛請 AI 寫的那個「清楚的錯誤」——**這是對的**。

然後**改回 `FakeNutritionGateway()`**，再跑一次 → 又通了。

### 這一段要你數的數字

```
換掉整個 AI 服務供應商，你動了幾個檔案？
  · 新增：adapter/openai_nutrition.py     1 個
  · 修改：entrypoints/cli.py 的 1 行      1 個
  · domain / application 動了幾行？        0 行  ←★
```

**這個 0 就是「你有沒有架構」的答案。** 不用看架構圖，不用聽任何人說明。

---

## 一個一定要講清楚的限制

假插頭是**照規則答題**的，所以：

| 假插頭能保證 | 假插頭保證不了 |
|---|---|
| 跑得動（流程接得起來） | 判得準（模型的語意判斷對不對） |
| 每次結果一樣（可以寫檢查） | 真實輸入的邊界情況 |
| 零成本、零金鑰、離線 | 換模型後行為有沒有漂掉 |

**真實事故**：一個判斷「是不是緊急狀況」的功能，假插頭測全部通過，
換真的 AI 一測，「我要請病假」被判成「緊急事件」——它看到「病」這個字就緊張了。

> 假的保證「跑得動」，真的保證「判得準」。**兩件事不能互相取代。**
> 「那要怎麼系統性地驗判得準？」→ 需要一本可重跑的考古題庫（golden dataset）：
> 收 10 題（5 常見 ＋ 3 邊界 ＋ 2 歷史事故），每改一次指令就整本重考。本課只帶過。

---

## 你剛剛裝好的可控開關

```
④ 依賴可控   沒有金鑰、沒有網路、沒有安裝，整套跑得起來   （技術名：Ports & Adapters）
```

---

## 填一下計分表

回到 `SCORECARD.md`，把上機 ② 那一段填完。
