#!/usr/bin/env python3
"""Resolve a curated source list out of the data.gov.tw catalogue into sources.json.

The catalogue export is ~69 MB and changes daily, so it is not committed. This
script freezes the picks — dataset id, title, agency, and every download URL —
into a small manifest that fetch_sources.py can replay anywhere.

    curl -o catalog.csv https://data.gov.tw/datasets/export/csv
    python3 scripts/make_sources.py catalog.csv
"""
import csv, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'sources.json'

COUNTY = (r'新北市|臺北市|桃園[市縣]|臺中[市縣]|臺南[市縣]|高雄[市縣]|基隆市|新竹[市縣]|'
          r'嘉義[市縣]|宜蘭縣|苗栗縣|彰化縣|南投縣|雲林縣|屏東縣|臺東縣|花蓮縣|澎湖縣|金門縣|連江縣')

# Curated picks, by analysis category rather than by agency.
PICKS = [
    # ── 01 人口分布 ──────────────────────────────────────────────────────────
    ('01_人口分布/普查_全國', '10906', '人口及住宅普查（常住人口數及人口密度，99 與 109 年）'),
    ('01_人口分布/普查_全國', '24238', '常住人口數及人口密度'),
    ('01_人口分布/普查_全國', '24759', '住戶數、常住人口數及平均每戶人口數'),
    ('01_人口分布/普查_全國', '24240', '常住人口之年齡結構（不含移工）'),
    ('01_人口分布/普查_全國', '24239', '常住人口之性比例（不含移工）'),
    ('01_人口分布/普查_全國', '24244', '５歲以上常住人口之遷徙情形'),
    ('01_人口分布/普查_全國', '24282', '６歲以上常住人口之工作地及就學地狀況'),
    ('01_人口分布/普查_全國', '24241', '１５歲以上常住人口之教育程度'),
    ('01_人口分布/普查_全國', '24243', '１５歲以上民間常住人口之工作狀況'),
    # ── 02 住宅存量 ──────────────────────────────────────────────────────────
    ('02_住宅存量/普查', '24783', '住宅單位數（含空閒住宅）'),
    ('02_住宅存量/房屋稅籍', '20342', '臺閩地區房屋稅籍所有人歸戶統計表'),
    # ── 03 人口動態（普查十年一次，這裡放年度／月度的替代來源） ─────────────
    ('03_人口動態_電信信令', '160179', '各縣市電信信令人口統計－夜間停留人口'),
    ('03_人口動態_電信信令', '160180', '各縣市電信信令人口統計－日間活動人口'),
    ('03_人口動態_電信信令', '160178', '各縣市電信信令人口統計－特定區域旅次'),
    # 戶籍人口是唯一能做到每月、每村里的序列；戶數尤其重要，住宅需求是以戶計。
    ('03_人口動態_戶籍/村里月報', '8411',  '各村（里）戶籍人口統計月報表'),
    ('03_人口動態_戶籍/村里月報', '77140', '各村（里）戶籍人口統計月報表（新增區域代碼）'),
    ('03_人口動態_戶籍/村里戶數', '77132', '村里戶數、單一年齡人口（新增區域代碼）'),
    ('03_人口動態_戶籍/村里戶數', '32973', '村里戶數、單一年齡人口'),
    ('03_人口動態_戶籍/鄉鎮市區', '8410',  '各鄉鎮市區人口密度'),
    # ── 04 住宅政策 ──────────────────────────────────────────────────────────
    ('04_住宅政策_中央', '73250',  '住宅補貼辦理概況'),
    ('04_住宅政策_中央', '169800', '接受住宅補貼戶次及金額'),
    ('04_住宅政策_中央', '164857', '公益出租人稅賦減徵戶數統計表'),
    ('04_住宅政策_中央', '21232',  '住宅建設下載專區'),
    ('04_住宅政策_中央', '147535', '國有非公用不動產保留供興辦社會住宅清冊'),
    # ── 05 社會住宅（地方政府） ─────────────────────────────────────────────
    ('05_社會住宅_地方', '149652', '桃園市社會住宅名稱與戶數'),
    ('05_社會住宅_地方', '149586', '桃園市社會住宅基地地號及面積表'),
    ('05_社會住宅_地方', '130113', '臺南市社會住宅案地及戶數資料'),
    ('05_社會住宅_地方', '142745', '臺南市社會住宅包租代管辦理廠商資訊'),
    ('05_社會住宅_地方', '155779', '臺北市政府社會住宅包租代管媒合統計資料'),
    ('05_社會住宅_地方', '84140',  '臺中市社會住宅基地地號及面積表'),
    ('05_社會住宅_地方', '166888', '高雄市社會住宅包租代管統計'),
    ('05_社會住宅_地方', '165798', '109 年臺東縣社會住宅'),
]

