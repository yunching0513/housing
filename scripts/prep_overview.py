#!/usr/bin/env python3
"""Pull the headline number out of each page's dataset for the overview.

The overview page states a figure for every page it links to. Reading them from
the same JSONs the pages use means the front door cannot drift out of step with
what is behind it — the alternative is prose with numbers typed in by hand, which
goes stale the first time a source is updated and nobody notices.

Run after the other prep scripts:

    python3 scripts/prep_overview.py
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / 'data'
OUT = D / 'tw_overview.json'


def load(name):
    p = D / name
    if not p.exists():
        sys.exit(f'缺少 {p.relative_to(ROOT)}，請先跑對應的 prep 腳本')
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    hou = load('tw_housing.json')
    pop = load('tw_population.json')
    town = load('tw_town_data.json')
    moi = load('tw_moi_series.json')
    soc = load('tw_social_housing.json')
    aff = load('tw_affordability.json')
    pser = load('tw_pop_series.json')
    sig = load('tw_signal.json')
    prof = load('tw_county_profile.json')

    n_hou, n_moi = hou['national'], moi['national']
    last = len(moi['periods']) - 1
    i09 = next(i for i, p in enumerate(moi['periods']) if p['short'] == '109H2')
    age0 = n_moi['byAge'][0]['rates']

    # metro.html 只畫六都與新竹縣市，所以它的「內部差距最大」也只能在這 8 個裡取，
    # 否則首頁會報一個那一頁上根本不存在的縣市。
    METRO = {'新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '新竹縣', '新竹市'}
    spread = max((c for c in prof['counties'] if c['spread'] and c['name'] in METRO),
                 key=lambda c: c['spread'])

    # priority.html 的兩組名次跟 prep_profile 的方向不同：那一頁的「房子夠不夠」是
    # 空屋率低者為第 1（缺房優先），而 profile 的 rank.vacancy 是高者為第 1，
    # 而且母體是有負擔能力資料的 21 個縣市而非 22 個。照它自己的定義重算一次，
    # 首頁報的數字才會跟點進去看到的一致。
    live = [c for c in prof['counties'] if c['pir'] is not None]
    r_vac = {c['name']: i + 1 for i, c in enumerate(sorted(live, key=lambda c: c['vacancy']))}
    r_pir = {c['name']: i + 1 for i, c in enumerate(sorted(live, key=lambda c: -c['pir']))}
    gapped = max(live, key=lambda c: abs(r_vac[c['name']] - r_pir[c['name']]))
    gap_vac, gap_pir = r_vac[gapped['name']], r_pir[gapped['name']]
    towns = sig['towns']
    inflow = max(towns, key=lambda t: t['dayWork'] - t['nightWork'])
    outflow = min(towns, key=lambda t: t['dayWork'] - t['nightWork'])
    tao = next(c for c in soc['counties'] if c['name'] == '桃園市')

    pages = [
        {'file': 'index.html', 'title': '臺灣住宅供需圖', 'unit': '22 縣市',
         'asks': '人在哪、房子在哪，對得上嗎',
         'says': f"全國 {n_hou['houses']:,} 宅對 {n_hou['households']:,} 戶，"
                 f"空屋率 {n_hou['vacancy']}%",
         'note': '分型用散布圖不用四色地圖：22 個縣市有 5 個離分界不到 0.5 個百分點'},
        {'file': 'town.html', 'title': '臺灣空屋地圖', 'unit': '368 鄉鎮市區',
         'asks': '空屋這麼多，為什麼還要蓋社宅',
         'says': f"空屋 {n_hou['idle']:,} 宅，但空屋率最高的是新屋與小宅，"
                 f"不是老屋",
         'note': '圖資畫得出 366 個，那瑪夏區與烏坵鄉沒有對應範圍'},
        {'file': 'metro.html', 'title': '六都與新竹的內部落差', 'unit': '174 鄉鎮市區',
         'asks': '縣市平均值掩蓋了什麼',
         'says': f"{spread['name']}內部最高區是最低區的 {spread['spread']} 倍"
                 f"（{spread['townMinName']} {spread['townMin']}% → "
                 f"{spread['townMaxName']} {spread['townMax']}%）",
         'note': '這 174 區裝了全國 75.4% 的住宅'},
        {'file': 'trend.html', 'title': '空屋率的十六年', 'unit': '22 縣市 ＋ 174 行政區',
         'asks': '空屋率正在往哪走',
         'says': f"全國五年只 {n_moi['rates'][last] - n_moi['rates'][i09]:+.2f} 個百分點，"
                 f"底下卻是 13 升 9 降",
         'note': f"新屋（5 年以下）一年由 {age0[0]}% 降到 {age0[2]}%"},
        {'file': 'social.html', 'title': '包租代管在哪裡', 'unit': '22 縣市（19 有辦）',
         'asks': '用既有房子的那半邊政策，落在哪',
         'says': f"累計媒合 {soc['national']['matched']:,} 戶，"
                 f"其中 {tao['matched'] / soc['national']['matched'] * 100:.1f}% 在桃園市",
         'note': f"仍有效的契約只有 {soc['national']['live']:,} 戶"
                 f"（{soc['national']['liveShare']}%）"},
        {'file': 'priority.html', 'title': '先蓋在哪裡', 'unit': '22 縣市（21 有負擔資料）',
         'asks': '用哪個標準決定優先序',
         'says': f"{gapped['name']}在「房子夠不夠」排第 {gap_vac}、"
                 f"在「買不買得起」排第 {gap_pir}，"
                 f"差 {abs(gap_vac - gap_pir)} 個名次",
         'note': '建議：人口當門檻、負擔能力當排序、空屋率當工具選擇'},
        {'file': 'signal.html', 'title': '白天的臺灣，晚上的臺灣', 'unit': '368 鄉鎮市區',
         'asks': '人白天在哪、晚上在哪',
         'says': f"{inflow['county']}{inflow['name']}白天多 "
                 f"{inflow['dayWork'] - inflow['nightWork']:,} 人，"
                 f"{outflow['county']}{outflow['name']}少 "
                 f"{abs(outflow['dayWork'] - outflow['nightWork']):,} 人",
         'note': '日夜比與空屋率幾乎不相關（r=0.06），不能單獨拿來選址'},
        {'file': 'county.html', 'title': '縣市檔案', 'unit': '22 縣市',
         'asks': '這一個縣市到底怎麼樣',
         'says': '選一個縣市，七份資料一次看完，每個數字附 22 縣市名次',
         'note': '合併的代價是期別不一致，頁面上逐項標注'},
    ]

    sources = [
        {'name': '人口及住宅普查', 'org': '主計總處', 'period': '109 年 11 月',
         'unit': '鄉鎮市區', 'have': True, 'use': '結構分析的基準，所有比率的分母'},
        {'name': '歷次各市縣常住人口', 'org': '主計總處',
         'period': f"45–{pser['years'][-1]} 年", 'unit': '縣市', 'have': True,
         'use': '人口趨勢；全國高點就是 109 年'},
        {'name': '低度使用（用電）住宅', 'org': '內政部',
         'period': f"98–{moi['periods'][last]['label']}", 'unit': '縣市＋六都新竹行政區',
         'have': True, 'use': '空屋的官方指標，唯一的長期數列'},
        {'name': '包租代管執行情形', 'org': '國土署', 'period': soc['asOf'],
         'unit': '縣市', 'have': True, 'use': '用既有住宅那半邊的政策投入'},
        {'name': '房價負擔能力指標', 'org': '內政部', 'period': aff['period'],
         'unit': '縣市', 'have': True, 'use': '買不買得起；優先序的排序依據'},
        {'name': '電信信令人口', 'org': 'SEGIS', 'period': sig['period'],
         'unit': '鄉鎮市區', 'have': True, 'use': '實際停留人口與日夜差'},
        {'name': '社宅直接興建進度', 'org': '國土署', 'period': '—', 'unit': '縣市',
         'have': False, 'use': '覆蓋率分子的另一半。站台擋機房 IP，需在一般網路環境下載'},
        {'name': '租金水準', 'org': '內政部', 'period': '—', 'unit': '縣市',
         'have': False, 'use': '社宅是租賃政策，租金所得比才是最貼題的負擔指標'},
    ]

    reading = [
        {'h': '兩種空屋不要混用',
         'p': f"普查問住戶「現在有沒有在用」，得到 {n_hou['vacancy']}%；"
              f"內政部看電表每月 60 度以下，得到 {n_moi['rates'][last]}%。"
              '兩者在極端一致、中段分歧，等級相關只有 0.50，不要相減。'},
        {'h': '期別不一致是合併的代價',
         'p': '七份資料橫跨 109 到 115 年。同一份資料內的比較安全，跨資料比較要先看期別；'
              '每一頁都標了自己的資料期。'},
        {'h': '名次不等於好壞',
         'p': '空屋率第 1 名是空屋率最高，不是最好。包租代管第 1 名是辦最多，'
              '不代表辦得最對——那要看它有沒有落在需要的地方。'},
        {'h': '信令數的是手機不是人',
         'p': '一人兩支手機是兩個人，沒有手機的小孩與長輩是零個人。'
              f"桃園大園區的信令夜間人口是普查常住的 2.73 倍，因為那裡是機場。"},
        {'h': '分界線附近不要當硬結論',
         'p': '四分型只差一個空屋率門檻。新北市離全國分界 0.04 個百分點，'
              '換一個空屋定義就會翻面，換一個標準會換一批縣市。'},
    ]

    data = {
        'built': {'pages': len(pages), 'counties': len(prof['counties']),
                  'towns': len(town['towns']), 'sources': sum(1 for s in sources if s['have'])},
        'headline': {
            'houses': n_hou['houses'], 'households': n_hou['households'],
            'idle': n_hou['idle'], 'vacancy': n_hou['vacancy'],
            'moiNow': n_moi['rates'][last], 'moiLabel': moi['periods'][last]['label'],
            'shMatched': soc['national']['matched'], 'shLive': soc['national']['live'],
            'pir': aff['national']['pir'], 'burden': aff['national']['burden'],
            'popPeak': pser['national'][pser['baseIndex']],
            'popNow': pser['national'][-1], 'popYear': pser['years'][-1],
            'pct': pop['totals']['pct'],
        },
        'pages': pages, 'sources': sources, 'reading': reading,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')
    print(f'{OUT.relative_to(ROOT)}：{len(pages)} 頁、{len(sources)} 份來源'
          f'（{data["built"]["sources"]} 份在手）')
    for p in pages:
        print(f'  {p["file"]:15s}{p["says"]}')


if __name__ == '__main__':
    main()
