#!/usr/bin/env python3
"""Report the structure of every file in a folder, without guessing at it.

Written for the moment a new batch of government data lands: before anything is
parsed, this says what is actually there — sheet names, column headers, row
counts, the first data row. Reading the structure takes one command instead of a
round of "what do the columns look like?".

    python3 scripts/inspect_data.py "data_TW/2026_社會住宅興辦情形"
    python3 scripts/inspect_data.py data_TW --depth 2 --json out.json

Handles csv/tsv, xlsx/xlsm, ods, json, xml, pdf, zip and plain text with the
standard library only. Encoding is sniffed across the four that Taiwanese
government files actually use, because a Big5 file read as UTF-8 produces
plausible-looking garbage rather than an error.
"""
import argparse, csv, io, json, pathlib, re, sys, xml.etree.ElementTree as ET, zipfile

ENCODINGS = ('utf-8-sig', 'utf-8', 'cp950', 'big5hkscs')
XL = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ODS = {'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
       'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
       'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}


def decode(raw):
    for enc in ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', 'replace'), 'utf-8(取代)'


def head(cells, n=8):
    out = [str(c).strip()[:22] for c in cells[:n]]
    if len(cells) > n:
        out.append(f'…共 {len(cells)} 欄')
    return out


def csv_info(path, raw):
    text, enc = decode(raw)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',\t;|')
        delim = dialect.delimiter
    except csv.Error:
        delim = '\t' if path.suffix.lower() == '.tsv' else ','
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [r for r in rows if any(c.strip() for c in r)]
    info = {'kind': 'csv', 'encoding': enc, 'delimiter': delim, 'rows': len(rows)}
    if rows:
        info['header'] = head(rows[0])
        # Government tables often stack two or three header rows; show enough to see it.
        info['sample'] = [head(r) for r in rows[1:4]]
        widths = {len(r) for r in rows}
        if len(widths) > 1:
            info['ragged'] = f'欄數不一致：{sorted(widths)[:6]}'
    return info


