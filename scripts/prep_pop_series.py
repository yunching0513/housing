#!/usr/bin/env python3
"""歷次各市縣常住人口：把人口那一軸從兩個時點拉成一條線。

`prep_data.py` compares two census points, 99 → 109. This table covers 45 年 to
115 年 for the same 22 counties, which does two things the two-point comparison
cannot: it shows whether a county's ten-year change is a trend or a blip, and it
carries the population past the census into 113、114、115 年.

Source: 行政院主計總處 表 3 歷次各市縣常住人口（單位：千人）。

Two things about the table itself:

* 69 年以前新竹縣含新竹市、嘉義縣含嘉義市, so those two cities are '-' in the
  first three columns and their parent counties are not comparable across the
  split. Kept as null rather than back-filled.
* 115 年 is marked Ⓟ 初步統計結果 in the source and is flagged as such here.

    python3 scripts/prep_pop_series.py
"""
import json, pathlib, sys, xml.etree.ElementTree as ET, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'sources' / '歷次各市縣常住人口_表3.xlsx'
OUT = ROOT / 'data' / 'tw_pop_series.json'
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

# 新竹市、嘉義市 were split out of their counties in 71 年; the source therefore
# has no separate figure for them before 79 年.
SPLIT_NOTE = {'新竹市': '新竹縣', '嘉義市': '嘉義縣'}


def sheet_rows(path):
    """xlsx without a spreadsheet library: shared strings plus one sheet."""
    z = zipfile.ZipFile(path)
    ss = [''.join(t.text or '' for t in si.iter(NS + 't'))
          for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')]
    out = []
    for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter(NS + 'row'):
        cells = {}
        for c in row.findall(NS + 'c'):
            v = c.find(NS + 'v')
            if v is None:
                continue
            col = ''.join(ch for ch in c.get('r') if ch.isalpha())
            cells[col] = ss[int(v.text)] if c.get('t') == 's' else v.text
        if cells:
            out.append(cells)
    return out


def main():
    if not SRC.exists():
        sys.exit(f'缺少來源檔：{SRC}')
    rows = sheet_rows(SRC)

    header = next((r for r in rows if r.get('B', '').endswith('年')), None)
    assert header, '找不到年度標題列'
    cols = [(k, header[k]) for k in sorted(header, key=lambda k: (len(k), k))
            if header[k].endswith('年') and header[k][:-1].isdigit()]
    years = [int(lab[:-1]) for _, lab in cols]
    assert years == sorted(years) and len(years) >= 8, f'年度欄位異常：{years}'

    hou = json.loads((ROOT / 'data' / 'tw_housing.json').read_text(encoding='utf-8'))
    names = [c['name'] for c in hou['counties']]
    want = set(names) | {'總計'}

    series = {}
    for r in rows:
        label = (r.get('A') or '').replace('　', '').strip()
        if label not in want:
            continue
        # 千人 → 人; '-' marks a county that did not exist separately that year.
        series[label] = [None if r.get(k, '-') in ('-', '') else int(float(r[k]) * 1000)
                         for k, _ in cols]
    missing = [n for n in names if n not in series]
    assert not missing, f'表中缺少：{missing}'
    assert '總計' in series, '找不到總計列'

    # The published 總計 must match the sum of the 22 counties. It will not match
    # exactly: every cell is printed in 千人, so each county carries up to ±500
    # of rounding and 總計 carries its own. 22 counties + the total bounds the
    # gap at 11,500 — anything past that is a real mismatch, not rounding.
    TOL = len(names) * 500 + 500
    for j, y in enumerate(years):
        vals = [series[n][j] for n in names]
        if any(v is None for v in vals):
            continue
        got, want_v = sum(vals), series['總計'][j]
        assert abs(got - want_v) <= TOL, f'{y}年加總{got:,} ≠ 總計{want_v:,}'

    prelim = years[-1]
    latest = len(years) - 1
    i109 = years.index(109)

    counties = []
    for n in names:
        v = series[n]
        counties.append({
            'name': n, 'values': v,
            'firstYear': years[next(i for i, x in enumerate(v) if x is not None)],
            'splitFrom': SPLIT_NOTE.get(n),
            # Change since the census baseline the other pages are locked to.
            'since109': v[latest] - v[i109],
            'since109Pct': round((v[latest] / v[i109] - 1) * 100, 2),
            'peakYear': years[v.index(max(x for x in v if x is not None))],
        })

    data = {
        'source': '行政院主計總處 表3歷次各市縣常住人口（單位原為千人，此處還原為人）',
        'unitNote': '原表單位為千人，因此每個數字的解析度是1,000人',
        'years': years,
        'prelimYear': prelim,
        'censusYears': [99, 109],
        'baseIndex': i109,
        'national': series['總計'],
        'counties': counties,
        'splitNote': '69年以前新竹縣含新竹市、嘉義縣含嘉義市，兩市在前三欄為空值',
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    print(f'{OUT.relative_to(ROOT)}：{len(years)}個年度 × {len(names)}縣市'
          f'（{years[0]}–{years[-1]}年，{prelim}年為初步統計）')
    print(f'全國{years[0]}年{series["總計"][0]:,} → {years[-1]}年{series["總計"][-1]:,}')
    peak = max(range(len(years)), key=lambda j: series['總計'][j])
    print(f'全國高點{years[peak]}年{series["總計"][peak]:,}')
    grow = sorted(counties, key=lambda c: -c['since109Pct'])
    print(f'  109 → {years[-1]}年增最多：'
          + '、'.join(f'{c["name"]}{c["since109Pct"]:+.1f}%' for c in grow[:3]))
    print(f'減最多：'
          + '、'.join(f'{c["name"]}{c["since109Pct"]:+.1f}%' for c in grow[-3:]))


if __name__ == '__main__':
    main()
