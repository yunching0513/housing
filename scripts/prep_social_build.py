#!/usr/bin/env python3
"""社宅直接興建進度：覆蓋率分子的另一半。

包租代管用的是別人已經蓋好的房子，這一份是政府自己蓋的。兩份加起來才算得出
「社會住宅覆蓋率」——這個站從第一頁起就想回答、但一直缺一半的數字。

Source: 國土管理署《全國社會住宅興辦進度統計表》，截至 2026 年 7 月 31 日
        （民國 115 年 7 月 31 日，與包租代管那份同一個資料日）。

表的形狀：每個縣市三列（中央／地方／小計），六個欄位。前四欄是「已決標」底下
的細分，最後兩欄是加總：

    已完工 ＋ 興建中 ＋ 待開工 ＝ 已決標小計
    已決標小計 ＋ 規劃中 ＝ 總計

兩個都會在寫檔前逐列驗算，對不上就中止——這種三層表頭最容易在欄序上出錯，而
錯了不會有任何徵兆。

    python3 scripts/prep_social_build.py
"""
import json, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data_TW' / '2026_社會住宅興辦情形' / '1150731-社會住宅興辦案件執行情形彙整表_1.pdf'
OUT = ROOT / 'data' / 'tw_social_build.json'

COUNTIES = ['臺北市', '新北市', '桃園市', '臺中市', '臺南市', '高雄市', '基隆市',
            '新竹市', '新竹縣', '苗栗縣', '彰化縣', '南投縣', '雲林縣', '嘉義市',
            '嘉義縣', '屏東縣', '宜蘭縣', '花蓮縣', '臺東縣', '澎湖縣', '金門縣', '連江縣']
SUBJECTS = ['中央', '地方', '小計']
# 已完工、興建中、待開工 是「已決標」的三個階段；小計是它們的和。
STAGES = ['done', 'building', 'awaiting', 'awarded', 'planning', 'total']
STAGE_LABEL = {'done': '已完工', 'building': '興建中', 'awaiting': '已決標待開工',
               'awarded': '已決標小計', 'planning': '規劃中', 'total': '總計'}


def text_of(pdf):
    if not shutil.which('pdftotext'):
        sys.exit('需要 pdftotext（poppler-utils）：apt-get install -y poppler-utils')
    with tempfile.TemporaryDirectory() as d:
        txt = pathlib.Path(d) / 'p.txt'
        subprocess.run(['pdftotext', '-layout', str(pdf), str(txt)],
                       check=True, capture_output=True)
        return txt.read_text(encoding='utf-8').splitlines()


def num(tok):
    return int(tok.replace(',', ''))


