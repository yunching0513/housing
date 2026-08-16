#!/usr/bin/env python3
"""Convert the census .ods tables to CSV, without needing LibreOffice or pandas.

An .ods file is a zip holding content.xml; the only real subtleties are
`number-columns-repeated` (runs of identical cells are stored once) and the fact
that a displayed string can differ from the underlying `office:value`. Both are
handled here, so the numbers come out machine-readable rather than as the
comma-formatted text the spreadsheet shows.

    python3 scripts/ods_to_csv.py data_TW/07_普查109年_統計表          # whole tree
    python3 scripts/ods_to_csv.py "path/表87 住宅使用情形.ods"          # one file

CSVs are written next to their source with a .csv suffix.
"""
import csv, pathlib, re, sys, zipfile

CELL = re.compile(r'<table:table-cell(.*?)(?:/>|>(.*?)</table:table-cell>)', re.S)
ROW = re.compile(r'<table:table-row(.*?)>(.*?)</table:table-row>', re.S)
REPEAT = re.compile(r'number-columns-repeated="(\d+)"')
ROW_REPEAT = re.compile(r'number-rows-repeated="(\d+)"')
VALUE = re.compile(r'office:value="([-\d.]+)"')
TAG = re.compile(r'<[^>]+>')
# A run longer than this is the sheet's trailing padding, not data.
MAX_RUN = 64


def cells(chunk):
    out = []
    for attrs, body in CELL.findall(chunk):
        rep = REPEAT.search(attrs)
        n = min(int(rep.group(1)) if rep else 1, MAX_RUN)
        val = VALUE.search(attrs)
        text = val.group(1) if val else TAG.sub('', body or '').replace('　', ' ').strip()
        out.extend([text] * n)
    while out and not out[-1]:
        out.pop()
    return out


def convert(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('content.xml').decode('utf-8')
    rows = []
    for attrs, body in ROW.findall(xml):
        line = cells(body)
        rep = ROW_REPEAT.search(attrs)
        n = min(int(rep.group(1)) if rep else 1, MAX_RUN)
        rows.extend([line] * (n if line else 1))
    while rows and not any(rows[-1]):
        rows.pop()
    if not rows:
        return None
    width = max(len(r) for r in rows)
    dest = path.with_suffix('.csv')
    with dest.open('w', encoding='utf-8-sig', newline='') as fh:
        csv.writer(fh).writerows(r + [''] * (width - len(r)) for r in rows)
    return dest, len(rows), width


def main():
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'data_TW')
    files = [target] if target.suffix == '.ods' else sorted(target.rglob('*.ods'))
    if not files:
        sys.exit(f'找不到 .ods 檔：{target}')
    done = failed = 0
    for f in files:
        try:
            r = convert(f)
            if r:
                done += 1
            else:
                failed += 1
                print(f'  空白：{f.name}')
        except Exception as e:
            failed += 1
            print(f'  失敗：{f.name} ({type(e).__name__})')
    print(f'轉出 {done} 個 CSV' + (f'，{failed} 個未成功' if failed else ''))


if __name__ == '__main__':
    main()
