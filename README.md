# 臺灣人口分布與住宅供應

為評估社會住宅政策而建的資料與圖表。目前有兩部分：一張已完成的人口變化地圖，
以及一套把相關公開資料抓齊、分類、留下查核紀錄的下載工具。

## 一、資料下載工具

```bash
# 1. 取得政府資料開放平臺的資料集總目錄（約 69 MB，不入版控）
curl -o catalog.csv https://data.gov.tw/datasets/export/csv

# 2. 由目錄挑出需要的資料集，凍結成 sources.json
python3 scripts/make_sources.py catalog.csv

# 3. 下載到指定資料夾
python3 scripts/fetch_sources.py --out "/path/to/2026 - housing_TW"

# 4. 普查的索引檔本身列出上千張統計表，展開後再抓一次
python3 scripts/expand_census.py --out "/path/to/2026 - housing_TW"
python3 scripts/fetch_sources.py --out "/path/to/2026 - housing_TW"

# 5. 由下載紀錄產生該資料夾的說明檔
python3 scripts/make_readme.py --out "/path/to/2026 - housing_TW"
```

`sources.json` 是凍結後的來源清單（資料集識別碼、名稱、機關、更新頻率、下載網址），
`_metadata/manifest.csv` 則記錄每次下載的 HTTP 狀態、位元組數與 SHA-256，可據以查核
來源或偵測上游更新。重跑時會依 manifest 略過已成功的網址，只重試失敗項。

抓取時會遇到兩個政府網站的老問題，腳本都有處理：

- `ws.dgbas.gov.tw` 送出的憑證鏈缺少 TWCA 中介憑證。腳本會依憑證自身的 AIA 欄位取回
  缺少的那張並補進信任鏈——**補齊憑證鏈，不是關閉驗證**。
- 多個政府主機會擋非瀏覽器的 User-Agent。

`census.dgbas.gov.tw` 與 `www.dgbas.gov.tw` 另有 Cloudflare 人機驗證，指令列無法通過；
這些項目會被標記在 manifest 與資料夾 README 中，在一般桌機用瀏覽器開即可下載。

### 版控範圍

`data_TW/` 內已下載的資料多數入版控，但**戶政司的村里逐月序列不入版控**
（`data_TW/03_人口動態_戶籍/`，264 個檔、約 200 MB）。那是逐月累積的檔案，
放進 git 會讓每次 clone 都付出不成比例的代價；在本機執行一次
`fetch_sources.py` 即可取得，且拿到的會是最新一期。

## 二、臺灣人口十年遷徙圖

以民國 99 年與 109 年的**常住人口數**，做出 22 縣市的人口變化地圖。

### 產出

`dist/index.html` — 單一自帶資料的 HTML 頁面（無外部請求）。內含：

- 縣市面量圖（choropleth），可切換三個指標：十年成長率、十年增減人數、109 年人口密度
- 22 縣市排序條圖，與地圖、表格三向連動（hover／點選固定）
- 完整資料表（可排序），同時作為色彩編碼的替代讀取管道
- 金門、馬祖以標示放大倍率的插圖呈現；主圖附比例尺與經緯格網

### 資料來源

| 檔案 | 內容 |
|---|---|
| `data/sources/99年常住人口數及人口密度.csv` | 行政院主計總處，民國 99 年 |
| `data/sources/109年常住人口數及人口密度.xml` | 行政院主計總處，民國 109 年 |
| `data/sources/twCounty2010.geo.json` | g0v `twgeojson`，2010 年縣市界 |

#### 兩期行政區的對齊

99 年資料早於 99 年 12 月 25 日五都改制，因此：

- `桃園縣` → `桃園市`、`臺北縣` → `新北市`
- 臺中、臺南、高雄取原表中**縣市合計的母列**，而非合併前的市／縣子列

對齊後兩期加總分別為 23,123,866 與 23,829,897 人，與原始檔的總計列完全一致（`prep_data.py`
會在執行時印出這項核對）。

### 重建（地圖）

```bash
python3 scripts/prep_data.py   # 合併兩期人口資料 -> data/tw_population.json
python3 scripts/prep_geo.py    # 簡化縣市界圖資  -> data/tw_counties.json
python3 scripts/build.py       # 把資料內嵌進版型 -> dist/index.html
```

`prep_data.py` 與 `prep_geo.py` 預期在含有原始檔的目錄下執行，路徑寫在各檔開頭。

### 製圖決策

- **圖資簡化**：Douglas–Peucker（本島容差 0.0013°、插圖 0.00035°），並移除 0.15 km² 以下的
  島礁——保留蘭嶼、綠島、小琉球、龜山島與澎湖／馬祖的有人島。9.3 MB → 146 KB。
- **色階**：成長率與增減數用發散式（衰退／成長各四階、0 為中點），密度用循序式。所有色階的
  明度單調性、相鄰階差與對比皆以程式推導並通過檢核，未以目視挑色。淺色與深色主題各有一組
  錨點（深色主題由兩端帶亮度、中點吃暗）。
- **字體**：不內嵌網頁字型。中文字型檔動輒數 MB，且 artifact 的 CSP 會擋掉字型 CDN，連結後
  只會靜默 fallback；因此改以三組系統字型堆疊分工（明體標題／黑體內文／等寬數字）。

### 判讀提醒

- 常住人口 ≠ 戶籍人口。
- 連江縣 −19.1% 主要來自駐軍精簡（男性 11,770 → 7,892 人），離島小基數變動須謹慎解讀。
- 成長率為十年累計，非年增率。
