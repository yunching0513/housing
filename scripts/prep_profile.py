#!/usr/bin/env python3
"""Merge every county-level dataset into one record per county.

Seven pages now each hold a slice of the same 22 counties. Anyone asking a
practical question — 「宜蘭到底怎麼樣」 — has to open all seven and hold the
answer in their head. This builds the other view: one county, everything known
about it, with its rank among the 22 on each measure so a number means something
without having to remember the other 21.

Reads what the other prep scripts already produced, so run it last:

    python3 scripts/prep_profile.py
"""
import json, pathlib, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / 'data'
OUT = D / 'tw_county_profile.json'

METRO = {'新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '新竹縣', '新竹市'}


def load(name):
    p = D / name
    if not p.exists():
        sys.exit(f'缺少 {p.relative_to(ROOT)}，請先跑對應的 prep 腳本')
    return json.loads(p.read_text(encoding='utf-8'))


def ranks(rows, key, high_is_first=True):
    """Rank 1 .. n over the counties that have a value; None stays None.

    Ties share the lower rank, the way a league table does, so two counties on
    9.21 are both 5th and nobody is 6th.
    """
    have = [r for r in rows if r.get(key) is not None]
    have.sort(key=lambda r: r[key], reverse=high_is_first)
    out, prev, prev_rank = {}, object(), 0
    for i, r in enumerate(have, 1):
        if r[key] != prev:
            prev, prev_rank = r[key], i
        out[r['name']] = prev_rank
    return out, len(have)


def main():
    pop = load('tw_population.json')
    hou = load('tw_housing.json')
    moi = load('tw_moi_series.json')
    soc = load('tw_social_housing.json')
    aff = load('tw_affordability.json')
    pser = load('tw_pop_series.json')
    town = load('tw_town_data.json')
    sig = load('tw_signal.json')
    bld = load('tw_social_build.json')

    P = {c['name']: c for c in pop['counties']}
    H = {c['name']: c for c in hou['counties']}
    M = {c['name']: c for c in moi['counties']}
    S = {c['name']: c for c in soc['counties']}
    A = {c['name']: c for c in aff['counties']}
    Y = {c['name']: c for c in pser['counties']}
    B = {c['name']: c for c in bld['counties']}
    names = [c['name'] for c in hou['counties']]

    i09 = next(i for i, p in enumerate(moi['periods']) if p['short'] == '109H2')
    last = len(moi['periods']) - 1

    # Township-level data rolled up: the internal spread is the whole point of
    # the metro page, and it is a property of the county, not of any township.
    by_county = {}
    for t in town['towns']:
        by_county.setdefault(t['county'], []).append(t)
    sig_by = {}
    for t in sig['towns']:
        s = sig_by.setdefault(t['county'], {'night': 0, 'day': 0, 'n': 0})
        s['night'] += t['nightWork']; s['day'] += t['dayWork']; s['n'] += 1

    rows = []
    for n in names:
        h, m, a, s, y, b = H[n], M[n], A[n], S[n], Y[n], B[n]
        ts = sorted(by_county.get(n, []), key=lambda t: t['vacancy'])
        sg = sig_by.get(n)
        rows.append({
            'name': n, 'region': P[n].get('region'),
            'quadrant': h['quadrant'], 'margin': h.get('margin'),

            # 人口
            'p99': P[n]['p99'], 'p109': P[n]['p109'], 'pct': P[n]['pct'],
            'delta': P[n]['delta'], 'density': P[n]['density109'],
            'popSeries': y['values'], 'since109Pct': y['since109Pct'],
            'peakYear': y['peakYear'],

            # 住宅（普查 109/11）
            'houses': h['houses'], 'households': h['households'],
            'idle': h['idle'], 'vacancy': h['vacancy'],
            'perHousehold': h['perHousehold'],

            # 低度使用（用電）23 期
            'moiSeries': m['rates'],
            'moiNow': m['rates'][last], 'moi109': m['rates'][i09],
            'moiChange': round(m['rates'][last] - m['rates'][i09], 2),
            'moiCount': m['countRecent'][-1],

            # 包租代管：19 個縣市有辦，其餘為 None 而不是 0
            'shMatched': s['matched'], 'shPer1000': s['per1000'], 'shLatest': s['latest'],

            # 社宅直接興建：已完工是「現在住得進去的」，總計含規劃中所以是承諾不是存量
            'shbDone': b['total']['done'], 'shbBuilding': b['total']['building'],
            'shbAwarded': b['total']['awarded'], 'shbPlanning': b['total']['planning'],
            'shbTotal': b['total']['total'],
            'shbDonePer1000': b['donePer1000'], 'shbTotalPer1000': b['totalPer1000'],
            'shbCentralShare': b['centralShare'],

            # 負擔能力：連江縣未列，澎湖金門樣本不足
            'pir': a['pir'], 'burden': a['burden'], 'band': a['band'],
            'affThin': a.get('thin', False),

            # 鄉鎮市區內部差距
            'townCount': len(ts),
            'townMin': ts[0]['vacancy'] if ts else None,
            'townMax': ts[-1]['vacancy'] if ts else None,
            'townMinName': ts[0]['name'] if ts else None,
            'townMaxName': ts[-1]['name'] if ts else None,
            'spread': round(ts[-1]['vacancy'] / ts[0]['vacancy'], 2) if ts and ts[0]['vacancy'] else None,
            'hasDistricts': n in METRO,

            # 電信信令 112/11，由鄉鎮市區加總
            'sigNight': sg['night'] if sg else None,
            'sigDay': sg['day'] if sg else None,
            'sigRatio': round(sg['day'] / sg['night'], 3) if sg else None,
        })

    # Rank on the measures where a rank actually helps a reader. The direction is
    # "1 = the end a housing policy reader would look at first", stated per row.
    RANKED = [
        ('vacancy', True, '空屋率高'), ('perHousehold', True, '宅戶比高'),
        ('pct', True, '十年人口成長高'), ('since109Pct', True, '109→115 成長高'),
        ('density', True, '人口密度高'), ('houses', True, '住宅存量大'),
        ('moiNow', True, '低度使用率高'), ('moiChange', True, '低度使用上升多'),
        ('pir', True, '房價所得比高'), ('burden', True, '房貸負擔率高'),
        ('shPer1000', True, '包租代管每千家戶多'), ('shMatched', True, '包租代管累計多'),
        ('shbDonePer1000', True, '社宅已完工每千家戶多'),
        ('shbTotalPer1000', True, '社宅總計每千家戶多'),
        ('spread', True, '內部差距大'), ('sigRatio', True, '白天淨流入多'),
    ]
    rank_meta = {}
    for key, desc, label in RANKED:
        r, n_have = ranks(rows, key, desc)
        rank_meta[key] = {'label': label, 'of': n_have}
        for row in rows:
            row.setdefault('rank', {})[key] = r.get(row['name'])

    nat = {
        'vacancy': hou['national']['vacancy'],
        'perHousehold': hou['national']['perHousehold'],
        'houses': hou['national']['houses'],
        'households': hou['national']['households'],
        'idle': hou['national']['idle'],
        'pct': pop['totals']['pct'],
        'moiSeries': moi['national']['rates'],
        'moiNow': moi['national']['rates'][last],
        'moi109': moi['national']['rates'][i09],
        'pir': aff['national']['pir'], 'burden': aff['national']['burden'],
        'band': aff['national']['band'],
        'shPer1000': soc['national']['per1000'], 'shMatched': soc['national']['matched'],
        'shbDone': bld['national']['total']['done'],
        'shbTotal': bld['national']['total']['total'],
        'shbDonePer1000': bld['national']['donePer1000'],
        'shbTotalPer1000': bld['national']['totalPer1000'],
        'shbCentralShare': bld['national']['centralShare'],
        'shLive': soc['national']['live'], 'shLiveShare': soc['national']['liveShare'],
        'popSeries': pser['national'],
        'sigRatio': round(sig['national']['dayWork'] / sig['national']['nightWork'], 3),
        'density': round(pop['totals']['p109'] / 36197, 1),
    }

    data = {
        'periods': {
            'census': '民國 109 年 11 月', 'moi': moi['periods'][last]['label'],
            'social': soc['asOf'], 'build': bld['asOf'], 'afford': aff['period'],
            'signal': sig['period'], 'pop': f"{pser['years'][-1]} 年",
        },
        'moiPeriods': [p['short'] for p in moi['periods']],
        'moiMethods': [p['method'] for p in moi['periods']],
        'popYears': pser['years'],
        'quadrants': hou['quadrants'],
        'rankMeta': rank_meta,
        'national': nat,
        'counties': rows,
        'notes': {
            'social': soc['notListed'],
            'afford': aff['notListed'],
            'affordThin': [c['name'] for c in aff['counties'] if c.get('thin')],
        },
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    kb = len(OUT.read_bytes()) / 1024
    print(f'{OUT.relative_to(ROOT)}：{len(rows)} 縣市 × {len(RANKED)} 項排名，{kb:.0f} KB')
    print(f'  未辦包租代管：{"、".join(data["notes"]["social"]) or "無"}')
    print(f'  無負擔能力資料：{"、".join(data["notes"]["afford"]) or "無"}'
          f'　樣本不足：{"、".join(data["notes"]["affordThin"]) or "無"}')
    sp = [r for r in rows if r['spread']]
    print(f'  內部差距最大：' + '、'.join(
        f'{r["name"]} {r["spread"]}倍' for r in sorted(sp, key=lambda r: -r['spread'])[:3]))
    print(f'  全國中位空屋率 {statistics.median(r["vacancy"] for r in rows):.2f}%')


if __name__ == '__main__':
    main()
