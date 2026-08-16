#!/usr/bin/env python3
"""Extract township-level housing and migration data from the 109 年 census.

Every county folder carries the same seven tables broken down by 鄉鎮市區:

  表20 遷徙情形          誰在近五年搬進來
  表31 住戶數            住戶數與常住人口
  表37 住宅使用情形       住宅存量與空屋
  表38 住宅之竣工年份     全部住宅的屋齡
  表39 住宅之樓地板面積   全部住宅的坪數
  表41 空閒住宅之竣工年份  空屋的屋齡
  表42 空閒住宅之樓地板面積 空屋的坪數

The last two are what let the page answer 「空屋這麼多為什麼還要蓋」: an empty home
that is 40 years old in a shrinking township is not stock social housing can use.

Note the census uses two different vacancy concepts, and they are not interchangeable:
表37「目前沒有使用」excludes homes occasionally self-occupied, while 表41/42「空閒住宅」
includes them but excludes homes used as offices or storage. Both are carried through.

    python3 scripts/prep_town_data.py
"""
import json, pathlib, re, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / 'data_TW' / '07_普查109年_統計表' / '縣市'
OUT = ROOT / 'data' / 'tw_town_data.json'

CELL = re.compile(r'<table:table-cell(.*?)(?:/>|>(.*?)</table:table-cell>)', re.S)
ROW = re.compile(r'<table:table-row[^>]*>(.*?)</table:table-row>', re.S)
REPEAT = re.compile(r'number-columns-repeated="(\d+)"')
VALUE = re.compile(r'office:value="([-\d.]+)"')
TAG = re.compile(r'<[^>]+>')
NUM = re.compile(r'\d+(\.\d+)?')
HEAD = ('按鄉鎮市區別分', '按經常居住地區分')
STOP = ('男', '女', 'Male', 'Female')

