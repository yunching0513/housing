#!/usr/bin/env python3
"""Simplify the g0v twCounty2010 GeoJSON into a compact payload for the artifact.

Steps: drop negligible islands, Douglas-Peucker simplify, round coordinates,
and tag Kinmen / Matsu so the page can draw them as magnified insets.
"""
import json, math

SRC = 'twCounty2010.geo.json'
OUT = 'tw_counties.json'

# Rename the source's 台 spellings to the official 臺 used by the DGBAS tables,
# and carry the 2010 桃園縣 -> 桃園市 upgrade.
RENAME = {
    '台東縣': '臺東縣', '台北市': '臺北市', '台中市': '臺中市',
    '台南市': '臺南市', '桃園縣': '桃園市',
}
GROUP = {'金門縣': 'kinmen', '連江縣': 'matsu'}

# km^2 floor for keeping an island. 0.15 keeps 蘭嶼/綠島/小琉球/龜山島, the
# inhabited 澎湖 and 馬祖 islands, and 烈嶼; it drops bare rocks and sandbars.
MIN_AREA_KM2 = 0.15
DEG2_TO_KM2 = 111.32 * 111.32  # scaled by cos(lat) below


def ring_area_km2(ring):
    """Shoelace area in km^2, with longitude degrees shrunk by cos(mean lat)."""
    if len(ring) < 4:
        return 0.0
    lat0 = sum(p[1] for p in ring) / len(ring)
    k = math.cos(math.radians(lat0))
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0 * DEG2_TO_KM2 * k


def perp2(p, a, b):
    """Squared perpendicular distance from p to segment ab, in degree units."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return (px - ax) ** 2 + (py - ay) ** 2
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def simplify(ring, eps):
    """Iterative Douglas-Peucker (recursion would blow the stack on 40k-point rings)."""
    if len(ring) < 4:
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
            stack.append((i, bi))
            stack.append((bi, j))
    out = [p for p, k in zip(ring, keep) if k]
    # A degenerate ring is worse than no ring at all.
    return out if len(out) >= 4 else ring[:: max(1, len(ring) // 8)] + [ring[0]]


def polygons(geom):
    return [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']


def main():
    src = json.load(open(SRC))
    counties, dropped = [], 0

    for feat in src['features']:
        raw = feat['properties']['name']
        name = RENAME.get(raw, raw)
        group = GROUP.get(name, 'main')
        # Insets are drawn ~5x larger, so they need a finer tolerance to stay crisp.
        eps = 0.00035 if group != 'main' else 0.0013

        kept = []
        for poly in polygons(feat['geometry']):
            outer = poly[0]  # holes are irrelevant at this scale
            area = ring_area_km2(outer)
            if area < MIN_AREA_KM2:
                dropped += 1
                continue
            ring = simplify(outer, eps)
            kept.append((area, [[round(x, 4), round(y, 4)] for x, y in ring]))

        if not kept:  # never let a county vanish
            biggest = max(
                (p[0] for p in polygons(feat['geometry'])),
                key=ring_area_km2,
            )
            kept = [(0.0, [[round(x, 4), round(y, 4)] for x, y in simplify(biggest, eps)])]

        kept.sort(key=lambda t: -t[0])
        counties.append({'name': name, 'group': group, 'rings': [r for _, r in kept]})

    bounds = {}
    for c in counties:
        g = c['group']
        b = bounds.setdefault(g, [180.0, 90.0, -180.0, -90.0])
        for ring in c['rings']:
            for x, y in ring:
                b[0] = min(b[0], x); b[1] = min(b[1], y)
                b[2] = max(b[2], x); b[3] = max(b[3], y)

    payload = {'bounds': bounds, 'counties': counties}
    json.dump(payload, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))

    pts = sum(len(r) for c in counties for r in c['rings'])
    rings = sum(len(c['rings']) for c in counties)
    import os
    print(f'counties={len(counties)} rings={rings} points={pts} dropped_rings={dropped}')
    print(f'{OUT}: {os.path.getsize(OUT)/1024:.1f} KB')
    for g, b in bounds.items():
        print(f'  {g}: lon[{b[0]:.3f},{b[2]:.3f}] lat[{b[1]:.3f},{b[3]:.3f}]')
    for c in sorted(counties, key=lambda c: -len(c['rings']))[:6]:
        print(f'  {c["name"]}: {len(c["rings"])} rings, {sum(len(r) for r in c["rings"])} pts')


if __name__ == '__main__':
    main()
