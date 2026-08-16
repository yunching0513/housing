#!/usr/bin/env python3
"""Build the housing-supply half of the page data from the 109 年 census tables.

Reads 表87（住宅使用情形）and 表66（住戶數、常住人口數及平均每戶人口數）, both
dated 民國109年11月 — the same reference month as the population tables and the
telecom-signalling release, which is why that month is the site's structural baseline.

Also assigns each county to one of four categories on two axes: whether population
grew, and whether vacancy sits above the national rate. Thresholds are derived, not
chosen: 0% for population, and the national vacancy rate for vacancy.

    python3 scripts/prep_housing.py --data data_TW
"""
import argparse, json, pathlib, re, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CELL = re.compile(r'<table:table-cell(.*?)(?:/>|>(.*?)</table:table-cell>)', re.S)
ROW = re.compile(r'<table:table-row[^>]*>(.*?)</table:table-row>', re.S)
REPEAT = re.compile(r'number-columns-repeated="(\d+)"')
VALUE = re.compile(r'office:value="([-\d.]+)"')
TAG = re.compile(r'<[^>]+>')

COUNTIES = ['新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '基隆市', '新竹市',
            '嘉義市', '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣',
            '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '金門縣', '連江縣']

# Plain-language labels, chosen for a policy-briefing and public audience rather
# than the usual "quadrant I–IV" wording.
QUADRANTS = {
    'tight_growing': {'key': 'tight_growing', 'label': '真的不夠住',
                      'cond': '人變多，房子沒空著', 'act': '新建社宅的第一順位'},
    'slack_growing': {'key': 'slack_growing', 'label': '有房子，但租不起或不合用',
                      'cond': '人變多，房子卻空著', 'act': '先做包租代管與空屋活化'},
    'tight_shrinking': {'key': 'tight_shrinking', 'label': '住得起的人才留得下來',
                        'cond': '人變少，房子沒空著', 'act': '重點在租金負擔，不在增加總量'},
    'slack_shrinking': {'key': 'slack_shrinking', 'label': '房子多到用不完',
                        'cond': '人變少，房子空著', 'act': '新建效益最低，轉向既有住宅改善'},
}


def sheet(path):
    xml = zipfile.ZipFile(path).read('content.xml').decode('utf-8')
    out = []
    for body in ROW.findall(xml):
        line = []
        for attrs, cell in CELL.findall(body):
            rep = REPEAT.search(attrs)
            n = min(int(rep.group(1)) if rep else 1, 32)
            val = VALUE.search(attrs)
            line.extend([val.group(1) if val else
                         TAG.sub('', cell or '').replace('　', '').strip()] * n)
        out.append(line)
    return out


def indexed(rows, wanted, least=6):
    """縣市 -> numeric cells. A county name also shows up in header and English
    rows, so only accept a line that actually carries enough numbers."""
    found = {}
    for line in rows:
        label = next((c for c in line[:3] if c in wanted), None)
        if not label or label in found:
            continue
        nums = [float(c) for c in line if re.fullmatch(r'\d+(\.\d+)?', c or '')]
        if len(nums) >= least:
            found[label] = nums
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(ROOT / 'data_TW'))
    ap.add_argument('--out', default=str(ROOT / 'data' / 'tw_housing.json'))
    args = ap.parse_args()

    base = pathlib.Path(args.data) / '07_普查109年_統計表' / '其他'
    use, hh = base / '表87 住宅使用情形.ods', base / '表66 住戶數、常住人口數及平均每戶人口數.ods'
    for f in (use, hh):
        if not f.exists():
            sys.exit(f'缺少 {f}\n請先執行 scripts/fetch_sources.py')

    pop = {c['name']: c for c in
           json.loads((ROOT / 'data' / 'tw_population.json').read_text(encoding='utf-8'))['counties']}
    want = set(COUNTIES) | {'總計'}
    u, h = indexed(sheet(use), want), indexed(sheet(hh), want)

    def row(name):
        # 表87: 總計, 有人合計, 住宅專用, 兼農工, 無人合計, 偶爾自住, 自住以外, 目前沒有使用
        n = u[name]
        households = h[name][0]
        total, occupied, idle = n[0], n[1], n[7]
        return {
            'houses': int(total),
            'occupied': int(occupied),
            'unoccupied': int(n[4]),
            'occasional': int(n[5]),
            'otherUse': int(n[6]),
            'idle': int(idle),
            'vacancy': round(idle / total * 100, 2),
            'households': int(households),
            'perHousehold': round(total / households, 3),
        }

    national = row('總計')
    cut = national['vacancy']          # 全國空置率，作為「房子空不空」的分界
    counties = []
    for name in COUNTIES:
        r = row(name)
        r['name'] = name
        growing = pop[name]['pct'] > 0
        slack = r['vacancy'] >= cut
        r['quadrant'] = ('slack_growing' if growing and slack else
                         'tight_growing' if growing else
                         'slack_shrinking' if slack else 'tight_shrinking')
        # How close to the vacancy cut, in percentage points. Counties sitting on
        # the line get flagged rather than silently sorted.
        r['margin'] = round(r['vacancy'] - cut, 2)
        counties.append(r)

    payload = {
        'period': '民國109年11月',
        'source': '行政院主計總處 109 年人口及住宅普查 表87、表66',
        'national': national,
        'vacancyCut': cut,
        'quadrants': QUADRANTS,
        'counties': counties,
    }
    pathlib.Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'{args.out}')
    print(f"全國 {national['houses']:,} 宅 / {national['households']:,} 戶 ・ "
          f"空置率 {cut}% ・ 宅戶比 {national['perHousehold']}\n")
    order = {'tight_growing': 0, 'slack_growing': 1, 'tight_shrinking': 2, 'slack_shrinking': 3}
    for q in sorted(QUADRANTS, key=lambda k: order[k]):
        members = [c for c in counties if c['quadrant'] == q]
        print(f"{QUADRANTS[q]['label']}（{QUADRANTS[q]['cond']}）: {len(members)} 個")
        for c in sorted(members, key=lambda c: -pop[c['name']]['pct']):
            flag = ' ←貼近分界' if abs(c['margin']) < 0.5 else ''
            print(f"   {c['name']:5s} 人口{pop[c['name']]['pct']:+6.1f}%  "
                  f"空置{c['vacancy']:5.1f}%  宅戶比{c['perHousehold']:.3f}{flag}")


if __name__ == '__main__':
    main()