def main():
    if not SRC.exists():
        sys.exit(f'缺少來源檔：{SRC}')
    lines = text_of(SRC)

    date = '民國 115 年 7 月 31 日'
    for ln in lines:
        m = re.search(r'截至\s*(\d{4})\s*年\s*(\d+)\s*月\s*(\d+)\s*日', ln)
        if m:
            date = f'民國 {int(m.group(1)) - 1911} 年 {int(m.group(2))} 月 {int(m.group(3))} 日'
            break

    # 縣市名印在三列的**中間**那列（地方），不是第一列。所以不能邊讀邊指派：
    # 讀到「中央」那列時還不知道它屬於誰。改成先收成 中央／地方／小計 一組，
    # 湊滿三列再從組裡找名字。
    rows, national, group, group_name = {}, {}, {}, None
    for ln in lines:
        parts = ln.split()
        if not parts:
            continue
        here = None
        if parts[0] in COUNTIES or parts[0] == '合計':
            here = parts[0]
            parts = parts[1:]
        if not parts or parts[0] not in SUBJECTS:
            continue
        subject, vals = parts[0], parts[1:]
        if len(vals) != len(STAGES) or not all(re.fullmatch(r'[\d,]+', v) for v in vals):
            continue
        if subject == '中央':                      # 每一組都由「中央」開頭
            group, group_name = {}, None
        if here:
            group_name = here
        group[subject] = dict(zip(STAGES, (num(v) for v in vals)))
        if subject == '小計':                      # 每一組都由「小計」結尾
            assert group_name, f'讀到一組沒有縣市名的資料：{group}'
            assert set(group) == set(SUBJECTS), f'{group_name} 只有 {sorted(group)}'
            if group_name == '合計':
                national.update(group)
            else:
                rows[group_name] = group
            group, group_name = {}, None

    missing = [c for c in COUNTIES if c not in rows]
    assert not missing, f'表中缺少：{missing}'
    assert set(national) == set(SUBJECTS), f'合計列不完整：{sorted(national)}'

    # 三道驗算。欄序若被讀錯，這裡一定會爆，不會默默算出一份錯的資料。
    for name, by in list(rows.items()) + [('合計', national)]:
        for subject, v in by.items():
            got = v['done'] + v['building'] + v['awaiting']
            assert got == v['awarded'], \
                f'{name}/{subject} 已決標 {v["awarded"]} ≠ 三階段和 {got}'
            assert v['awarded'] + v['planning'] == v['total'], \
                f'{name}/{subject} 總計 {v["total"]} ≠ 已決標＋規劃中'
        for k in STAGES:
            assert by['中央'][k] + by['地方'][k] == by['小計'][k], \
                f'{name} 的 {k}：中央＋地方 ≠ 小計'
    for k in STAGES:
        got = sum(rows[c]['小計'][k] for c in COUNTIES)
        assert got == national['小計'][k], \
            f'{STAGE_LABEL[k]} 縣市加總 {got:,} ≠ 合計 {national["小計"][k]:,}'

    hou = json.loads((ROOT / 'data' / 'tw_housing.json').read_text(encoding='utf-8'))
    households = {c['name']: c['households'] for c in hou['counties']}
    soc = json.loads((ROOT / 'data' / 'tw_social_housing.json').read_text(encoding='utf-8'))
    rented = {c['name']: c['matched'] for c in soc['counties']}

    counties = []
    for name in COUNTIES:
        by = rows[name]
        hh = households[name]
        s = by['小計']
        counties.append({
            'name': name,
            'central': by['中央'], 'local': by['地方'], 'total': s,
            'households': hh,
            # 每千家戶：縣市大小差 500 倍，絕對戶數只會畫出人口圖
            'donePer1000': round(s['done'] / hh * 1000, 2),
            'awardedPer1000': round(s['awarded'] / hh * 1000, 2),
            'totalPer1000': round(s['total'] / hh * 1000, 2),
            # 中央佔比：這一項在縣市之間差很大，是誰在蓋的直接證據
            'centralShare': round(by['中央']['total'] / s['total'] * 100, 1) if s['total'] else None,
            # 兩條路合起來才是社宅供給。包租代管是累計媒合，不是存量，兩者
            # 口徑不同，所以分開存、頁面上分開講，不做成一個混合數字。
            'rented': rented.get(name),
        })

    nat_hh = hou['national']['households']
    data = {
        'asOf': date,
        'source': '內政部國土管理署《全國社會住宅興辦進度統計表》',
        'stageLabels': STAGE_LABEL,
        'definition': {
            '已完工': '新建社宅為取得使用執照；修繕社宅為修繕完成',
            '興建中': '取得建造執照並完成開工申報',
            '已決標': '已完工＋興建中＋已決標待開工',
            '規劃中': '尚未決標',
        },
        'national': {
            'central': national['中央'], 'local': national['地方'], 'total': national['小計'],
            'households': nat_hh,
            'donePer1000': round(national['小計']['done'] / nat_hh * 1000, 2),
            'totalPer1000': round(national['小計']['total'] / nat_hh * 1000, 2),
            'centralShare': round(national['中央']['total'] / national['小計']['total'] * 100, 1),
            'rented': soc['national']['matched'],
            'rentedLive': soc['national']['live'],
        },
        'counties': counties,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    n = data['national']
    print(f'{OUT.relative_to(ROOT)}：{len(counties)} 縣市，資料日 {date}')
    print(f"  全國已完工 {n['total']['done']:,} 戶　興建中 {n['total']['building']:,}"
          f"　待開工 {n['total']['awaiting']:,}")
    print(f"  已決標 {n['total']['awarded']:,}　規劃中 {n['total']['planning']:,}"
          f"　總計 {n['total']['total']:,}")
    print(f"  中央佔 {n['centralShare']}%　每千家戶已完工 {n['donePer1000']} 戶")
    top = sorted(counties, key=lambda c: -c['donePer1000'])
    for c in top[:5]:
        print(f"  {c['name']:5s}已完工 {c['total']['done']:>7,} 戶"
              f"　每千家戶 {c['donePer1000']:>6.2f}　中央佔 {c['centralShare']}%")
    zero = [c['name'] for c in counties if c['total']['done'] == 0]
    print(f"  已完工 0 戶的縣市（{len(zero)} 個）：{'、'.join(zero)}")


if __name__ == '__main__':
    main()
