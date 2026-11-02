# vibe-coding｜上機素材包：讓 AI 產生的結果可控

> 臺大計中 2026「從 Vibe Coding 到 Production Architecture」上午場
> Jeff 洪鼎鈞 · OG Tech 歐碁科技

---

## 下載（二選一）＋ 先做這三件事（3 分鐘）

```bash
# 方式 A：有 git（推薦，上機 ③ 會用到 git）
git clone https://github.com/jeffhong824/vibe-coding.git
cd vibe-coding

# 方式 B：沒有 git
# 到 github.com/jeffhong824/vibe-coding → 綠色 Code 按鈕 → Download ZIP → 解壓

# 1. 確認 Python 跑得動（3.9 以上都可以）
python3 --version

# 2. 跑一次閘門，看你的起點
python3 run_gates.py

# 3. 你應該看到 3 / 5。全班都要是 3 / 5。
```

**不需要 pip install，不需要 Docker，不需要任何 API key，不需要網路。**
用到的全部是 Python 內建函式庫。

如果你的結果不是 `3 / 5`，先舉手——**起點不同，後面的結果就沒辦法比較**。

---

## 這個資料夾在解決什麼問題

一間教室 40 個人，對 AI 說同一句話「幫我做一個上傳餐點照片、回傳熱量的功能」，
會得到 **40 種不同的東西**：檔案放在不同地方、回傳的欄位名稱不一樣、
錯誤處理方式不一樣、有人裝了一堆套件有人沒有。

不是因為 AI 不穩定，是因為**你沒有給它任何約束**。

這個資料夾就是那些約束。它讓你和你旁邊的人，用同一句話得到**結構上一樣**的結果。

```
可控 ＝ 起點相同 ＋ 規則可讀 ＋ 骨架已定 ＋ 閘門會擋 ＋ 形狀被釘死 ＋ 對錯先定義
        └ 這個資料夾 ┘ └AGENTS.md┘ └資料夾結構┘ └run_gates┘ └ schema ┘ └ SPEC 的 AC ┘
```

---

## 五個「可控開關」＝ 五道閘門

`python3 run_gates.py` 會一次跑完五道閘門，印出一張計分板：

| # | 開關 | 閘門 | 它擋掉什麼 |
|---|---|---|---|
| ① | **位置可控** | 架構閘門 | AI 把邏輯寫錯樓層、或在核心層偷接外部服務 |
| ② | **形狀可控** | 契約閘門 | 回傳多欄位、少欄位、型別錯、超出範圍 |
| ③ | **對錯可控** | 驗收閘門 | 行為跟 SPEC.md 的驗收標準不符 |
| ④ | **依賴可控** | 離線閘門 | 沒有金鑰／沒有網路就跑不起來 |
| ⑤ | **規則可控** | 封印閘門 | **AI 為了讓閘門變綠，去改規則本身** |

第 ⑤ 道是最容易被忽略、也最重要的一道。
AI 收到的目標是「讓檢查通過」，不是「讓產品正確」——
所以它會很自然地去刪掉那條擋住它的檢查。封印閘門就是在防這件事。

---

## 資料夾長什麼樣

```
starter-kit/
├── AGENTS.md ─────────── ★ 給 AI 的鐵則。每一條都可以當場查證，不是精神喊話
├── CLAUDE.md ─────────── Claude Code 的橋接（一行 import AGENTS.md）
├── SPEC.md ───────────── ★ 施工圖：一個入口 ＋ 回傳樣本 JSON ＋ 4 條可打勾的驗收
├── SCORECARD.md ──────── 你的可控度計分表（上課時填）
├── run_gates.py ──────── ★ 一行跑完五道閘門
│
├── schemas/
│   └── meal_analysis.schema.json ── 契約：欄位、型別、範圍
│
├── domain/ ───────────── 地基：規矩。不 import 任何外部套件
│   ├── entities.py                 MealAnalysis（回傳的東西長什麼樣）
│   └── exceptions.py               領域錯誤（NotFoodError…）
│
├── application/ ──────── 辦公室：做事流程
│   ├── ports/nutrition_gateway.py  ★ 插座規格（已寫好，不要改）
│   └── use_cases/analyze_meal.py   ★ TODO ← 上機① 你要填這裡
│
├── adapter/ ──────────── 外牆：真的插頭（上機② 讓 AI 生在這裡）
├── infrastructure/
│   └── fake_nutrition.py ───────── ★ 假電器（確定性，已寫好）
├── entrypoints/cli.py ── 一行指令走完整流程，不用起服務
│
├── checks/ ───────────── 五道閘門的實作（純內建函式庫，看得懂）
└── labs/ ─────────────── 上機 ①②③ 的步驟
```

---

## 上機順序

| 上機 | 你要做什麼 | 做完計分板應該是 |
|---|---|---|
| 起點 | 什麼都不做，先跑 `python3 run_gates.py` | **3 / 5** |
| [① 打地基](labs/LAB1.md) | 填 `application/use_cases/analyze_meal.py`；體驗架構閘門變紅 | **5 / 5** |
| [② 留插座](labs/LAB2.md) | 讓 AI 生真的插頭 `adapter/`；確認換插頭時牆不用動 | **5 / 5**（仍離線） |
| [③ 畫施工圖](labs/LAB3.md) | 改 `SPEC.md` 一行 → 重新生成 → 看 diff 範圍 | **5 / 5** |

**重點不是把五個變綠，是「你旁邊的人也是五個綠，而且你們的檔案長得一樣」。**

---

## 常見狀況

| 症狀 | 原因 | 處理 |
|---|---|---|
| `python3: command not found` | 沒有 Python | 用 `py -3`（Windows）或見下方「沒有 Python 怎麼辦」 |
| 起點不是 3 / 5 | 你動過檔案，或下載不完整 | 重新 clone（或 `git checkout .` 還原） |
| 封印閘門紅了 | 有人（多半是 AI）改了 `SPEC.md` / `AGENTS.md` / `checks/` | 這就是本課的重點。看 `labs/LAB1.md` 的「反作弊」段 |
| 想故意改規則 | 可以，但要**自己決定**，不是 AI 順手改 | 改完跑 `python3 checks/seal.py` 重新封印 |

### 沒有 Python 怎麼辦

這個資料夾的價值有一半在「讀」，不在「跑」：

1. 打開 `AGENTS.md` 和 `SPEC.md`——**這兩個檔案就是可控的來源**。
2. 把 `checks/gate_architecture.py` 貼給 AI，請它「照這個規則檢查我的專案」。
3. 上機 ③（改一行 spec 看 diff）完全不需要跑起來，只需要 Git。

---

## 課後：怎麼把這套搬進自己的專案

1. 複製 `AGENTS.md`，把裡面的資料夾名稱改成你的專案的。
2. 複製 `checks/gate_architecture.py`，改 `FORBIDDEN` 清單成你的技術棧。
3. 複製 `checks/gate_seal.py` ＋ `seal.py`，把你的 `SPEC.md`、測試檔、CI 設定放進保護名單。
4. 把 `run_gates.py` 接進 CI：它的離開碼是 0（全綠）或 1（有紅燈），可以直接當 CI 的 gate。

授權：教學用途自由取用。案例中的 AI 服務呼叫僅為示範，不含任何金鑰。