# County breakdowns of these census tables give 鄉鎮市區 detail — the level social
# housing siting actually happens at.
COUNTY_TABLES = [
    '住宅單位數',
    '常住人口數及人口密度',
    '住戶數、常住人口數及平均每戶人口數',
    '５歲以上常住人口之遷徙情形',
    '６歲以上常住人口之工作地及就學地狀況',
]

EXTRA = [{
    'category': '06_地理圖資',
    'dataset_id': None,
    'title': '臺灣縣市界圖資（2010 年界線）',
    'agency': 'g0v twgeojson',
    'update': '不定期',
    'urls': ['https://raw.githubusercontent.com/g0v/twgeojson/master/json/twCounty2010.geo.json'],
}]

# ── 08 家庭收支調查 ──────────────────────────────────────────────────────────
# 這一批不在 data.gov.tw 的目錄裡，是報告頁的直接連結，所以走 EXTRA 而非 PICKS。
#   https://www.stat.gov.tw/News_Content.aspx?n=3908&s=236588
# 一律取 .ods 不取 .xls：.xls 是 OLE2 二進位，沒有第三方套件讀不動；.ods 是 zip
# 內含 content.xml，scripts/ods_to_csv.py 用內建函式庫就能拆（AGENTS.md §4）。
FIES = 'https://ws.dgbas.gov.tw/001/Upload/463/relfile/11530/236588'
FIES_TABLES = [
    # 114 年橫斷面
    ('49',  '第2表_平均每戶家庭收支按區域別分'),
    ('89',  '第8表_家庭住宅及主要設備概況按區域別分'),
    ('105', '第10表_家庭住宅及主要設備概況依可支配所得按戶數五等分位分'),
    ('77',  '第6表_平均每戶家庭收支依可支配所得按戶數五等分位分'),
    ('45',  '第1表_平均每戶家庭收支按戶內人數分'),
    ('111', '所得收入者第1表_平均每人所得來源按區域別分'),
    # 歷年序列
    ('Year24', '歷年第24表_家庭住宅狀況'),
    ('Year14', '歷年第14表_家庭消費支出結構按消費型態分'),
    ('Year10', '歷年第10表_可支配所得消費支出及儲蓄'),
    ('Year03', '歷年第3表_戶數五等分位組之平均每戶可支配所得'),
    ('Year07', '歷年第7表_戶數十等分位組分界點之可支配所得'),
    ('Year01', '歷年第1表_所得總額與可支配所得'),
    ('Index',  '家庭收支重要指標'),
]
# 名詞解釋與調查方法一起收：設算租金怎麼算、縣市樣本數多少，都只寫在這兩份裡。
FIES_DOCS = [('Definec', '附錄一_名詞解釋'), ('Methodc', '附錄二_調查方法')]

EXTRA += [{
    'category': '08_家庭收支調查',
    'dataset_id': None,
    'title': f'114年家庭收支調查_{name}',
    'agency': '行政院主計總處',
    'update': '每年',
    'urls': [f'{FIES}/{stem}.{ext}'],
} for stem, name, ext in ([(a, b, 'ods') for a, b in FIES_TABLES]
                          + [(a, b, 'odt') for a, b in FIES_DOCS])]


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'catalog.csv')
    csv.field_size_limit(10 ** 9)
    rows = {r['資料集識別碼']: r for r in csv.DictReader(src.open(encoding='utf-8-sig'))}

    def entry(cat, did, title=None):
        r = rows.get(did)
        if not r:
            print(f'  !! dataset {did} not in catalogue', file=sys.stderr)
            return None
        return {
            'category': cat,
            'dataset_id': did,
            'title': title or r['資料集名稱'],
            'catalogue_title': r['資料集名稱'],
            'agency': r['提供機關'],
            'update': r['更新頻率'],
            'urls': [u.strip() for u in r['資料下載網址'].split(';') if u.strip()],
        }

    out = [e for e in (entry(c, d, t) for c, d, t in PICKS) if e]

    pat = re.compile(COUNTY)
    for r in rows.values():
        nm = r['資料集名稱']
        m = pat.match(nm)
        if not m or nm[m.end():] not in COUNTY_TABLES:
            continue
        if '/open/Cen/' not in r['資料下載網址'] and 'ws.dgbas' not in r['資料下載網址']:
            continue
        e = entry(f'01_人口分布/普查_縣市/{m.group(0)}'
                  if nm[m.end():] != '住宅單位數' else f'02_住宅存量/普查_縣市/{m.group(0)}',
                  r['資料集識別碼'])
        if e:
            out.append(e)

    out.extend(EXTRA)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    files = sum(len(e['urls']) for e in out)
    print(f'{OUT.name}: {len(out)} 個資料集 / {files} 個檔案')
    for cat in sorted({e['category'].split('/')[0] for e in out}):
        n = sum(len(e['urls']) for e in out if e['category'].startswith(cat))
        print(f'  {cat:24s} {n:4d} 檔')


if __name__ == '__main__':
    main()
