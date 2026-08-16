# 臺灣人口分布與住宅供應 資料集

為評估社會住宅政策而蒐集的公開資料，共 **566 個檔案／66.3 MB**，取自 11 個機關。
下載時間：2026-08-16。

每個檔案的來源網址、HTTP 狀態、位元組數與 SHA-256 都記在 `_metadata/manifest.csv`，
可據以查核來源或偵測上游更新。

## 資料夾結構

| 資料夾 | 檔數 | 內容 |
|---|---:|---|
| `01_人口分布` | 75 | 普查常住人口（全國表＋22 縣市表，縣市表含鄉鎮市區細分）。人口需求端的基礎。 |
| `02_住宅存量` | 3 | 普查住宅單位數與財政部房屋稅籍統計。住宅供給端的存量。 |
| `03_人口動態_戶籍` | 87 | 戶政司村里戶籍人口月報、村里戶數與鄉鎮市區人口密度。普查十年一次，這是唯一能做到每月、每村里的序列。檔案量大，未入版控，執行下載腳本即可取得。 |
| `03_人口動態_電信信令` | 6 | 主計總處電信信令人口——夜間停留（≈實際居住）、日間活動、特定區域旅次。 |
| `04_住宅政策_中央` | 5 | 住宅補貼、公益出租人稅賦減徵、國有非公用土地供社宅清冊。 |
| `05_社會住宅_地方` | 8 | 六都與臺東的社宅基地、戶數、包租代管媒合統計。 |
| `06_地理圖資` | 1 | 縣市界 GeoJSON，供製圖使用。 |
| `07_普查109年_統計表` | 381 | 109 年普查統計表原檔（.ods）：住宅所有權屬、使用情形、竣工年份、樓地板面積、空閒住宅、家戶型態、遷徙與通勤。含全國表與各縣市表。 |

## 主要來源機關

- 行政院主計總處（456 檔）
- 戶政司（87 檔）
- 統計處（6 檔）
- 內政部國土管理署（4 檔）
- 財政部財政資訊中心（3 檔）
- 臺中市政府都市發展局（3 檔）
- 桃園市政府都市發展局（2 檔）
- 臺南市政府都市發展局（2 檔）
- 財政部國有財產署（1 檔）
- 臺北市政府都市發展局（1 檔）
- g0v twgeojson（1 檔）

## 判讀提醒

- **常住人口 ≠ 戶籍人口。** 普查的常住人口是實際居住者，與戶籍登記人口差距可觀，
  雙北、新竹尤其明顯。評估住宅需求應以常住人口與住戶數為準。
- **電信信令要去 SEGIS 拿完整版。** 這個資料夾裡的是 data.gov.tw 上的 109 年 11 月、
  縣市層級。SEGIS（segis.moi.gov.tw）另有 112 年 11 月，且縣市、鄉鎮市區、村里三級
  免費且免申請，並提供 SHP。做空間分析請以 SEGIS 版為準。
- **99 年資料早於五都改制。** 桃園縣→桃園市、臺北縣→新北市；臺中／臺南／高雄要取
  「縣市合計」的母列，不能取合併前的市／縣子列，否則兩期無法對齊。
- **普查十年一次，但常住人口已年度化。** 主計總處自 115 年起雙軌發布常住人口與戶籍
  人口；115 年 1 月 1 日全國常住人口 2,371 萬人，較戶籍人口多 41.1 萬（1.8%）。
  趨勢分析應改用這個年度序列，不必再等下次普查。

## 年度追蹤該用什麼

普查十年才一次，中間年份要靠這幾種替代來源：

| 想看的事 | 資料 | 頻率 | 最細層級 |
|---|---|---|---|
| 名目人口 | 戶籍人口（內政部戶政司） | 每月 | 村里 |
| 常住人口 | 常住人口統計（主計總處，115 年起） | 每年 | 縣市 |
| 實際居住／日夜人口 | 電信信令人口（SEGIS） | 109、112 年 11 月 | 村里 |
| 空屋 | 低度使用（用電）住宅（內政部） | **每半年** | 鄉鎮市區 |
| 住宅存量 | 房屋稅籍住宅類數量（財政部） | 每季 | 行政區 |
| 房價負擔 | 房價所得比、貸款負擔率（內政部） | 每季 | 縣市 |

低度使用住宅的定義是**每月平均用電度數 ≤ 60 度**；109 年起改為每半年統計一次，
上半年採 5、6 月用電，下半年採 11、12 月用電，並結合房屋稅籍住宅類資料與全國地址
母體資料庫推計。這是台灣目前唯一制度化的「用電推估空屋」，不必自己重造。

## 需要在本機補抓的資料

