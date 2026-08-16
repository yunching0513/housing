#!/usr/bin/env python3
"""Cross-check the census vacancy rate against 內政部's electricity-based figures.

The two are different concepts measured different ways, so they will never match.
The point of this script is to quantify *how* they differ, county by county, so the
pages can state it rather than hand-wave. Run it after prep_housing.py.

內政部 figures are transcribed from《低度使用(用電)住宅、待售新成屋統計資訊簡冊》
115 年 7 月出刊，表 3（資料期 114 年下半年）. They are typed in here rather than
scraped because the source is a PDF whose fonts carry no usable text mapping.

    python3 scripts/verify_vacancy.py
"""
import json, pathlib, statistics

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 表3：114 年下半年各縣市低度使用(用電)住宅比率（%）。全國 9.44%。
MOI_114H2 = {
    '新北市': 6.84, '臺北市': 6.39, '桃園市': 8.53, '臺中市': 8.58, '臺南市': 10.92,
    '高雄市': 10.30, '宜蘭縣': 14.50, '新竹縣': 8.70, '苗栗縣': 11.26, '彰化縣': 11.01,
    '南投縣': 12.79, '雲林縣': 14.09, '嘉義縣': 14.28, '屏東縣': 11.80, '臺東縣': 15.47,
    '花蓮縣': 13.95, '澎湖縣': 14.62, '基隆市': 11.56, '新竹市': 7.79, '嘉義市': 11.79,
    '金門縣': 16.23, '連江縣': 13.02,
}
MOI_NATIONAL = 9.44

# 附錄二：109 年逐筆比對結果（僅比對成功者）。四格合計 100%。
CROSSTAB = {
    ('空閒', '低度使用'): 6.71, ('空閒', '非低度使用'): 13.13,
    ('非空閒', '低度使用'): 2.80, ('非空閒', '非低度使用'): 77.37,
}


def spearman(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos
        return r
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    hou = json.loads((ROOT / 'data' / 'tw_housing.json').read_text(encoding='utf-8'))
    census = {c['name']: c['vacancy'] for c in hou['counties']}

    rows = [(n, census[n], MOI_114H2[n]) for n in MOI_114H2]
    by_moi = {n: i + 1 for i, (n, _, _) in enumerate(sorted(rows, key=lambda r: -r[2]))}
    by_cen = {n: i + 1 for i, (n, _, _) in enumerate(sorted(rows, key=lambda r: -r[1]))}
    rows.sort(key=lambda r: -r[2])

    print('普查空屋率（109 年 11 月，目前沒有使用） vs 低度使用用電住宅率（114 年下半年）\n')
    print(f"{'縣市':6s}{'普查':>9s}{'用電':>9s}{'差':>8s}{'普查名次':>9s}{'用電名次':>9s}")
    for n, c, m in rows:
        print(f'{n:6s}{c:>8.1f}%{m:>8.2f}%{c - m:>+8.1f}{by_cen[n]:>9d}{by_moi[n]:>9d}')

    a = [r[1] for r in rows]
    b = [r[2] for r in rows]
    print(f'\n全國：普查 {hou["national"]["vacancy"]}%　用電 {MOI_NATIONAL}%'
          f'　差 {hou["national"]["vacancy"] - MOI_NATIONAL:+.2f} 個百分點')
    print(f'縣市平均：普查 {statistics.mean(a):.2f}%　用電 {statistics.mean(b):.2f}%')
    print(f'Spearman 等級相關：{spearman(a, b):.3f}')

    gaps = sorted(rows, key=lambda r: -(r[1] - r[2]))[:5]
    print('\n差距最大的五個縣市（普查高於用電）：')
    for n, c, m in gaps:
        print(f'  {n:6s}{c - m:+5.1f} 個百分點　普查第 {by_cen[n]} 名 / 用電第 {by_moi[n]} 名')

    # The published 84.08% agreement is dominated by the both-negative cell.
    both = CROSSTAB[('空閒', '低度使用')]
    only_census = CROSSTAB[('空閒', '非低度使用')]
    only_power = CROSSTAB[('非空閒', '低度使用')]
    neither = CROSSTAB[('非空閒', '非低度使用')]
    print(f'\n109 年逐筆比對（官方附錄二）：')
    print(f'  官方公布一致率　　　　　　{both + neither:.2f}%')
    print(f'  其中「兩者都不是空屋」　　{neither:.2f}%　← 一致率的絕大部分')
    print(f'  普查空閒住宅合計　　　　　{both + only_census:.2f}%')
    print(f'  用電低度使用合計　　　　　{both + only_power:.2f}%')
    print(f'  空閒住宅中同時是低度使用　{both / (both + only_census) * 100:.1f}%')
    print(f'  低度使用中同時是空閒住宅　{both / (both + only_power) * 100:.1f}%')


if __name__ == '__main__':
    main()
