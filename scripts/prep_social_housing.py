#!/usr/bin/env python3
"""Parse 社會住宅包租代管計畫執行情形 into a county table.

包租代管 is the half of social-housing policy that uses the *existing* stock:
the government (or a contracted operator) leases a private flat and sublets it,
instead of building. That makes it the natural counterpart to the vacancy pages
— it is the instrument the quadrant analysis recommends for 「有房子，但租不起」.

Two things about this source have to survive into the data or the map will lie:

1. The figures are **累計媒合戶數** — every match ever made across five rounds of
   the programme, summed. They are not a stock. The footer says the national
   cumulative 234,596 corresponds to 116,390 contracts still in force; the
   split is published nationally only, so no county figure may be scaled by it.
2. 澎湖縣、金門縣、連江縣 are absent from the table entirely, and some counties
   carry 「未開辦」 for a round. Absent ≠ zero, so both are kept as null.

    python3 scripts/prep_social_housing.py
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PDF = ROOT / 'data' / 'sources' / '社會住宅包租代管計畫執行情形_1150731.pdf'
OUT = ROOT / 'data' / 'tw_social_housing.json'

COUNTIES = ['新北市', '臺北市', '桃園市', '臺中市', '臺南市', '高雄市', '宜蘭縣',
            '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義縣', '屏東縣',
            '臺東縣', '花蓮縣', '澎湖縣', '基隆市', '新竹市', '嘉義市', '金門縣', '連江縣']

# 表頭橫跨三列，pdftotext 拆不出來；欄序是人工核對後寫死的，並以小計列驗證。
ROUNDS = ['第5期地方', '第5期中央', '第4期地方', '第4期中央',
          '第3期地方', '第3期中央', '第2期地方', '第2期中央', '第1期']
DASH = '－'          # U+FF0D，該期未辦理
NOTSTART = '未開辦'


def text_of(pdf):
    if not shutil.which('pdftotext'):
        sys.exit('需要 pdftotext（poppler-utils）：apt-get install -y poppler-utils')
    with tempfile.TemporaryDirectory() as d:
        txt = pathlib.Path(d) / 'p.txt'
        subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)], check=True,
                       capture_output=True)
        return txt.read_text(encoding='utf-8').splitlines()


def cell(tok):
    if tok in (DASH, '-', NOTSTART, '─', '—'):
        return None
    return int(tok.replace(',', ''))


def main():
    if not PDF.exists():
        sys.exit(f'缺少來源檔：{PDF}')
    lines = text_of(PDF)

    date = '115 年 7 月 31 日'
    for ln in lines:
        m = re.search(r'資料日期：\s*(\d+\s*年\s*\d+\s*月\s*\d+\s*日)', ln)
        if m:
            date = re.sub(r'\s+', ' ', m.group(1))
            break

    # 六都的縣市名獨占一列（下一列才是數字），其餘縣市名與數字同列。
    rows, pending = {}, None
    for ln in lines:
        parts = ln.split()
        if not parts:
            continue
        if parts[0] in COUNTIES:
            if len(parts) == 1 + len(ROUNDS):
                rows[parts[0]] = [cell(t) for t in parts[1:]]
                pending = None
            elif len(parts) == 1:
                pending = parts[0]
            continue
        if pending and len(parts) == len(ROUNDS):
            rows[pending] = [cell(t) for t in parts]
            pending = None
        elif parts[0] == '小計' and len(parts) == 1 + len(ROUNDS):
            rows['__小計__'] = [cell(t) for t in parts[1:]]

    subtotal = rows.pop('__小計__', None)
    assert subtotal, '找不到小計列，欄序可能已變動'
    missing = [c for c in COUNTIES if c not in rows]

    # 逐欄與小計對帳：欄序錯了這裡一定會爆。
    for j, label in enumerate(ROUNDS):
        got = sum(r[j] or 0 for r in rows.values())
        assert got == subtotal[j], f'{label} 加總 {got} ≠ 小計 {subtotal[j]}'

    grand = None
    for ln in lines:
        m = re.search(r'^\s*([\d,]{6,})\s*$', ln)
        if m and cell(m.group(1)) == sum(subtotal):
            grand = cell(m.group(1))
    grand = grand or sum(subtotal)

    live = None
    for ln in lines:
        m = re.search(r'有效契約數[^\d]*([\d,]+)\s*戶', ln)
        if m:
            live = cell(m.group(1))
    assert live, '找不到有效契約數'

    hou = json.loads((ROOT / 'data' / 'tw_housing.json').read_text(encoding='utf-8'))
    households = {c['name']: c['households'] for c in hou['counties']}

    counties = []
    for name in COUNTIES:
        v = rows.get(name)
        hh = households[name]
        matched = sum(x for x in (v or []) if x is not None) if v else None
        counties.append({
            'name': name,
            'listed': v is not None,
            'rounds': v,
            'matched': matched,
            'households': hh,
            # 每千家戶：縣市大小差 500 倍，絕對戶數畫成面量圖只會畫出人口圖
            'per1000': round(matched / hh * 1000, 2) if matched is not None else None,
            'latest': (v[0] if v and v[0] is not None else 0) +
                      (v[1] if v and v[1] is not None else 0) if v else None,
        })

    nat_hh = hou['national']['households']
    data = {
        'source': '內政部國土管理署《社會住宅包租代管計畫執行情形》',
        'asOf': date,
        'measure': '累計媒合戶數',
        'roundLabels': ROUNDS,
        'national': {
            'matched': grand, 'live': live,
            'liveShare': round(live / grand * 100, 1),
            'households': nat_hh,
            'per1000': round(grand / nat_hh * 1000, 2),
            'byRound': subtotal,
            'latest': (subtotal[0] or 0) + (subtotal[1] or 0),
        },
        'notListed': missing,
        'counties': counties,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    print(f'{OUT.relative_to(ROOT)}：{len(COUNTIES) - len(missing)} 個縣市有資料，'
          f'{len(missing)} 個未列（{"、".join(missing)}）')
    print(f'  資料日期 {date}')
    print(f'  累計媒合 {grand:,} 戶　有效契約 {live:,} 戶（{data["national"]["liveShare"]}%）')
    print(f'  全國每千家戶 {data["national"]["per1000"]} 戶')
    top = sorted((c for c in counties if c['per1000']), key=lambda c: -c['per1000'])
    for c in top[:5]:
        print(f'  {c["name"]:5s}{c["per1000"]:>7.2f} 戶/千家戶　累計 {c["matched"]:>7,}')
    print(f'  最低：' + '、'.join(f'{c["name"]} {c["per1000"]}' for c in top[-3:]))


if __name__ == '__main__':
    main()
