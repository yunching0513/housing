#!/usr/bin/env python3
"""Simplify the township boundaries into a payload the page can embed.

Source is g0v twgeojson's town file (20 MB, 377 features). Three fixes are needed
before it lines up with the 109 年 census:

  * Names predate 桃園 2014 年升格, so its 市/鎮/鄉 all become 區; 員林鎮 and 頭份鎮
    likewise became 市.
  * Nine features are sea areas split off from their township, e.g. 「基隆市中山區(海)」.
    They are merged back into the parent rather than drawn as separate units.
  * 台 is normalised to 臺 throughout.

Two townships have no geometry in the source at all — 高雄市那瑪夏區 and 金門縣烏坵鄉.
They are reported here and flagged on the page rather than silently dropped.

    python3 scripts/prep_town_geo.py
"""
import json, math, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'sources' / 'twTown1982.geo.json'
OUT = ROOT / 'data' / 'tw_towns.json'

MIN_AREA_KM2 = 0.4      # coarser than the county map: 368 units need a smaller payload
EPS = 0.0009            # Douglas-Peucker tolerance in degrees (~100 m)
DEG2_TO_KM2 = 111.32 * 111.32
SEA = re.compile(r'\((海|海區)\)?$')
RENAME_TOWN = {'彰化縣/員林鎮': '員林市', '苗栗縣/頭份鎮': '頭份市'}
# The 2010 reform turned every 市/鎮/鄉 in these five into a 區. Land features already
# carry the new names; only the split-off sea blocks still use the old ones.
UPGRADED = {'新北市', '臺中市', '臺南市', '高雄市', '桃園市'}
# 釣魚臺列嶼 is administratively 宜蘭縣頭城鎮 but sits in 基隆市中正區 in this source and
# reaches 123.7°E. Keeping it would add 1.7° of empty ocean and shrink the island to
# nothing, so it is excluded from the drawn extent.
EAST_LIMIT = 122.2


def norm_county(name):
    name = name.replace('台', '臺')
    return '桃園市' if name == '桃園縣' else name


def norm_town(county, town):
    town = SEA.sub('', town).replace('台', '臺')
    key = f'{county}/{town}'
    if key in RENAME_TOWN:
        return RENAME_TOWN[key]
    if county in UPGRADED and town[-1] in '市鎮鄉':
        return town[:-1] + '區'
    return town


def ring_area_km2(ring):
    if len(ring) < 4:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    s = 0.0
    for i in range(len(ring) - 1):
        s += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return abs(s) / 2.0 * DEG2_TO_KM2 * math.cos(math.radians(lat0))


def perp2(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def simplify(ring, eps):
    if len(ring) < 5:
        return ring
    eps2 = eps * eps
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        best, bi = -1.0, -1
        for k in range(i + 1, j):
            d = perp2(ring[k], ring[i], ring[j])
            if d > best:
                best, bi = d, k
        if best > eps2:
            keep[bi] = True
            stack.append((i, bi)); stack.append((bi, j))
    out = [p for p, k in zip(ring, keep) if k]
    return out if len(out) >= 4 else ring[:: max(1, len(ring) // 6)] + [ring[0]]


def polygons(geom):
    return [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']


def main():
    if not SRC.exists():
        sys.exit(f'缺少{SRC}')
    src = json.loads(SRC.read_text(encoding='utf-8'))

    merged, dropped, sea_merges = {}, 0, 0
    for feat in src['features']:
        p = feat['properties']
        county = norm_county(p['COUNTYNAME'])
        raw = p['TOWNNAME']
        town = norm_town(county, raw)
        key = f'{county}/{town}'
        if SEA.search(raw):
            sea_merges += 1
        entry = merged.setdefault(key, {'county': county, 'town': town, 'rings': []})
        for poly in polygons(feat['geometry']):
            outer = poly[0]
            if ring_area_km2(outer) < MIN_AREA_KM2 or max(x for x, _ in outer) > EAST_LIMIT:
                dropped += 1
                continue
            entry['rings'].append([[round(x, 4), round(y, 4)] for x, y in simplify(outer, EPS)])

    towns = []
    for key, e in sorted(merged.items()):
        if not e['rings']:
            dropped += 1
            continue
        e['rings'].sort(key=lambda r: -ring_area_km2(r))
        towns.append({'key': key, 'county': e['county'], 'name': e['town'], 'rings': e['rings']})

    b = [180.0, 90.0, -180.0, -90.0]
    for t in towns:
        for ring in t['rings']:
            for x, y in ring:
                b[0] = min(b[0], x); b[1] = min(b[1], y)
                b[2] = max(b[2], x); b[3] = max(b[3], y)

    OUT.write_text(json.dumps({'bounds': b, 'towns': towns}, ensure_ascii=False,
                              separators=(',', ':')), encoding='utf-8')

    pts = sum(len(r) for t in towns for r in t['rings'])
    print(f'鄉鎮市區{len(towns)}個 ・ 環{sum(len(t["rings"]) for t in towns)} ・ 點{pts:,}')
    print(f'合併海域圖塊{sea_merges}個 ・ 移除小島礁{dropped}個')
    print(f'{OUT.name}: {OUT.stat().st_size / 1024:.0f} KB')
    print(f'範圍lon[{b[0]:.3f},{b[2]:.3f}] lat[{b[1]:.3f},{b[3]:.3f}]')

    census = ROOT / 'data' / 'town_census_keys.json'
    if census.exists():
        want = set(json.loads(census.read_text(encoding='utf-8')))
        have = {t['key'] for t in towns}
        if want - have:
            print(f'\n※ 普查有、圖資缺（{len(want - have)}）：{"、".join(sorted(want - have))}')
        if have - want:
            print(f'※ 圖資有、普查缺（{len(have - want)}）：{"、".join(sorted(have - want))}')


if __name__ == '__main__':
    main()
