# 給 AI 的工地規矩

> 這份檔案的每一條都**可以當場查證**。
> 如果一條規則沒辦法用「指著某個檔案問：這樣算不算違反」得到明確答案，它就不該寫在這裡。
>
> 驗證方式：`python3 run_gates.py`

---

## 0. 最重要的一條

**不准修改下列檔案。** 它們是這個專案的規則本身，不是實作細節：

```
AGENTS.md
CLAUDE.md
SPEC.md
schemas/
checks/
run_gates.py
application/ports/
```

如果你認為某一條規則需要改，**先停下來，用文字說明為什麼，讓人類決定**。
擅自修改會被 `checks/gate_seal.py` 當場抓到。

> 這條規則存在的原因：AI 收到的目標是「讓檢查通過」，不是「讓產品正確」。
> 最快讓檢查通過的方式永遠是刪掉檢查。

---

## 1. 東西該放哪裡（樓層規則）

```
entrypoints/     啟動器。把東西接起來，不含任何判斷
adapter/         外牆：真的外部服務實作（呼叫 AI 服務、資料庫、HTTP）
infrastructure/  水電：設定、假實作（fake）
──────────────── 以上：可以重寫、可以砍掉重來
application/     辦公室：做事流程（use_cases）＋ 插座規格（ports）
domain/          地基：規矩、資料形狀、領域錯誤
──────────────── 以上：是資產。要改先問人
```

**依賴方向只能往下（往內）。** 樓上可以靠樓下，樓下不能靠樓上。

具體來說：

- 新的做事流程**只能**寫在 `application/use_cases/`，一個流程一個檔案。
- `domain/` 與 `application/` **不得 import**：
  `requests` / `httpx` / `urllib` / `openai` / `anthropic` / `google` /
  `boto3` / `sqlalchemy` / `fastapi` / `flask` / `django` /
  以及 `adapter` / `infrastructure` / `entrypoints`。
- `domain/` 額外**不得 import** `application`。
- 需要外部能力時：在 `application/ports/` 定義 `Protocol`，實作放 `adapter/`。
- `entrypoints/` 裡不得出現業務判斷的 `if`。

> 查證：`python3 checks/gate_architecture.py`

---

## 2. 回傳的東西長什麼樣（形狀規則）

- 唯一的事實來源是 `schemas/meal_analysis.schema.json`。
- **不准新增欄位、不准改欄位名稱、不准改型別。**
- 回傳值一律先過 `domain.entities.MealAnalysis`，由它負責 `to_dict()`。
- 算不出來的數字要標 `null` 或放進 `limitations`，**絕對不要編一個數字**。

> 查證：`python3 checks/gate_contract.py`

---

## 3. 什麼叫做對了（驗收規則）

`SPEC.md` 的 `AC-1` ～ `AC-4` 是這個功能的驗收標準。

- 每一條 AC 都必須有一個對應的斷言。
- **不准為了通過而放寬斷言、不准 mock 掉正要驗的東西、不准硬編碼樣例答案。**
- 閘門過不了就修產品，不是修閘門。

> 查證：`python3 checks/gate_acceptance.py`

---

## 4. 不准增加執行門檻（依賴規則）

- **不准 `pip install` 任何東西。** 只用 Python 內建函式庫。
- 不准要求 API key、不准要求網路、不准要求資料庫、不准要求 Docker。
- 真的要呼叫外部服務時：寫在 `adapter/`，並且**同時**確保
  `infrastructure/fake_nutrition.py` 這條路徑仍然能單獨跑完整流程。

> 理由：一個需要安裝才能跑的閘門，等於沒有閘門——沒有人會跑它。
> 查證：`python3 checks/gate_offline.py`

---

## 5. 改動要小（diff 規則）

- 優先改既有檔案，不要另開新檔案。
- 一次改動只做一件事。
- 不要順手重排 import、不要順手改格式、不要順手改無關的檔案。
- 如果你判斷需要動到「受保護檔案」以外的多個檔案，**先列出清單讓人類確認**。

---

## 6. 寫給人看的規則

- 註解與文件用**繁體中文**（台灣用語）。
- 變數與函式名用英文。
- 每個 use case 的 docstring 要寫「這個流程在完成什麼任務」，不是重複函式名。

---

## 這份檔案怎麼用

貼給 AI 的時候，連同這一句：

```
先讀 AGENTS.md，照它的規則做。做完跑 python3 run_gates.py，
把計分板貼回來給我看。如果有紅燈，修產品，不要修檢查。
```
