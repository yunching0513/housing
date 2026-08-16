#!/usr/bin/env python3
"""Append the census's own table index to sources.json.

Dataset 10906 is not data — it is a catalogue. Each of its two XML files lists
every table of that census round (1,037 for 99 年, 1,134 for 109 年) with a direct
.ods link. This script reads those indexes and adds the housing and household
tables, national and per-county, to the source list.

Run after fetch_sources.py has pulled the two index files.

    python3 scripts/expand_census.py --out data_TW
"""
import argparse, json, pathlib, re, sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
COUNTY = re.compile(r'新北市|臺北市|桃園[市縣]|臺中[市縣]|臺南[市縣]|高雄[市縣]|基隆市|新竹[市縣]|'
                    r'嘉義[市縣]|宜蘭縣|苗栗縣|彰化縣|南投縣|雲林縣|屏東縣|臺東縣|花蓮縣|澎湖縣|金門縣|連江縣')
# Housing supply and household formation — the demand/supply pair a social-housing
# assessment needs. Population tables already arrive via the curated picks.
KEEP = re.compile(r'住宅|宅數|空閒|權屬|樓地板|房廳|'          # supply
                  r'住戶數|家戶型態|戶內人口數|'                # household formation
                  r'遷徙|年前居住地|工作地與經常居住地')          # where demand comes from
CLEAN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def tidy(item):
    """'（參）住宅\\表８７　住宅使用情形' -> ('住宅', '表87 住宅使用情形')"""
    part = item.replace('\\', '/').split('/')
    section = re.sub(r'^（.）', '', part[0]).strip() if len(part) > 1 else ''
    name = part[-1]
    # full-width digits read badly in filenames
    name = name.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    return section, CLEAN.sub('_', re.sub(r'\s+', ' ', name)).strip()[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'data_TW'))
    ap.add_argument('--sources', default=str(ROOT / 'sources.json'))
    args = ap.parse_args()

    src = pathlib.Path(args.sources)
    sources = json.loads(src.read_text(encoding='utf-8'))
    known = {u for e in sources for u in e['urls']}
    added = 0

    for path in sorted(pathlib.Path(args.out).glob('**/人口及住宅普查*.xml')):
        year = re.search(r'_(\d{3})民國年', path.name)
        year = year.group(1).lstrip('0') if year else '?'
        recs = [{c.tag: (c.text or '').strip() for c in r} for r in ET.parse(path).getroot()]
        for r in recs:
            item, url = r.get('資料項目', ''), r.get('連結', '')
            if not url or url in known or not KEEP.search(item):
                continue
            section, name = tidy(item)
            m = COUNTY.search(name)
            cat = f'07_普查{year}年_統計表/{section or "其他"}'
            if m:
                cat = f'07_普查{year}年_統計表/縣市/{m.group(0)}'
            sources.append({
                'category': cat,
                'dataset_id': '10906',
                'title': name,
                'agency': '行政院主計總處',
                'update': '每10年',
                'urls': [url],
            })
            known.add(url)
            added += 1

    src.write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'新增 {added} 張普查統計表，sources.json 現有 {len(sources)} 個項目 '
          f'/ {sum(len(e["urls"]) for e in sources)} 個檔案')


if __name__ == '__main__':
    main()
