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
import csv, json, pathlib, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'sources' / '112年11月行政區電信信令人口統計_鄉鎮市區.csv'
OUT = ROOT / 'data' / 'tw_signal.json'

# Column positions in the English header row (the file carries a Chinese second
# header row that must be skipped, not parsed).
COL = {'county': 1, 'town': 3, 'nightWork': 4, 'dayWork': 7,
       'nightWeekend': 8, 'dayWeekend': 11,
       'tripsWork': (12, 16), 'tripsWeekend': (16, 20)}


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
        trips = lambda a, b: sum(int(r[i]) for i in range(a, b))
        out.append({
            'key': key, 'county': t['county'], 'name': t['name'],
            'nightWork': nw, 'dayWork': dw, 'nightWeekend': nwe, 'dayWeekend': dwe,
            # >1 means the district fills up by day: somewhere people go, not live.
            'ratio': round(dw / nw, 3),
            'ratioWeekend': round(dwe / nwe, 3),
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
           ('nightWork', 'dayWork', 'nightWeekend', 'dayWeekend', 'residents')}
    nat['ratio'] = round(nat['dayWork'] / nat['nightWork'], 3)
    nat['signalRatio'] = round(nat['nightWork'] / nat['residents'], 3)
    med = statistics.median(o['ratio'] for o in out)

    data = {
        'period': '民國 112 年 11 月',
        'censusPeriod': '民國 109 年 11 月',
        'source': '社會經濟資料服務平臺（SEGIS）行政區電信信令人口統計，'
                  f'資料時間 {period}',
        'national': nat,
        'medianRatio': round(med, 3),
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
    odd = sorted(out, key=lambda o: -abs(o['signalRatio'] - 1))[:4]
    print('  信令與普查差最大：' + '、'.join(
        f'{o["county"]}{o["name"]} {o["signalRatio"]}' for o in odd))


if __name__ == '__main__':
    main()
