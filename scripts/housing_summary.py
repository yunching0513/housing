#!/usr/bin/env python3
"""Pull the county-level housing supply picture out of the 109 年 census tables.

Reads 表87（住宅使用情形）and 表66（住戶數、常住人口數及平均每戶人口數）and joins
them into one tidy CSV: housing stock, occupied, vacant, and the vacancy rate that
matters for social-housing policy — 「目前沒有使用」, which excludes homes that are
occasionally self-occupied or used as offices/storage.

    python3 scripts/housing_summary.py --out data_TW
"""
import argparse, csv, pathlib, re, sys, zipfile

CELL = re.compile(r'<table:table-cell(.*?)(?:/>|>(.*?)</table:table-cell>)', re.S)
ROW = re.compile(r'<table:table-row[^>]*>(.*?)</table:table-row>', re.S)
REPEAT = re.compile(r'number-columns-repeated="(\d+)"')
VALUE = re.compile(r'office:value="([-\d.]+)"')
TAG = re.compile(r'<[^>]+>')
COUNTIES = ['新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '基隆市', '新竹市',
            '嘉義市', '宜蘭縣', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣',
            '屏東縣', '臺東縣', '花蓮縣', '澎湖縣', '金門縣', '連江縣']


def sheet(path):
    xml = zipfile.ZipFile(path).read('content.xml').decode('utf-8')
    out = []
    for body in ROW.findall(xml):
        line = []
        for attrs, cell in CELL.findall(body):
            rep = REPEAT.search(attrs)
            n = min(int(rep.group(1)) if rep else 1, 32)
            val = VALUE.search(attrs)
            line.extend([val.group(1) if val else
                         TAG.sub('', cell or '').replace('　', '').strip()] * n)
        out.append(line)
    return out


def indexed(rows, wanted, least=6):
    """Map 縣市 -> its numeric cells.

    A county name also appears in header and English-label rows, so only accept a
    row that actually carries at least `least` numbers.
    """
    found = {}
    for line in rows:
        label = next((c for c in line[:3] if c in wanted), None)
        if not label or label in found:
            continue
        nums = [float(c) for c in line if re.fullmatch(r'\d+(\.\d+)?', c or '')]
        if len(nums) >= least:
            found[label] = nums
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data_TW')
    args = ap.parse_args()
    base = pathlib.Path(args.out) / '07_普查109年_統計表' / '其他'
    use = base / '表87 住宅使用情形.ods'
    hh = base / '表66 住戶數、常住人口數及平均每戶人口數.ods'
    for f in (use, hh):
        if not f.exists():
            sys.exit(f'缺少 {f}')

    want = set(COUNTIES) | {'總計'}
    u, h = indexed(sheet(use), want), indexed(sheet(hh), want)

    dest = pathlib.Path(args.out) / '02_住宅存量' / '109年住宅供給彙整.csv'
    dest.parent.mkdir(parents=True, exist_ok=True)
    head = ['縣市', '住宅總數_宅', '有人經常居住_宅', '無人經常居住_宅', '偶爾自住_宅',
            '自住以外用途_宅', '目前沒有使用_宅', '空置率_percent', '住戶數_戶',
            '每戶人口', '住宅數除以住戶數']
    out = []
    for name in ['總計'] + COUNTIES:
        if name not in u:
            continue
        n = u[name]
        # 表87 columns: 總計, 有人合計, 住宅專用, 兼農工, 無人合計, 偶爾自住,
        # 自住以外用途, 目前沒有使用
        total, occ, unocc, occa, other, idle = n[0], n[1], n[4], n[5], n[6], n[7]
        hn = h.get(name, [])
        households = hn[0] if hn else 0
        per = hn[2] if len(hn) > 2 else 0
        out.append([name, int(total), int(occ), int(unocc), int(occa), int(other), int(idle),
                    round(idle / total * 100, 2), int(households), per,
                    round(total / households, 3) if households else ''])

    with dest.open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(out)

    print(f'{dest}（{len(out)} 列）\n')
    print(f'{"":8s}{"住宅總數":>11s}{"目前沒使用":>11s}{"空置率":>8s}{"住戶數":>11s}{"宅/戶":>7s}')
    for r in out:
        print(f'{r[0]:8s}{r[1]:>11,}{r[6]:>11,}{r[7]:>7.1f}%{r[8]:>11,}{r[10]:>7}')


if __name__ == '__main__':
    main()
