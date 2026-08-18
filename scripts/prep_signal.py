#!/usr/bin/env python3
"""Join SEGIS telecom-signalling population to the census township table.

Everything else in this project counts people where they are *registered* or
where they *usually live*. Signalling counts where the phone actually was. That
is the only source here that can separate 「白天在哪裡」 from 「晚上在哪裡」,
which is the question behind「社宅要蓋在工作旁邊還是睡覺的地方旁邊」.

Source: 社會經濟資料服務平臺（SEGIS）行政區電信信令人口統計，資料期 112 年 11 月。

What the numbers are, in the platform's own terms:
    平日夜間停留人數  weekday nights spent in the district — the residence proxy
    平日日間活動人數  weekday daytime presence — the workplace/school proxy
    旅次              trips beginning or ending in the district, by time band

It counts SIM cards, not people. Two phones is two people; a child or an elderly
person without one is nobody. Airports and tourist towns record travellers as
residents. Mountain districts with thin coverage under-count. The ratios below
are usable; any single district's absolute figure is not.

    python3 scripts/prep_signal.py
"""
import csv, json, pathlib, statistics, sys, xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'sources' / '112年11月行政區電信信令人口統計_鄉鎮市區.csv'
AREA_DIR = ROOT / 'data_TW' / '01_人口分布' / '普查_縣市'
OUT = ROOT / 'data' / 'tw_signal.json'
AREA_TAG = '土地面積_平方公里_Total_land_area_km2'

# Column positions in the English header row (the file carries a Chinese second
# header row that must be skipped, not parsed).
COL = {'county': 1, 'town': 3, 'nightWork': 4,
       'morningWork': 5, 'afternoonWork': 6, 'dayWork': 7,
       'nightWeekend': 8, 'morningWeekend': 9, 'afternoonWeekend': 10, 'dayWeekend': 11,
       'tripsWork': (12, 16), 'tripsWeekend': (16, 20)}


def land_areas():
    """各鄉鎮市區的土地面積（平方公里），取自普查的「常住人口數及人口密度」表。

    為什麼不從圖形算：簡化過的圖形算出來的總面積比官方多 1.1%，
    小面積的行政區誤差可以到 6%。密度是拿來排名的，分母錯 6% 就會換名次。
    官方表就在 data_TW 裡，沒有理由自己推一個。

    每個縣市檔的第一列是該縣市的合計，後面才是各鄉鎮市區，中間夾英文名的空白列。
    逐縣市與合計列對帳，對不上就中止。
    """
    out, county_tot = {}, {}
    files = sorted(AREA_DIR.glob('*/*常住人口數及人口密度_109民國年.xml'))
    if not files:
        sys.exit(f'找不到面積來源：{AREA_DIR}')
    for f in files:
        rows = []
        for rec in ET.parse(f).getroot():
            name = (rec[0].text or '').replace('\u3000', '').strip()
            node = rec.find(AREA_TAG)
            val = (node.text or '').strip() if node is not None else ''
            if not name or not val:          # 英文名那一列的數值是空的
                continue
            rows.append((name, float(val)))
        if not rows:
            sys.exit(f'{f.name} 一列都讀不到，欄位名可能改了')
        county, total = rows[0]              # 第一列是縣市合計
        county_tot[county] = total
        for name, area in rows[1:]:
            out[f'{county}/{name}'] = area
        # 來源四捨五入到 0.1 平方公里，所以每一個鄉鎮市區最多差 0.05
        tol = 0.05 * len(rows[1:]) + 0.05
        got = sum(a for _, a in rows[1:])
        if abs(got - total) > tol:
            sys.exit(f'{county}的鄉鎮市區面積加總 {got:.1f} 對不上合計 {total:.1f}'
                     f'（容差 {tol:.2f}）')
    nation = sum(county_tot.values())
    if abs(nation - 36197) > 22 * 0.05 + 1:
        sys.exit(f'22 縣市面積加總 {nation:.1f} 對不上臺灣土地面積 36,197 平方公里')
    return out


