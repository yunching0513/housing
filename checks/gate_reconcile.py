"""閘門 ③｜對帳可控：各份中間檔彼此說的話一不一致。

分工說清楚：
  各支 prep_*.py 負責跟**原始表的小計列**對帳，對不上就中止，那是第一道。
  這一道檢查的是**產出之間**：全國等不等於各縣市加總、22 個縣市名是不是同一組、
  368 個鄉鎮市區在兩份資料裡是不是同一批、首頁講的數字跟它引用的檔案一不一樣。

它在擋什麼：
  單獨看每一份檔案都合格，合起來卻對不上。這種錯不會有任何一支程式報錯，
  只會在頁面上安靜地出現兩個不同的全國數字。

怎麼自己跑：  python3 checks/gate_reconcile.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'


def load(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def close(a, b, tol, why, problems):
    if a is None or b is None:
        problems.append(f'{why}：有一邊是 null（{a} vs {b}）')
    elif abs(a - b) > tol:
        problems.append(f'{why}：{a:,} vs {b:,}，差 {abs(a - b):,.4g}（容差 {tol}）')


def run():
    problems = []
    try:
        hou, town, pop = load('tw_housing.json'), load('tw_town_data.json'), load('tw_population.json')
        moi, soc, bld = load('tw_moi_series.json'), load('tw_social_housing.json'), load('tw_social_build.json')
        aff, pser, sig = load('tw_affordability.json'), load('tw_pop_series.json'), load('tw_signal.json')
        prof, rent, ov = load('tw_county_profile.json'), load('tw_rent.json'), load('tw_overview.json')
        geo, tgeo = load('tw_counties.json'), load('tw_towns.json')
    except FileNotFoundError as exc:
        return [f'缺檔案：{exc}']

    # ── 全國 = 各縣市加總 ──
    for key in ('houses', 'households', 'idle'):
        close(hou['national'][key], sum(c[key] for c in hou['counties']), 0,
              f'tw_housing 的全國 {key} 與 22 縣市加總', problems)
    close(hou['national']['vacancy'],
          hou['national']['idle'] / hou['national']['houses'] * 100, 0.01,
          'tw_housing 的全國空屋率與 idle/houses 算出來的', problems)
    for key in ('houses', 'households', 'idle'):
        close(town['national'][key], sum(t[key] for t in town['towns']), 0,
              f'tw_town_data 的全國 {key} 與 368 鄉鎮市區加總', problems)
    for key in ('houses', 'households', 'idle'):
        close(hou['national'][key], town['national'][key], 0,
              f'普查縣市檔與鄉鎮市區檔的全國 {key}', problems)
    # 未開辦的縣市是 null 而不是 0，加總時要挑掉；挑掉幾個也要對得上 notListed
    listed = [c for c in soc['counties'] if c['matched'] is not None]
    if len(listed) + len(soc['notListed']) != len(soc['counties']):
        problems.append(f'tw_social_housing 有 {len(soc["counties"]) - len(listed)} 個縣市沒有'
                        f'媒合數，但 notListed 只列了 {len(soc["notListed"])} 個')
    close(soc['national']['matched'], sum(c['matched'] for c in listed), 0,
          'tw_social_housing 的全國累計媒合與有開辦的縣市加總', problems)
    for stage in ('done', 'total'):
        close(bld['national']['total'][stage],
              sum(c['total'][stage] for c in bld['counties']), 0,
              f'tw_social_build 的全國 {stage} 與 22 縣市加總', problems)
    for side in ('central', 'local'):
        for stage in ('done', 'building', 'awaiting', 'planning', 'total'):
            close(bld['national'][side][stage],
                  sum(c[side][stage] for c in bld['counties']), 0,
                  f'tw_social_build 的全國 {side}.{stage} 與 22 縣市加總', problems)
    for stage in ('done', 'building', 'awaiting', 'planning', 'total'):
        close(bld['national']['total'][stage],
              bld['national']['central'][stage] + bld['national']['local'][stage], 0,
              f'tw_social_build 的全國 {stage}：中央＋地方是不是等於小計', problems)
    close(rent['national']['n'], sum(c['n'] for c in rent['counties']), 0,
          'tw_rent 的全國筆數與 22 縣市加總', problems)
    close(pser['national'][-1], sum(c['values'][-1] for c in pser['counties']),
          len(pser['counties']) * 500 + 500,
          'tw_pop_series 最新一年的全國人口與 22 縣市加總（來源以千人為單位，'
          '每個縣市最多差 500 人）', problems)

    # ── 22 個縣市名必須是同一組 ──
    base = {c['name'] for c in hou['counties']}
    if len(base) != 22:
        problems.append(f'普查的縣市數是 {len(base)} 個，不是 22 個')
    for label, names in (
            ('tw_population', {c['name'] for c in pop['counties']}),
            ('tw_moi_series', {c['name'] for c in moi['counties']}),
            ('tw_social_housing', {c['name'] for c in soc['counties']}),
            ('tw_social_build', {c['name'] for c in bld['counties']}),
            ('tw_affordability', {c['name'] for c in aff['counties']}),
            ('tw_pop_series', {c['name'] for c in pser['counties']}),
            ('tw_county_profile', {c['name'] for c in prof['counties']}),
            ('tw_rent', {c['name'] for c in rent['counties']}),
            ('tw_counties（圖形）', {c['name'] for c in geo['counties']})):
        if names != base:
            problems.append(f'{label} 的縣市名與普查對不上：'
                            f'多了 {sorted(names - base)}、少了 {sorted(base - names)}')

    # ── 368 個鄉鎮市區必須是同一批 ──
    tkeys = {t['key'] for t in town['towns']}
    if len(tkeys) != 368:
        problems.append(f'普查的鄉鎮市區是 {len(tkeys)} 個，不是 368 個')
    if {t['key'] for t in sig['towns']} != tkeys:
        problems.append('tw_signal 的鄉鎮市區與普查對不上')
    missing_geo = tkeys - {t['key'] for t in tgeo['towns']}
    if len(missing_geo) != 2:
        problems.append(f'圖資缺的鄉鎮市區從 2 個變成 {len(missing_geo)} 個：'
                        f'{sorted(missing_geo)}（原本只缺那瑪夏區與烏坵鄉）')
    rent_keys = {(t['county'], t['name']) for t in rent['towns']}
    census_keys = {(t['county'], t['name']) for t in town['towns']}
    if rent_keys - census_keys:
        problems.append(f'tw_rent 有普查沒有的鄉鎮市區：{sorted(rent_keys - census_keys)}')

    # ── 數列長度 ──
    n_period = len(moi['periods'])
    for label, rows in (('national', [moi['national']]), ('counties', moi['counties'])):
        for r in rows:
            if len(r['rates']) != n_period:
                problems.append(f'tw_moi_series 的 {label} 數列長度 {len(r["rates"])} '
                                f'不等於期別數 {n_period}')
                break
    for c in pser['counties']:
        if len(c['values']) != len(pser['years']):
            problems.append(f'tw_pop_series 的 {c["name"]} 數列長度與年份數對不上')
            break
    for c in rent['counties']:
        if len(c['series']) != len(rent['years']):
            problems.append(f'tw_rent 的 {c["name"]} 數列長度與年份數對不上')
            break

    # ── 首頁講的數字，必須跟它引用的那份檔案一樣 ──
    h = ov['headline']
    close(h['houses'], hou['national']['houses'], 0, '首頁的住宅總數與普查', problems)
    close(h['households'], hou['national']['households'], 0, '首頁的家戶數與普查', problems)
    close(h['idle'], hou['national']['idle'], 0, '首頁的空屋數與普查', problems)
    close(h['vacancy'], hou['national']['vacancy'], 0, '首頁的空屋率與普查', problems)
    close(h['moiNow'], moi['national']['rates'][-1], 0, '首頁的用電空屋率與內政部數列', problems)
    close(h['shMatched'], soc['national']['matched'], 0, '首頁的累計媒合與包租代管檔', problems)
    close(h['shLive'], soc['national']['live'], 0, '首頁的有效契約與包租代管檔', problems)
    close(h['pir'], aff['national']['pir'], 0, '首頁的房價所得比與負擔能力檔', problems)
    close(h['popNow'], pser['national'][-1], 0, '首頁的最新人口與常住人口數列', problems)
    if ov['built']['pages'] != len(ov['pages']):
        problems.append('首頁自稱的頁數與它列出來的頁數不一樣')
    if ov['built']['counties'] != len(prof['counties']):
        problems.append('首頁自稱的縣市數與縣市檔案不一樣')
    if ov['built']['towns'] != len(town['towns']):
        problems.append('首頁自稱的鄉鎮市區數與普查不一樣')

    # ── 比率不能超出物理上可能的範圍 ──
    for c in hou['counties']:
        if not 0 <= c['vacancy'] <= 100:
            problems.append(f'{c["name"]} 的空屋率 {c["vacancy"]} 不在 0-100 之間')
    for c in rent['counties']:
        if c['n'] and c['rent'] is not None and c['rent'] <= 0:
            problems.append(f'{c["name"]} 的租金中位數是 {c["rent"]}')
    return problems


HINT = ('對不上就回去修產出資料的那支 prep 程式，不要放寬這裡的容差。'
        '容差每放寬一次，下一次真的算錯就抓不到了。')

if __name__ == '__main__':
    found = run()
    if found:
        print('閘門 ③ 對帳可控：✗')
        for line in found:
            print('   ', line)
        print('   提示：', HINT)
        raise SystemExit(1)
    print('閘門 ③ 對帳可控：✓')