TABLES = {
    'use':      ('表*住宅使用情形.ods', 6),
    'house':    ('表*住戶數、常住人口數及平均每戶人口數.ods', 9),
    'move':     ('表*遷徙情形.ods', 6),
    'age':      ('表*住宅之竣工年份.ods', 8),
    'area':     ('表*住宅之樓地板面積.ods', 7),
    'vacantAge':  ('表*空閒住宅之竣工年份.ods', 8),
    'vacantArea': ('表*空閒住宅之樓地板面積.ods', 7),
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


def township_rows(path, least):
    """Rows after the 按鄉鎮市區別分 header, stopping before the 男/女 repeat blocks."""
    found, started = {}, False
    for line in sheet(path):
        joined = ''.join(line[:3])
        if any(h in joined for h in HEAD):
            started = True
            continue
        if not started:
            continue
        label = next((c for c in line[:3] if c and not NUM.fullmatch(c)), '')
        if label in STOP:
            break
        nums = [float(c) for c in line if NUM.fullmatch(c or '')]
        if label and len(nums) >= least and label not in found:
            found[label] = nums
    return found


def pick(folder, pattern, least):
    hits = sorted(folder.glob(pattern))
    if not hits:
        return None
    return township_rows(hits[0], least)


def main():
    if not BASE.exists():
        sys.exit(f'缺少 {BASE}\n請先執行 scripts/fetch_sources.py')

    towns, missing = [], []
    for folder in sorted(BASE.iterdir()):
        if not folder.is_dir():
            continue
        county = folder.name
        got = {}
        for key, (pat, least) in TABLES.items():
            got[key] = pick(folder, pat, least)
            if got[key] is None:
                missing.append(f'{county}/{pat}')
        if any(v is None for v in got.values()):
            continue

        for name, use in got['use'].items():
            if name == county:      # the county total row
                continue
            h = got['house'].get(name)
            mv = got['move'].get(name)
            ag = got['age'].get(name)
            ar = got['area'].get(name)
            va = got['vacantAge'].get(name)
            vr = got['vacantArea'].get(name)
            if not all((h, mv, ag, ar, va, vr)):
                missing.append(f'{county}/{name}')
                continue

            houses, occupied, unocc, occasional, other, idle = use[:6]
            households, residents = h[0], h[1]
            moveTotal, sameCounty, otherCounty, abroad = mv[0], mv[3], mv[4], mv[5]
            vacant = va[0]
            towns.append({
                'key': f'{county}/{name}', 'county': county, 'name': name,
                'houses': int(houses), 'occupied': int(occupied),
                'unoccupied': int(unocc), 'occasional': int(occasional),
                'otherUse': int(other), 'idle': int(idle),
                'vacancy': round(idle / houses * 100, 2),
                'households': int(households), 'residents': int(residents),
                'perHousehold': round(houses / households, 3),
                # 遷入率: share of current residents who lived in another county —
                # or abroad — five years ago. Inflow, not net migration: people who
                # left are not counted anywhere in this table.
                'inflow': round((otherCounty + abroad) / moveTotal * 100, 2),
                'inflowCounty': round(sameCounty / moveTotal * 100, 2),
                'vacant': int(vacant),
                # 屋齡, counted back from 109 年
                'ageAll': [int(x) for x in ag[1:5]] + [int(ag[5])],
                'ageVacant': [int(x) for x in va[1:5]] + [int(va[5])],
                'areaAll': [int(x) for x in ar[1:6]],
                'areaVacant': [int(x) for x in vr[1:6]],
                'avgAreaAll': ar[6], 'avgAreaVacant': vr[6],
            })

    def total(field, i=None):
        return sum((t[field][i] if i is not None else t[field]) for t in towns)

    national = {
        'houses': total('houses'), 'households': total('households'),
        'idle': total('idle'), 'vacant': total('vacant'),
        'occasional': total('occasional'), 'otherUse': total('otherUse'),
        'ageVacant': [total('ageVacant', i) for i in range(5)],
        'ageAll': [total('ageAll', i) for i in range(5)],
        'areaVacant': [total('areaVacant', i) for i in range(5)],
        'areaAll': [total('areaAll', i) for i in range(5)],
    }
    national['vacancy'] = round(national['idle'] / national['houses'] * 100, 2)
    national['perHousehold'] = round(national['houses'] / national['households'], 3)

    cut = national['vacancy']
    inflows = sorted(t['inflow'] for t in towns)
    inflowCut = inflows[len(inflows) // 2]          # median, so the split is even by count
    for t in towns:
        busy = t['inflow'] >= inflowCut
        slack = t['vacancy'] >= cut
        t['quadrant'] = ('slack_growing' if busy and slack else
                         'tight_growing' if busy else
                         'slack_shrinking' if slack else 'tight_shrinking')
        t['margin'] = round(t['vacancy'] - cut, 2)

    OUT.write_text(json.dumps({
        'period': '民國109年11月',
        'source': '行政院主計總處 109 年人口及住宅普查 縣市報告表 20、31、37、38、39、41、42',
        'national': national, 'vacancyCut': cut, 'inflowCut': inflowCut,
        'ageLabels': ['40 年以上', '30–39 年', '20–29 年', '10–19 年', '未滿 10 年'],
        'areaLabels': ['未滿 60 m²', '60–120', '120–180', '180–300', '300 m² 以上'],
        'towns': towns,
    }, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    print(f'鄉鎮市區 {len(towns)} 個 ・ {OUT.name} {OUT.stat().st_size / 1024:.0f} KB')
    if missing:
        print(f'※ 缺漏 {len(missing)}：{missing[:6]}')
    n = national
    print(f"\n全國 住宅 {n['houses']:,} 宅 ・ 住戶 {n['households']:,} 戶 ・ "
          f"目前沒有使用 {n['idle']:,} 宅（{n['vacancy']}%）")
    print(f"空閒住宅 {n['vacant']:,} 宅 = 偶爾自住 {n['occasional']:,} + 目前沒有使用 {n['idle']:,}")
    lab = ['40年以上', '30-39年', '20-29年', '10-19年', '未滿10年']
    print('\n空屋的屋齡結構：')
    for i, l in enumerate(lab):
        v, a = n['ageVacant'][i], n['ageAll'][i]
        print(f"  {l:8s} 空屋 {v:>9,} 宅（占空屋 {v/n['vacant']*100:5.1f}%）"
              f"　全部住宅同齡層的空屋率 {v/a*100:5.1f}%")
    print('\n空屋的坪數結構：')
    al = ['未滿60m²', '60-120', '120-180', '180-300', '300m²以上']
    for i, l in enumerate(al):
        v, a = n['areaVacant'][i], n['areaAll'][i]
        print(f"  {l:10s} 空屋 {v:>9,} 宅（占空屋 {v/n['vacant']*100:5.1f}%）"
              f"　該坪數的空屋率 {v/a*100:5.1f}%")
    print(f"\n遷入率中位數 {inflowCut}% ・ 空屋率分界 {cut}%")
    import collections
    for q, c in collections.Counter(t['quadrant'] for t in towns).most_common():
        print(f'  {q}: {c}')


if __name__ == '__main__':
    main()
