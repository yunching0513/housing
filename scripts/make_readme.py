#!/usr/bin/env python3
"""Write the data folder's own README from the download manifest.

Counts and failure lists are derived, never hand-typed, so the description
cannot drift from what is actually on disk.

    python3 scripts/make_readme.py --out data_TW
"""
import argparse, collections, csv, pathlib
from datetime import datetime, timezone

WHAT = {
    '01_人口分布': '普查常住人口（全國表＋22 縣市表，縣市表含鄉鎮市區細分）。人口需求端的基礎。',
    '02_住宅存量': '普查住宅單位數與財政部房屋稅籍統計。住宅供給端的存量。',
    '03_人口動態_電信信令': '主計總處電信信令人口——夜間停留（≈實際居住）、日間活動、特定區域旅次。',
    '03_人口動態_戶籍': '戶政司村里戶籍人口月報、村里戶數與鄉鎮市區人口密度。普查十年一次，'
                        '這是唯一能做到每月、每村里的序列。檔案量大，未入版控，執行下載腳本即可取得。',
    '04_住宅政策_中央': '住宅補貼、公益出租人稅賦減徵、國有非公用土地供社宅清冊。',
    '05_社會住宅_地方': '六都與臺東的社宅基地、戶數、包租代管媒合統計。',
    '06_地理圖資': '縣市界 GeoJSON，供製圖使用。',
    '07_普查109年_統計表': '109 年普查統計表原檔（.ods）：住宅所有權屬、使用情形、竣工年份、樓地板面積、'
                           '空閒住宅、家戶型態、遷徙與通勤。含全國表與各縣市表。',
    '07_普查99年_統計表': '99 年普查對應表。上游有人機驗證，多半需在本機瀏覽器環境補抓。',
}

NOTES = """\
## 判讀提醒

- **常住人口 ≠ 戶籍人口。** 普查的常住人口是實際居住者，與戶籍登記人口差距可觀，
  雙北、新竹尤其明顯。評估住宅需求應以常住人口與住戶數為準。
- **電信信令是單月快照，不是年度序列。** 目前開放的是民國 109 年 11 月、縣市層級，
  是配合普查同期產製的。可以拿來校正普查，不能拿來看逐年趨勢。
- **99 年資料早於五都改制。** 桃園縣→桃園市、臺北縣→新北市；臺中／臺南／高雄要取
  「縣市合計」的母列，不能取合併前的市／縣子列，否則兩期無法對齊。
- **普查十年一次。** 要更密的頻率，見下方「年度追蹤該用什麼」。

## 年度追蹤該用什麼

普查十年才一次，中間年份要靠這幾種替代來源：

| 想看的事 | 資料 | 頻率 | 最細層級 |
|---|---|---|---|
| 名目人口 | 戶籍人口（內政部戶政司） | 每月 | 村里 |
| 實際居住人口 | 電信信令人口（主計總處） | 目前僅 109 年 11 月 | 縣市 |
| 空屋 | 低度使用（用電）住宅（內政部） | **每半年** | 鄉鎮市區 |
| 住宅存量 | 房屋稅籍住宅類數量（財政部） | 每季 | 行政區 |
| 房價負擔 | 房價所得比、貸款負擔率（內政部） | 每季 | 縣市 |

低度使用住宅的定義是**每月平均用電度數 ≤ 60 度**；109 年起改為每半年統計一次，
上半年採 5、6 月用電，下半年採 11、12 月用電，並結合房屋稅籍住宅類資料與全國地址
母體資料庫推計。這是台灣目前唯一制度化的「用電推估空屋」，不必自己重造。
"""

MANUAL = """\
## 需要在本機補抓的資料

以下來源會擋非瀏覽器請求（Cloudflare 人機驗證或 WAF），在一般 Mac 上用瀏覽器開即可下載：

| 資料 | 位置 |
|---|---|
| 低度使用（用電）住宅宅數及比率 | https://pip.moi.gov.tw 　不動產資訊平台 → 住宅資訊統計彙報 |
| 社會住宅興辦進度（直接興建／包租代管，分縣市） | https://pip.moi.gov.tw/v3/b/SCRB0501.aspx |
| 房價所得比、貸款負擔率 | https://pip.moi.gov.tw 　住宅負擔能力統計 |
| 99 年普查統計表（.ods） | https://census.dgbas.gov.tw/PHC2010/chinese/51/ 　表號見下方清單 |

99 年各表的完整檔名清單在 `01_人口分布/普查_全國/人口及住宅普查*_099民國年.xml`——
那個檔案本身就是普查的表目錄，共 1,037 筆，每筆都附直接下載連結。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data_TW')
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    rows = list(csv.DictReader((out / '_metadata' / 'manifest.csv').open(encoding='utf-8-sig')))

    ok = [r for r in rows if r['狀態'] == '200']
    bad = [r for r in rows if r['狀態'] != '200']
    by_cat = collections.Counter(r['分類'].split('/')[0] for r in ok)
    agencies = collections.Counter(r['提供機關'] for r in ok if r['提供機關'])
    total_mb = sum(int(r['位元組']) for r in ok) / 1024 / 1024

    L = [
        '# 臺灣人口分布與住宅供應 資料集',
        '',
        f'為評估社會住宅政策而蒐集的公開資料，共 **{len(ok)} 個檔案／{total_mb:.1f} MB**，'
        f'取自 {len(agencies)} 個機關。',
        f'下載時間：{datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")}。',
        '',
        '每個檔案的來源網址、HTTP 狀態、位元組數與 SHA-256 都記在 `_metadata/manifest.csv`，',
        '可據以查核來源或偵測上游更新。',
        '',
        '## 資料夾結構',
        '',
        '| 資料夾 | 檔數 | 內容 |',
        '|---|---:|---|',
    ]
    for cat in sorted(by_cat):
        L.append(f'| `{cat}` | {by_cat[cat]} | {WHAT.get(cat, "")} |')

    L += ['', '## 主要來源機關', '']
    for a, n in agencies.most_common():
        L.append(f'- {a}（{n} 檔）')

    L += ['', NOTES, MANUAL, '## 重新下載', '', '```bash',
          'python3 scripts/fetch_sources.py --out "<這個資料夾>"',
          '```', '',
          '已成功下載的檔案會依 `_metadata/manifest.csv` 略過，只重試失敗的項目；',
          '加 `--force` 可全部重抓。', '']

    if bad:
        L += ['', f'## 本次未取得（{len(bad)} 筆）', '',
              '| 狀態 | 資料集 | 網址 |', '|---|---|---|']
        seen = set()
        for r in bad:
            k = (r['狀態'], r['資料集名稱'])
            if k in seen:
                continue
            seen.add(k)
            L.append(f'| {r["狀態"]} | {r["資料集名稱"]} | {r["來源網址"]} |')

    (out / 'README.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'{out}/README.md：成功 {len(ok)} 檔 / {total_mb:.1f} MB，未取得 {len(bad)} 筆')


if __name__ == '__main__':
    main()
