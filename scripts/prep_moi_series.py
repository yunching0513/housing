#!/usr/bin/env python3
"""Pull 內政部's low-electricity-use housing series out of the statistics booklet.

The census gives one very detailed snapshot (109 年 11 月). This booklet gives a
thin but long series: the same rate every half-year, back to 98 年. Joining them
is what turns "空屋率 13.05%" into "空屋率正在往哪走".

Source: 內政部不動產資訊平台《低度使用(用電)住宅、待售新成屋統計資訊簡冊》
        115 年 7 月出刊（資料期 114 年下半年），存於 data/sources/。

Tables read:
    表 1   98–114H2   縣市比率（23 期）
    表 2   112H2–114H2 縣市宅數與比率（5 期）
    表 6   113H2–114H2 依總面積分（5 級距 × 3 期）
    表 7   113H2–114H2 依屋齡分（7 級距 × 3 期）
    表 8–15 113H2–114H2 六都與新竹縣市各行政區（3 期）

    python3 scripts/prep_moi_series.py
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / 'data' / 'sources' / '114年低度使用住宅統計資訊簡冊.pdf'
OUT = ROOT / 'data' / 'tw_moi_series.json'

COUNTIES = ['新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '宜蘭縣',
            '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣', '屏東縣',
            '臺東縣', '花蓮縣', '澎湖縣', '基隆市', '新竹市', '嘉義市', '金門縣', '連江縣']
AREAS = ['全國'] + COUNTIES

# 23 columns of 表 1. The method changed twice, and the booklet says so in a
# footnote most readers skip; carrying it in the data means the page can draw it.
#   98–107  比率推估法（原始資料已無法取得）
#   108–109 以 110H1 起的精進地址比對法重新勾稽
#   110H1–  直接統計
PERIODS = ([{'label': f'{y}年', 'year': y, 'half': None} for y in range(98, 109)] +
           [{'label': f'{y}年{h}', 'year': y, 'half': i + 1}
            for y in range(109, 115) for i, h in enumerate(['上半年', '下半年'])])
for p in PERIODS:
    p['method'] = ('estimated' if p['year'] <= 107 else
                   'recomputed' if p['year'] <= 109 else 'direct')
    p['short'] = f"{p['year']}{'' if p['half'] is None else ('H%d' % p['half'])}"

SIZE_LABELS = ['20 坪以下', '20–40 坪', '40–60 坪', '60–100 坪', '100 坪以上']
AGE_LABELS = ['5 年以下', '5–10 年', '10–20 年', '20–30 年', '30–40 年', '40–50 年', '50 年以上']
RECENT = ['113H2', '114H1', '114H2']          # the three periods 表 6/7/8–15 carry

# 表 8–15 are one county each, in this order.
DISTRICT_TABLES = ['新北市', '臺北市', '桃園市', '新竹縣', '新竹市', '臺中市', '臺南市', '高雄市']

STOP = re.compile(r'^\s*(註|備註|表\s*\d|圖\s*\d|\(|[一二三四五六七八九十]、)')
CJK = re.compile(r'^[一-鿿]+$')


def text_of(pdf):
    """pdftotext -layout keeps the column alignment, which is the only thing
    holding these tables together: the PDF has no table structure at all."""
    if not shutil.which('pdftotext'):
        sys.exit('需要 pdftotext（poppler-utils）：apt-get install -y poppler-utils')
    with tempfile.TemporaryDirectory() as d:
        txt = pathlib.Path(d) / 'b.txt'
        subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], check=True,
                       capture_output=True)
        return txt.read_text(encoding='utf-8').splitlines()


def num(tok):
    """'-' marks a cell the booklet leaves unstated (連江縣 has a few)."""
    if tok == '-' or tok == '--':
        return None
    return float(tok.replace(',', ''))


def rows_after(lines, start, want, names=None):
    """Read table rows following `start` until the notes line.

    A row is a Chinese name plus exactly `want` numeric tokens. Anything else in
    the band is a wrapped header or a page number, so it is dropped rather than
    guessed at — a mis-parsed row here would be silently wrong on the page.
    """
    out = {}
    for line in lines[start + 1:]:
        if out and STOP.match(line):
            break
        parts = line.split()
        if len(parts) != want + 1 or not CJK.match(parts[0]):
            continue
        if names is not None and parts[0] not in names:
            continue
        try:
            out[parts[0]] = [num(t) for t in parts[1:]]
        except ValueError:
            continue
    return out


def find(lines, pattern, start=0):
    rx = re.compile(pattern)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i
    sys.exit(f'找不到表：{pattern}')


def main():
    if not PDF.exists():
        sys.exit(f'缺少來源檔：{PDF}')
    lines = text_of(PDF)

    # 表 1 — the long series, 23 periods per area.
    t1 = rows_after(lines, find(lines, r'^表1\s'), len(PERIODS), set(AREAS))
    missing = [a for a in AREAS if a not in t1]
    assert not missing, f'表1 缺少：{missing}'

    # 表 2 — stock and count, so the page can say "幾宅" not just "百分之幾".
    t2 = rows_after(lines, find(lines, r'^表2\s'), 15, set(AREAS))
    assert len(t2) == len(AREAS), f'表2 只讀到 {len(t2)} 列'

    t6 = rows_after(lines, find(lines, r'^表6\s'), 15, set(AREAS))
    t7 = rows_after(lines, find(lines, r'^表7\s|^表7\s+\d+\s*$'), 21, set(AREAS))
    if len(t7) != len(AREAS):                      # 表 7's caption wraps oddly
        t7 = rows_after(lines, find(lines, r'依屋齡分'), 21, set(AREAS))
    assert len(t6) == len(AREAS), f'表6 只讀到 {len(t6)} 列'
    assert len(t7) == len(AREAS), f'表7 只讀到 {len(t7)} 列'

    # 表 8–15 — the same three periods, one row per 行政區.
    districts, cursor = [], 0
    for county in DISTRICT_TABLES:
        cursor = find(lines, rf'^表\d+\s.*{county}(各行政區|低度使用)', cursor)
        block = rows_after(lines, cursor, 10)
        for name, v in block.items():
            if name == '全區':
                continue
            districts.append({
                'key': f'{county}/{name}', 'county': county, 'name': name,
                'counts': [v[0], v[2], v[4]], 'rates': [v[1], v[3], v[5]],
                'dCount': v[6], 'dRate': v[7], 'yCount': v[8], 'yRate': v[9],
            })
        cursor += 1

    def bands(table, labels, area):
        n = len(RECENT)
        return [{'label': labels[i], 'rates': table[area][i * n:(i + 1) * n]}
                for i in range(len(labels))]

    data = {
        'source': '內政部不動產資訊平台《低度使用(用電)住宅、待售新成屋統計資訊簡冊》'
                  '115 年 7 月出刊，資料期 114 年下半年',
        'definition': '低度使用(用電)住宅：當期 11、12 月抄表之平均用電度數 60 度以下者。'
                      '與普查「目前沒有使用」是兩套不同的認定。',
        'matchRate': 81.67,
        'periods': PERIODS,
        'recent': RECENT,
        'sizeLabels': SIZE_LABELS,
        'ageLabels': AGE_LABELS,
        'national': {
            'rates': t1['全國'],
            'stockRecent': [t2['全國'][i * 3] for i in range(5)],
            'countRecent': [t2['全國'][i * 3 + 1] for i in range(5)],
            'bySize': bands(t6, SIZE_LABELS, '全國'),
            'byAge': bands(t7, AGE_LABELS, '全國'),
        },
        'counties': [{
            'name': c,
            'rates': t1[c],
            'stockRecent': [t2[c][i * 3] for i in range(5)],
            'countRecent': [t2[c][i * 3 + 1] for i in range(5)],
            'bySize': bands(t6, SIZE_LABELS, c),
            'byAge': bands(t7, AGE_LABELS, c),
        } for c in COUNTIES],
        'districts': districts,
    }

    # Consistency check: 表 2's last five 比率 columns must equal 表 1's last five.
    for area in AREAS:
        a = [t2[area][i * 3 + 2] for i in range(5)]
        b = t1[area][-5:]
        assert a == b, f'{area} 表1 與表2 比率不一致：{a} vs {b}'

    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    nat = t1['全國']
    lo = min(range(len(nat)), key=lambda i: nat[i])
    hi = max(range(len(nat)), key=lambda i: nat[i])
    print(f'{OUT.relative_to(ROOT)}：{len(PERIODS)} 期 × {len(AREAS)} 地區，'
          f'{len(districts)} 個行政區近三期')
    print(f'  全國 {PERIODS[0]["label"]} {nat[0]}% → {PERIODS[-1]["label"]} {nat[-1]}%')
    print(f'  最低 {PERIODS[lo]["label"]} {nat[lo]}%　最高 {PERIODS[hi]["label"]} {nat[hi]}%')
    print(f'  新屋（5 年以下）{" → ".join(f"{r}%" for r in data["national"]["byAge"][0]["rates"])}')


if __name__ == '__main__':
    main()