以下來源會擋非瀏覽器請求（Cloudflare 人機驗證或 WAF），在一般 Mac 上用瀏覽器開即可下載：

| 資料 | 位置 |
|---|---|
| 低度使用（用電）住宅宅數及比率 | https://pip.moi.gov.tw 　不動產資訊平台 → 住宅資訊統計彙報 |
| 社會住宅興辦進度（直接興建／包租代管，分縣市） | https://pip.moi.gov.tw/v3/b/SCRB0501.aspx |
| 房價所得比、貸款負擔率 | https://pip.moi.gov.tw 　住宅負擔能力統計 |
| 99 年普查統計表（.ods） | https://census.dgbas.gov.tw/PHC2010/chinese/51/ 　表號見下方清單 |
| 電信信令 112 年 11 月（縣市／鄉鎮市區／村里，CSV＋SHP） | https://segis.moi.gov.tw/STATCloud/QueryInterfaceView |
| 常住人口年度統計 | https://www.stat.gov.tw 　主計總處新聞稿與統計表 |

99 年各表的完整檔名清單在 `01_人口分布/普查_全國/人口及住宅普查*_099民國年.xml`——
那個檔案本身就是普查的表目錄，共 1,037 筆，每筆都附直接下載連結。

## 重新下載

```bash
python3 scripts/fetch_sources.py --out "<這個資料夾>"
```

已成功下載的檔案會依 `_metadata/manifest.csv` 略過，只重試失敗的項目；
加 `--force` 可全部重抓。


## 本次未取得（456 筆）