def xlsx_info(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = z.namelist()
    shared = []
    if 'xl/sharedStrings.xml' in names:
        shared = [''.join(t.text or '' for t in si.iter(XL + 't'))
                  for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(XL + 'si')]
    sheets = []
    try:
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        titles = [s.get('name') for s in wb.iter(XL + 'sheet')]
    except Exception:
        titles = []
    paths = sorted(n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
    for i, p in enumerate(paths):
        rows = []
        for row in ET.fromstring(z.read(p)).iter(XL + 'row'):
            cells = []
            for c in row.findall(XL + 'c'):
                v = c.find(XL + 'v')
                if v is None:
                    cells.append('')
                    continue
                cells.append(shared[int(v.text)] if c.get('t') == 's' and shared else v.text)
            if any(str(x).strip() for x in cells):
                rows.append(cells)
            if len(rows) >= 6:
                break
        total = sum(1 for _ in ET.fromstring(z.read(p)).iter(XL + 'row'))
        sheets.append({'name': titles[i] if i < len(titles) else p.split('/')[-1],
                       'rows': total, 'preview': [head(r) for r in rows[:5]]})
    return {'kind': 'xlsx', 'sheets': sheets}


def ods_info(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    root = ET.fromstring(z.read('content.xml'))
    sheets = []
    for tbl in root.iter(f'{{{ODS["table"]}}}table'):
        name = tbl.get(f'{{{ODS["table"]}}}name')
        rows, total = [], 0
        for tr in tbl.iter(f'{{{ODS["table"]}}}table-row'):
            total += 1
            if len(rows) >= 5:
                continue
            cells = []
            for td in tr.findall(f'{{{ODS["table"]}}}table-cell'):
                rep = int(td.get(f'{{{ODS["table"]}}}number-columns-repeated', 1))
                txt = ''.join(p.text or '' for p in td.iter(f'{{{ODS["text"]}}}p'))
                cells.extend([txt] * min(rep, 40))
            if any(c.strip() for c in cells):
                rows.append(cells)
        sheets.append({'name': name, 'rows': total, 'preview': [head(r) for r in rows]})
    return {'kind': 'ods', 'sheets': sheets}


def json_info(raw):
    text, enc = decode(raw)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return {'kind': 'json', 'encoding': enc, 'error': str(e)[:90]}
    def shape(o, d=0):
        if isinstance(o, dict):
            ks = list(o)[:10]
            return {'type': 'object', 'keys': ks + (['…'] if len(o) > 10 else []),
                    'first': shape(o[ks[0]], d + 1) if ks and d < 2 else None}
        if isinstance(o, list):
            return {'type': f'array[{len(o)}]',
                    'item': shape(o[0], d + 1) if o and d < 2 else None}
        return {'type': type(o).__name__, 'value': str(o)[:40]}
    return {'kind': 'json', 'encoding': enc, 'shape': shape(obj)}


def xml_info(raw):
    text, enc = decode(raw)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return {'kind': 'xml', 'encoding': enc, 'error': str(e)[:90]}
    tags = {}
    for e in root.iter():
        tags[e.tag] = tags.get(e.tag, 0) + 1
    top = sorted(tags.items(), key=lambda kv: -kv[1])[:10]
    first = next((e for e in root.iter() if len(e) and e is not root), root)
    return {'kind': 'xml', 'encoding': enc, 'root': root.tag,
            'tags': [f'{k} ×{v}' for k, v in top],
            'sample': {c.tag: (c.text or '').strip()[:30] for c in list(first)[:8]}}


def pdf_info(raw):
    pages = len(re.findall(rb'/Type\s*/Page[^s]', raw))
    info = {'kind': 'pdf', 'pages': pages or None}
    m = re.search(rb'/Title\s*\(([^)]{1,120})\)', raw)
    if m:
        # PDF titles are often UTF-16BE or in a font-specific encoding; showing
        # the mojibake is worse than showing nothing.
        t = m.group(1).decode('utf-8', 'replace')
        if '�' not in t and t.isprintable():
            info['title'] = t
    info['note'] = '用 pdftotext -layout 取出文字後再解析'
    return info


def zip_info(raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    items = [(i.filename, i.file_size) for i in z.infolist() if not i.is_dir()]
    return {'kind': 'zip', 'files': len(items),
            'contents': [f'{n} ({s:,}B)' for n, s in items[:12]]}


READERS = {'.csv': csv_info, '.tsv': csv_info, '.txt': csv_info}


def inspect(path):
    raw = path.read_bytes()
    ext = path.suffix.lower()
    try:
        if ext in READERS:
            return READERS[ext](path, raw)
        if ext in ('.xlsx', '.xlsm'):
            return xlsx_info(raw)
        if ext == '.ods':
            return ods_info(raw)
        if ext == '.json' or ext == '.geojson':
            return json_info(raw)
        if ext == '.xml':
            return xml_info(raw)
        if ext == '.pdf':
            return pdf_info(raw)
        if ext == '.zip':
            return zip_info(raw)
        if ext in ('.xls',):
            return {'kind': 'xls', 'note': '舊版二進位 Excel，需先另存為 xlsx 或 csv'}
    except Exception as e:
        return {'kind': ext or '?', 'error': f'{type(e).__name__}: {e}'[:120]}
    return {'kind': ext or '（無副檔名）'}


def show(path, info, indent='    '):
    for k in ('encoding', 'delimiter', 'rows', 'ragged', 'root', 'pages', 'title',
              'files', 'error', 'note'):
        if info.get(k):
            print(f'{indent}{k}: {info[k]}')
    if info.get('header'):
        print(f'{indent}欄位: {" | ".join(info["header"])}')
    for r in info.get('sample', []) if isinstance(info.get('sample'), list) else []:
        print(f'{indent}      {" | ".join(r)}')
    if isinstance(info.get('sample'), dict):
        print(f'{indent}子節點: {info["sample"]}')
    for s in info.get('sheets', []):
        print(f'{indent}工作表「{s["name"]}」{s["rows"]} 列')
        for r in s['preview']:
            print(f'{indent}      {" | ".join(r)}')
    for t in info.get('tags', []) or info.get('contents', []):
        print(f'{indent}  {t}')
    if info.get('shape'):
        print(f'{indent}結構: {json.dumps(info["shape"], ensure_ascii=False)[:300]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--depth', type=int, default=3, help='遞迴層數')
    ap.add_argument('--limit', type=int, default=60, help='最多檢視幾個檔')
    ap.add_argument('--json', help='另存完整結果為 JSON')
    a = ap.parse_args()

    root = pathlib.Path(a.folder)
    if not root.exists():
        sys.exit(f'找不到 {root}')

    files = sorted(p for p in root.rglob('*')
                   if p.is_file() and not p.name.startswith('.')
                   and len(p.relative_to(root).parts) <= a.depth)
    total = sum(p.stat().st_size for p in files)
    print(f'{root}：{len(files)} 個檔，共 {total / 1048576:.1f} MB\n')

    out = []
    for p in files[:a.limit]:
        rel = p.relative_to(root)
        size = p.stat().st_size
        print(f'{rel}　{size:,} bytes')
        info = inspect(p)
        show(p, info)
        print()
        out.append({'path': str(rel), 'bytes': size, **info})
    if len(files) > a.limit:
        print(f'（還有 {len(files) - a.limit} 個檔未列出，用 --limit 調整）')
    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({'folder': str(root), 'files': out}, ensure_ascii=False, indent=2),
            encoding='utf-8')
        print(f'完整結果寫入 {a.json}')


if __name__ == '__main__':
    main()