def main():
    if not SRC.exists():
        sys.exit(f'缺少來源檔：{SRC}')
    rows = list(csv.reader(SRC.open(encoding='utf-8-sig')))
    head = rows[0]
    assert head[0] == 'COUNTY_ID' and head[4] == 'NIGHT_WORK', '欄位順序與預期不符'
    body = [r for r in rows[2:] if r and r[0]]          # row 1 is the Chinese header

    periods = {r[-1] for r in body}
    assert len(periods) == 1, f'混到多個資料期：{periods}'
    period = periods.pop()

    areas = land_areas()
    town = {t['key']: t for t in
            json.loads((ROOT / 'data' / 'tw_town_data.json').read_text(encoding='utf-8'))['towns']}

    out, missing = [], []
    for r in body:
        key = f'{r[COL["county"]]}/{r[COL["town"]]}'
        t = town.get(key)
        if t is None:
            missing.append(key)
            continue
        nw, dw = int(r[COL['nightWork']]), int(r[COL['dayWork']])
        nwe, dwe = int(r[COL['nightWeekend']]), int(r[COL['dayWeekend']])
        # 上午是 07:00-13:00、下午是 13:00-19:00，來源分開給。
        # 「日間活動人數」是這兩段合起來的一個代表值，不是兩者相加。
        mw, aw = int(r[COL['morningWork']]), int(r[COL['afternoonWork']])
        mwe, awe = int(r[COL['morningWeekend']]), int(r[COL['afternoonWeekend']])
        area = areas.get(key)
        if area is None:
            sys.exit(f'{key} 沒有土地面積，無法算密度')
        trips = lambda a, b: sum(int(r[i]) for i in range(a, b))
        out.append({
            'key': key, 'county': t['county'], 'name': t['name'],
            'nightWork': nw, 'dayWork': dw, 'nightWeekend': nwe, 'dayWeekend': dwe,
            'morningWork': mw, 'afternoonWork': aw,
            'morningWeekend': mwe, 'afternoonWeekend': awe,
            # >1 means the district fills up by day: somewhere people go, not live.
            'ratio': round(dw / nw, 3),
            'ratioWeekend': round(dwe / nwe, 3),
            # 上午（07:00-13:00）那一段自己的比與淨值。問「早上人在哪」的時候，
            # 該看的是這一段，不是含下午的平均。
            'morningRatio': round(mw / nw, 3),
            'morningNet': mw - nw,
            'area': area,
            'morningDensity': round(mw / area),
            'nightDensity': round(nw / area),
            'tripsWork': trips(*COL['tripsWork']),
            'tripsWeekend': trips(*COL['tripsWeekend']),
            # Signalling 112/11 against census 常住人口 109/11: three years apart,
            # so a gap is partly real change and partly method. Kept as a ratio
            # because the outliers are exactly where the method breaks.
            'residents': t['residents'],
            'signalRatio': round(nw / t['residents'], 3),
            'vacancy': t['vacancy'], 'houses': t['houses'],
            'households': t['households'], 'inflow': t['inflow'],
        })
    assert not missing, f'信令有、普查沒有的鄉鎮市區：{missing}'
    absent = sorted(set(town) - {o['key'] for o in out})
    assert not absent, f'普查有、信令沒有的鄉鎮市區：{absent}'

    nat = {k: sum(o[k] for o in out) for k in
           ('nightWork', 'dayWork', 'nightWeekend', 'dayWeekend', 'residents',
            'morningWork', 'afternoonWork', 'morningWeekend', 'afternoonWeekend')}
    nat['area'] = round(sum(o['area'] for o in out), 1)
    nat['ratio'] = round(nat['dayWork'] / nat['nightWork'], 3)
    nat['morningRatio'] = round(nat['morningWork'] / nat['nightWork'], 3)
    nat['signalRatio'] = round(nat['nightWork'] / nat['residents'], 3)
    med = statistics.median(o['ratio'] for o in out)

    data = {
        'period': '民國 112 年 11 月',
        'censusPeriod': '民國 109 年 11 月',
        'source': '社會經濟資料服務平臺（SEGIS）行政區電信信令人口統計，'
                  f'資料時間 {period}',
        'national': nat,
        'medianRatio': round(med, 3),
        'medianMorningRatio': round(statistics.median(o['morningRatio'] for o in out), 3),
        'bands': {'morning': '07:00–13:00', 'afternoon': '13:00–19:00'},
        'towns': out,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    print(f'{OUT.relative_to(ROOT)}：{len(out)} 個鄉鎮市區')
    print(f'  全國平日夜間停留 {nat["nightWork"]:,}　普查常住 {nat["residents"]:,}'
          f'　比 {nat["signalRatio"]}')
    print(f'  全國日夜比 {nat["ratio"]}　鄉鎮市區中位數 {data["medianRatio"]}')
    hi = sorted(out, key=lambda o: -o['ratio'])[:5]
    lo = sorted(out, key=lambda o: o['ratio'])[:5]
    print('  白天湧入最多：' + '、'.join(f'{o["county"]}{o["name"]} {o["ratio"]}' for o in hi))
    print('  白天淨流出最多：' + '、'.join(f'{o["county"]}{o["name"]} {o["ratio"]}' for o in lo))
    hm = sorted(out, key=lambda o: -o['morningDensity'])[:5]
    print('  上午活動密度最高：' + '、'.join(
        f'{o["county"]}{o["name"]} {o["morningDensity"]:,}/km²' for o in hm))
    hn = sorted(out, key=lambda o: -o['morningNet'])[:5]
    print('  上午淨流入最多：' + '、'.join(
        f'{o["county"]}{o["name"]} {o["morningNet"]:+,}' for o in hn))
    odd = sorted(out, key=lambda o: -abs(o['signalRatio'] - 1))[:4]
    print('  信令與普查差最大：' + '、'.join(
        f'{o["county"]}{o["name"]} {o["signalRatio"]}' for o in odd))


if __name__ == '__main__':
    main()
