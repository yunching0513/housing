#!/usr/bin/env python3
"""Join the 99 年 (CSV) and 109 年 (XML) resident-population tables by county.

The 99 年 table predates the 2010 縣市改制, so it lists 桃園縣 and carries
臺中/臺南/高雄 as parent rows whose children are the old 市 + 縣 pairs. Taking the
parent rows (and renaming 桃園縣) puts both years on the post-2010 22-unit basis.
"""
import csv, json, re, unicodedata
import xml.etree.ElementTree as ET

CSV_SRC = '/root/.claude/uploads/0693c904-86e7-5afb-a3e1-81b06106ef4a/5c9f3a05-99____.csv'
XML_SRC = '/root/.claude/uploads/0693c904-86e7-5afb-a3e1-81b06106ef4a/4e215391-109____.xml'
OUT = 'tw_population.json'

COUNTIES = [
    '新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市',
    '基隆市', '新竹市', '嘉義市',
    '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣',
    '嘉義縣', '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '金門縣', '連江縣',
]
REGION = {
    '臺北市': '北部', '新北市': '北部', '桃園市': '北部', '基隆市': '北部',
    '新竹市': '北部', '新竹縣': '北部', '宜蘭縣': '北部',
    '臺中市': '中部', '苗栗縣': '中部', '彰化縣': '中部', '南投縣': '中部', '雲林縣': '中部',
    '臺南市': '南部', '高雄市': '南部', '嘉義市': '南部', '嘉義縣': '南部',
    '屏東縣': '南部', '澎湖縣': '南部',
    '臺東縣': '東部', '花蓮縣': '東部',
    '金門縣': '金馬', '連江縣': '金馬',
}
EN = {
    '新北市': 'New Taipei', '臺北市': 'Taipei', '桃園市': 'Taoyuan', '臺中市': 'Taichung',
    '臺南市': 'Tainan', '高雄市': 'Kaohsiung', '基隆市': 'Keelung', '新竹市': 'Hsinchu City',
    '嘉義市': 'Chiayi City', '宜蘭縣': 'Yilan', '新竹縣': 'Hsinchu County', '苗栗縣': 'Miaoli',
    '彰化縣': 'Changhua', '南投縣': 'Nantou', '雲林縣': 'Yunlin', '嘉義縣': 'Chiayi County',
    '屏東縣': 'Pingtung', '臺東縣': 'Taitung', '花蓮縣': 'Hualien', '澎湖縣': 'Penghu',
    '金門縣': 'Kinmen', '連江縣': 'Lienchiang',
}


def norm(s):
    """Strip whitespace (incl. U+3000), unify 台 -> 臺, and drop the parenthetical
    former name the 99 年 table carries on 新北市(臺北縣)."""
    s = unicodedata.normalize('NFKC', s or '')
    s = re.sub(r'\s+', '', s).replace('台', '臺')
    return re.sub(r'\(.*?\)', '', s)


def num(s):
    s = (s or '').strip().replace(',', '')
    return float(s) if s else None


def read_csv_99():
    """99 年. Depth = leading whitespace; the parent 臺中/臺南/高雄 rows sit one
    level above their old 市/縣 children, so the shallower row is the merged total."""
    rows = {}
    with open(CSV_SRC, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            label = r['按縣市別分']
            depth = len(label) - len(label.lstrip(' 　'))
            name = norm(label)
            if name == '桃園縣':
                name = '桃園市'
            if name not in COUNTIES:
                continue
            # Keep the outermost occurrence: the post-merger total.
            if name in rows and depth >= rows[name]['depth']:
                continue
            rows[name] = {
                'depth': depth,
                'total': int(num(r['常住人口數_總計_人_Number_of_resident_population_Grand_total_person'])),
                'male': int(num(r['常住人口數_男_人_Number_of_resident_population_Male_person'])),
                'female': int(num(r['常住人口數_女_人_Number_of_resident_population_Female_person'])),
                'area': num(r['土地面積_平方公里_Total_land_area_km2']),
            }
    return rows


def read_xml_109():
    rows = {}
    for rec in ET.parse(XML_SRC).getroot():
        get = lambda t: (rec.findtext(t) or '').strip()
        name = norm(get('按縣市別分_By_County_City'))
        if name not in COUNTIES:
            continue
        total = get('常住人口數_總計_人_Number_of_resident_population_Grand_total_person')
        if not total:
            continue  # the English-label twin rows carry no values
        rows[name] = {
            'total': int(num(total)),
            'male': int(num(get('常住人口數_男_人_Number_of_resident_population_Male_person'))),
            'female': int(num(get('常住人口數_女_人_Number_of_resident_population_Female_person'))),
            'area': num(get('土地面積_平方公里_Total_land_area_km2')),
            'density': num(get('人口密度_Population_density')),
        }
    return rows


def main():
    a, b = read_csv_99(), read_xml_109()
    missing = [c for c in COUNTIES if c not in a or c not in b]
    assert not missing, f'unmatched counties: {missing}'

    out = []
    for name in COUNTIES:
        p99, p109 = a[name]['total'], b[name]['total']
        out.append({
            'name': name,
            'en': EN[name],
            'region': REGION[name],
            'p99': p99,
            'p109': p109,
            'delta': p109 - p99,
            'pct': round((p109 - p99) / p99 * 100, 2),
            'area': b[name]['area'],
            'density99': round(p99 / a[name]['area'], 1),
            'density109': round(b[name]['density'], 1),
            'male109': b[name]['male'],
            'female109': b[name]['female'],
            'sexRatio109': round(b[name]['male'] / b[name]['female'] * 100, 1),
        })

    t99 = sum(c['p99'] for c in out)
    t109 = sum(c['p109'] for c in out)
    totals = {
        'p99': t99, 'p109': t109, 'delta': t109 - t99,
        'pct': round((t109 - t99) / t99 * 100, 2),
        'grew': sum(1 for c in out if c['delta'] > 0),
        'shrank': sum(1 for c in out if c['delta'] < 0),
    }
    json.dump({'counties': out, 'totals': totals}, open(OUT, 'w'),
              ensure_ascii=False, indent=1)

    # Cross-check the derived totals against the grand-total rows in the sources.
    print(f'99總計derived={t99:,}  (檔案23,123,866)')
    print(f'109總計derived={t109:,}  (檔案23,829,897)')
    print(f'增減{totals["delta"]:+,} ({totals["pct"]:+.2f}%)成長{totals["grew"]}縣市 / 衰退{totals["shrank"]}縣市\n')
    for c in sorted(out, key=lambda c: -c['pct']):
        print(f'{c["name"]:5s}{c["region"]:2s}{c["p99"]:>9,} -> {c["p109"]:>9,}  '
              f'{c["delta"]:>+8,}{c["pct"]:>+6.2f}%密度{c["density109"]:>7,.1f}')


if __name__ == '__main__':
    main()