| 狀態 | 資料集 | 網址 |
|---|---|---|
| cloudflare | 常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06134.xml |
| cloudflare | 住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06186.xml |
| cloudflare | 常住人口之年齡結構（不含移工） | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06136.xml |
| cloudflare | 常住人口之性比例（不含移工） | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06135.xml |
| cloudflare | ５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06140.xml |
| cloudflare | ６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06163.xml |
| cloudflare | １５歲以上常住人口之教育程度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06137.xml |
| cloudflare | １５歲以上民間常住人口之工作狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06139.xml |
| cloudflare | 住宅單位數（含空閒住宅） | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06209.xml |
| URLError:ConnectionResetError | 臺南市社會住宅案地及戶數資料 | https://soa.tainan.gov.tw/Api/Service/Get/36dded74-0716-46d0-abfd-fa4ebc22d565 |
| URLError:ConnectionResetError | 臺南市社會住宅包租代管辦理廠商資訊 | https://soa.tainan.gov.tw/Api/Service/Get/b7452117-47b4-49de-a9ad-32ca1b8aed96 |
| URLError:ConnectionResetError | 高雄市社會住宅包租代管統計 | https://openapi.kcg.gov.tw/Api/Service/Get/d0eed3a0-d8ff-46fe-be79-678bab123065 |
| URLError:ConnectionResetError | 109 年臺東縣社會住宅 | https://ttone.taitung.gov.tw/download?id=gAwMt7n9PkiQV5cFJbY1RQ%3D%3D |
| cloudflare | 桃園市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06147.xml |
| cloudflare | 新竹縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06148.xml |
| cloudflare | 嘉義市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06160.xml |
| cloudflare | 連江縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06162.xml |
| cloudflare | 臺東縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06155.xml |
| cloudflare | 雲林縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06175.xml |
| cloudflare | 嘉義縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06176.xml |
| cloudflare | 屏東縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06177.xml |
| cloudflare | 桃園縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06170.xml |
| cloudflare | 新竹縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06171.xml |
| cloudflare | 彰化縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06173.xml |
| cloudflare | 新竹市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06182.xml |
| cloudflare | 金門縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06184.xml |
| cloudflare | 臺南市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06167.xml |
| cloudflare | 彰化縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06196.xml |
| cloudflare | 南投縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06197.xml |
| cloudflare | 雲林縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06198.xml |
| cloudflare | 新北市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06210.xml |
| cloudflare | 臺中市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06212.xml |
| cloudflare | 南投縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06220.xml |
| cloudflare | 雲林縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06221.xml |
| cloudflare | 屏東縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06200.xml |
| cloudflare | 嘉義市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06206.xml |
| cloudflare | 臺中市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06189.xml |
| cloudflare | 新竹縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06194.xml |
| cloudflare | 屏東縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06223.xml |
| cloudflare | 新竹市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06228.xml |
| cloudflare | 宜蘭縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06007.xml |
| cloudflare | 嘉義縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06014.xml |
| cloudflare | 新竹市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06020.xml |
| cloudflare | 連江縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06185.xml |
| cloudflare | 金門縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06161.xml |
| cloudflare | 苗栗縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06172.xml |
| cloudflare | 南投縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06174.xml |
| cloudflare | 臺中市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06166.xml |
| cloudflare | 澎湖縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06180.xml |
| cloudflare | 屏東縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06154.xml |
| cloudflare | 澎湖縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06157.xml |
| cloudflare | 連江縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06208.xml |
| cloudflare | 臺東縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06201.xml |
| cloudflare | 花蓮縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06202.xml |
| cloudflare | 宜蘭縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06192.xml |
| cloudflare | 苗栗縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06195.xml |
| cloudflare | 嘉義縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06199.xml |
| cloudflare | 金門縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06207.xml |
| cloudflare | 臺北市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06188.xml |
| cloudflare | 金門縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06230.xml |
| cloudflare | 桃園縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06216.xml |
| cloudflare | 新竹縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06217.xml |
| cloudflare | 苗栗縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06218.xml |
| cloudflare | 臺東縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06224.xml |
| cloudflare | 基隆市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06227.xml |
| cloudflare | 臺北市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06211.xml |
| cloudflare | 臺南市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06213.xml |
| cloudflare | 新北市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06141.xml |
| cloudflare | 臺北市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06142.xml |
| cloudflare | 苗栗縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06149.xml |
| cloudflare | 彰化縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06150.xml |
| cloudflare | 南投縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06151.xml |
| cloudflare | 臺南市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06144.xml |
| cloudflare | 高雄市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06145.xml |
| cloudflare | 臺中市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06004.xml |
| cloudflare | 臺南市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06005.xml |
| cloudflare | 桃園市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06008.xml |
| cloudflare | 苗栗縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06010.xml |
| cloudflare | 彰化縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06011.xml |
| cloudflare | 南投縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06012.xml |
| cloudflare | 雲林縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06013.xml |
| cloudflare | 屏東縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06015.xml |
| cloudflare | 臺東縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06016.xml |
| cloudflare | 連江縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06023.xml |
| cloudflare | 新北市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06002.xml |
| cloudflare | 澎湖縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06018.xml |
| cloudflare | 基隆市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06019.xml |
| cloudflare | 臺北市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06003.xml |
| cloudflare | 嘉義市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06021.xml |
| cloudflare | 金門縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06022.xml |
| cloudflare | 新竹縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06009.xml |
| cloudflare | 花蓮縣常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06017.xml |
| cloudflare | 高雄市常住人口數及人口密度 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06006.xml |
| cloudflare | 基隆市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06181.xml |
| cloudflare | 嘉義市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06183.xml |
| cloudflare | 基隆市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06204.xml |
| cloudflare | 新竹市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06205.xml |
| cloudflare | 花蓮縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06225.xml |
| cloudflare | 澎湖縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06226.xml |
| cloudflare | 嘉義市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06229.xml |
| cloudflare | 連江縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06231.xml |
| cloudflare | 宜蘭縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06215.xml |
| cloudflare | 彰化縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06219.xml |
| cloudflare | 嘉義縣住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06222.xml |
| cloudflare | 高雄市住宅單位數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06214.xml |
| cloudflare | 新北市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06164.xml |
| cloudflare | 臺東縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06178.xml |
| cloudflare | 花蓮縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06179.xml |
| cloudflare | 臺北市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06165.xml |
| cloudflare | 高雄市６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06168.xml |
| cloudflare | 基隆市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06158.xml |
| cloudflare | 新竹市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06159.xml |
| cloudflare | 宜蘭縣６歲以上常住人口之工作地及就學地狀況 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06169.xml |
| cloudflare | 花蓮縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06156.xml |
| cloudflare | 雲林縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06152.xml |
| cloudflare | 嘉義縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06153.xml |
| cloudflare | 臺中市５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06143.xml |
| cloudflare | 宜蘭縣５歲以上常住人口之遷徙情形 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06146.xml |
| cloudflare | 新北市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06187.xml |
| cloudflare | 臺南市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06190.xml |
| cloudflare | 高雄市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06191.xml |
| cloudflare | 澎湖縣住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06203.xml |
| cloudflare | 桃園市住戶數、常住人口數及平均每戶人口數 | https://www.dgbas.gov.tw/public/data/open/Cen/Mp06193.xml |
| cloudflare | 表18、5歲以上常住人口5年前居住地－按經常居住地區分 | https://census.dgbas.gov.tw/PHC2010/chinese/51/318.ods |
| cloudflare | 表19、5歲以上常住人口遷徙情形－按經常居住地區分 | https://census.dgbas.gov.tw/PHC2010/chinese/51/319.ods |
| cloudflare | 表20、臺灣地區5歲以上常住人口跨縣市之遷徙狀況 | https://census.dgbas.gov.tw/PHC2010/chinese/51/320.ods |
| cloudflare | 表21、臺灣地區5歲以上跨縣市遷徙人口之年齡結構 | https://census.dgbas.gov.tw/PHC2010/chinese/51/321.ods |
| cloudflare | 表22、臺灣地區15歲以上跨縣市遷徙人口之教育程度 | https://census.dgbas.gov.tw/PHC2010/chinese/51/322.ods |
| cloudflare | 表23、臺灣地區15歲以上跨縣市遷徙人口之婚姻狀況 | https://census.dgbas.gov.tw/PHC2010/chinese/51/323.ods |
| cloudflare | 表24、臺灣地區15歲以上跨縣市遷徙人口之工作狀況 | https://census.dgbas.gov.tw/PHC2010/chinese/51/324.ods |
| cloudflare | 表25、臺灣地區15歲以上跨縣市遷徙人口有工作者之職業分布 | https://census.dgbas.gov.tw/PHC2010/chinese/51/325.ods |
| cloudflare | 表67、住戶數、常住人口數及平均每戶人口數 | https://census.dgbas.gov.tw/PHC2010/chinese/51/367.ods |
| cloudflare | 表69、普通住戶之家戶型態 | https://census.dgbas.gov.tw/PHC2010/chinese/51/369.ods |
| cloudflare | 表84、普通住戶之住宅所有權屬 | https://census.dgbas.gov.tw/PHC2010/chinese/51/384.ods |
| cloudflare | 表85、普通住戶之住宅擁有情形 | https://census.dgbas.gov.tw/PHC2010/chinese/51/385.ods |
| cloudflare | 表87、住宅單位數 | https://census.dgbas.gov.tw/PHC2010/chinese/51/387.ods |
| cloudflare | 表88、住宅之建築類型與使用狀況 | https://census.dgbas.gov.tw/PHC2010/chinese/51/388.ods |
| cloudflare | 表89、住宅之竣工年份 | https://census.dgbas.gov.tw/PHC2010/chinese/51/389.ods |
| cloudflare | 表90、住宅之樓地板面積 | https://census.dgbas.gov.tw/PHC2010/chinese/51/390.ods |
| cloudflare | 表91、空閒住宅之竣工年份 | https://census.dgbas.gov.tw/PHC2010/chinese/51/391.ods |
| cloudflare | 表92、空閒住宅之樓地板面積 | https://census.dgbas.gov.tw/PHC2010/chinese/51/392.ods |
| cloudflare | 表93、有人經常居住住宅之居住人數 | https://census.dgbas.gov.tw/PHC2010/chinese/51/393.ods |
| cloudflare | 表94、有人經常居住住宅之平均每人居住面積 | https://census.dgbas.gov.tw/PHC2010/chinese/51/394.ods |
| cloudflare | 表95、有人經常居住住宅之房廳數 | https://census.dgbas.gov.tw/PHC2010/chinese/51/395.ods |
| cloudflare | 表96、有人經常居住住宅之平均每人使用房廳數及衛浴套數 | https://census.dgbas.gov.tw/PHC2010/chinese/51/396.ods |
| cloudflare | 表97、有人經常居住住宅之用途 | https://census.dgbas.gov.tw/PHC2010/chinese/51/397.ods |
| cloudflare | 表9、臺灣地區5歲以上跨縣市遷徙人口概況－按年齡分 | https://census.dgbas.gov.tw/PHC2010/chinese/52/90.odt |
| cloudflare | 表10、臺灣地區15歲以上跨縣市遷徙人口概況－按婚姻狀況及教育程度分 | https://census.dgbas.gov.tw/PHC2010/chinese/52/100.odt |
| cloudflare | 5歲以上常住人口遷徙情形 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01150.ods |
| cloudflare | 普通住戶之家戶型態 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01290.ods |
| cloudflare | 普通住戶之住宅所有權屬 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01320.ods |
| cloudflare | 住宅單位數 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01330.ods |
| cloudflare | 住宅之竣工年份 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01340.ods |
| cloudflare | 住宅之建築類型 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01350.ods |
| cloudflare | 住宅之樓地板面積 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01360.ods |
| cloudflare | 空閒住宅之竣工年份 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01370.ods |
| cloudflare | 空閒住宅之樓地板面積 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01380.ods |
| cloudflare | 有人經常居住住宅之居住人數 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01390.ods |
| cloudflare | 有人經常居住住宅之房廳數 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01400.ods |
| cloudflare | 有人經常居住住宅之平均每人使用房廳數及衛浴套數 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01410.ods |
| cloudflare | 有人經常居住住宅之用途 | https://census.dgbas.gov.tw/PHC2010/chinese/53/01/01420.ods |
