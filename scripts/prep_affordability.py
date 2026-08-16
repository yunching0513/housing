#!/usr/bin/env python3
"""房價負擔能力指標：把「買不買得起」接進來。

The pages so far measure housing in units of *stock*: how many dwellings, how
many empty. None of them measures **price against income**, which is the thing
social housing actually exists to address. This file adds it.

Source: 內政部不動產資訊平台 房價負擔能力指標季報，115 年第 1 季。
    房價所得比    中位數住宅總價 ÷ 家戶年可支配所得中位數（倍）
    房貸負擔率    中位數住宅貸款月攤還額 ÷ 家戶月可支配所得中位數（%）

Two limits that must travel with the numbers:

1. Both indicators are about **buying**, not renting. Social housing is rental.
   They are the closest official affordability series that exists by county, but
   the exact measure would be 租金所得比, which this source does not publish.
2. 連江縣 is not in the release at all, and 澎湖縣、金門縣 carry the source's own
   「樣本數未達100戶」 flag. Both states are kept, not filled in.

    python3 scripts/prep_affordability.py
"""
import csv, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'sources' / '115Q1房價負擔能力指標_縣市.csv'
OUT = ROOT / 'data' / 'tw_affordability.json'

# 內政部的門檻定義（房價負擔能力指標編製說明）：房貸負擔率 30% 以下為可合理負擔，
# 30–40% 略低，40–50% 偏低，50% 以上過低。這是官方分級，不是本專案自訂。
BANDS = [(30, '可合理負擔'), (40, '略低'), (50, '偏低'), (float('inf'), '過低')]


def band(v):
    return next(lab for cut, lab in BANDS if v < cut)


def main():
    if not SRC.exists():
        sys.exit(f'缺少來源檔：{SRC}')
    rows = list(csv.DictReader(SRC.open(encoding='utf-8-sig')))
    period = {r['期間'] for r in rows}
    assert len(period) == 1, f'混到多個期別：{period}'
    period = period.pop()

    hou = json.loads((ROOT / 'data' / 'tw_housing.json').read_text(encoding='utf-8'))
    names = [c['name'] for c in hou['counties']]
    quad = {c['name']: c['quadrant'] for c in hou['counties']}

    rec = {}
    for r in rows:
        rec[r['地區']] = {
            'burden': float(r['房貸負擔率_百分比']),
            'burdenQ': float(r['房貸負擔率_季變動百分點']),
            'burdenY': float(r['房貸負擔率_年變動百分點']),
            'pir': float(r['房價所得比_倍']),
            'pirQ': float(r['房價所得比_季變動']),
            'pirY': float(r['房價所得比_年變動']),
            # The source flags its own thin cells; a 100-household sample behind a
            # county median is worth showing but not worth ranking on.
            'thin': r['樣本數未達100戶'].strip().lower() == 'true',
        }
    nat = rec.pop('全國')
    missing = [n for n in names if n not in rec]

    counties = []
    for n in names:
        v = rec.get(n)
        counties.append({
            'name': n, 'quadrant': quad[n], 'listed': v is not None,
            **({'burden': None, 'pir': None, 'thin': False, 'band': None}
               if v is None else {**v, 'band': band(v['burden'])}),
        })

    data = {
        'period': period,
        'source': '內政部不動產資訊平台《房價負擔能力指標》季報',
        'measures': {
            'pir': {'label': '房價所得比', 'unit': '倍',
                    'def': '中位數住宅總價 ÷ 家戶年可支配所得中位數。'
                           '9.47 倍代表不吃不喝 9.47 年才買得起中位數住宅。'},
            'burden': {'label': '房貸負擔率', 'unit': '%',
                       'def': '中位數住宅貸款月攤還額 ÷ 家戶月可支配所得中位數。'
                              '內政部分級：30% 以下可合理負擔，30–40% 略低，'
                              '40–50% 偏低，50% 以上過低。'},
        },
        'caveat': '兩項指標衡量的是「買」不是「租」。社宅是租賃政策，'
                  '這是目前唯一有縣市別的官方負擔能力數列，但不是最貼題的那一個。',
        'national': {**nat, 'band': band(nat['burden'])},
        'notListed': missing,
        'counties': counties,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    live = [c for c in counties if c['listed']]
    live.sort(key=lambda c: -c['pir'])
    print(f'{OUT.relative_to(ROOT)}：{period}，{len(live)} 縣市'
          + (f'，未列 {"、".join(missing)}' if missing else ''))
    print(f'  全國 房價所得比 {nat["pir"]} 倍　房貸負擔率 {nat["burden"]}%'
          f'（{band(nat["burden"])}），較上年 {nat["burdenY"]:+.2f} 個百分點')
    for c in live[:4]:
        print(f'  {c["name"]:5s}{c["pir"]:6.2f} 倍　{c["burden"]:5.2f}%　{c["band"]}'
              + ('　★樣本數未達 100 戶' if c['thin'] else ''))
    print('  最低：' + '、'.join(f'{c["name"]} {c["pir"]}' for c in live[-3:]))
    thin = [c['name'] for c in live if c['thin']]
    if thin:
        print(f'  樣本數未達 100 戶：{"、".join(thin)}')


if __name__ == '__main__':
    main()
