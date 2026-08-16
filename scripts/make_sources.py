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
    # ── 03 人口動態（年度追蹤） ──────────────────────────────────────────────
    ('03_人口動態_電信信令', '160179', '各縣市電信信令人口統計－夜間停留人口'),
    ('03_人口動態_電信信令', '160180', '各縣市電信信令人口統計－日間活動人口'),
    ('03_人口動態_電信信令', '160178', '各縣市電信信令人口統計－特定區域旅次'),
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
