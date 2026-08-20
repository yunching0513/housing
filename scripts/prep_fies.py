#!/usr/bin/env python3
"""把民國83年至114年的家庭收支調查整理成縣市 × 年度的面板。

    python3 scripts/prep_fies.py

資料來源是 data_TW/08_家庭收支調查/ 底下的 .ods，共三十二個年度，取三張表：

    第2表  平均每戶家庭收支按區域別分            → 所得、消費、儲蓄、設算租金
    第8表  家庭住宅及主要設備概況按區域別分      → 住宅權屬、建坪、戶量
    第10表 家庭住宅及主要設備概況依可支配所得
           按戶數五等分位分                       → 所得分位的居住條件（僅最新一年）

這支程式存在的理由，是社宅政策的分母一直不清楚：討論租金負擔得起與否，需要
縣市層級的家戶所得中位數，而那個數字只有家庭收支調查有。唯這份調查有四個限制
必須跟著數字一起走，所以它們寫成 caveat 與 breaks 欄位輸出，讓版面沒辦法不引用。

── 限制一：縣市別的抽樣誤差大到不能排名 ────────────────────────────────
主計總處在每一張區域別表的表末自己寫了：「由於縣市別樣本數有限，應用時需考量
抽樣誤差（一般統計上係採平均數±1.96個標準差為信賴區間），若據以作縣市排名，
不具嚴謹統計意義。」表上的「可支配所得標準差」是**平均數的標準誤**而非分配的
標準差：114年總平均的可支配所得是 1,210,367 元、標準差 24,159 元，若那是分配
的標準差，全國家戶所得的離散程度會小到不可思議。因此信賴區間照附註的寫法直接
取 1.96×標準差，不再除以根號 n。算出來的誤差幅度從全國的 ±3.9% 到新竹縣的
±41.7%，後者的樣本只有 350 戶。

── 限制二：不含金門縣與連江縣 ──────────────────────────────────────
二十個縣市的家庭戶數加總等於總平均欄，三十二年逐年檢查全部差 0，可知不是解析
漏抓，而是調查範圍本來就不包含這兩個縣。其餘各頁用的是普查的 22 縣市，兩者
併圖時那兩塊要留白並標明原因，不可以當成 0。

── 限制三：所得與消費支出兩邊都含自用住宅設算租金 ──────────────────────
第2表的所得項目有「4.自用住宅設算租金收入」，消費支出那邊也對應計入住宅服務。
換言之這份「可支配所得」不是現金所得：自有住宅者被記了一筆自己付給自己的房租。
做租金所得比時分母含設算租金、分子是真實付出的現金，兩者性質不同，所以
imputedRent 一併輸出，讓版面有辦法把它扣掉或至少標示出來。

── 限制四：三個定義斷點，跨過去就會講出不存在的故事 ─────────────────────
  * 民國99年：住宅所有權把「自有」拆成兩類。98年自有 87.89%，99年自有只剩
    84.89%，新類別「不住在一起的配偶、父母或子女所擁有」接走 3.38 個百分點。
    那不是自有率崩跌，是同一批人被改分到另一欄。可比的口徑是兩者相加，
    更穩妥的是看非租押比率。租押的定義從頭到尾沒動過，是唯一整段可讀的序列。
  * 民國112年：建坪改了定義。111年《名詞解釋》寫「公寓、大樓僅含自家陽台」，
    112年改成「不含公共設施、陽台及露臺等附屬建物面積」。每戶建坪平均數因此
    從 45.1 坪掉到 40.06 坪，一年少 11%，同期平均每戶人數只從 2.83 動到 2.79。
    那 5 坪不是房子變小，是量法變了。
  * 民國99年與103年：縣市改制。98年以前表上有 23 個縣市，99年起 20 個。
    要把兩段接起來，只能拿同一張表裡的家庭戶數當權重把縣與市加權合併；
    平均數與比率合併得起來，**中位數合併不起來**，所以 98 年以前的臺中、臺南、
    高雄三市的所得中位數一律給 null，不給一個看起來像數字的東西。
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# 讀 .ods 的那段在 ods_to_csv.py 裡已經有了，不重寫一份：同一份解析邏輯分兩處
# 維護，遲早會有一處先修好、另一處還在錯。
from scripts.ods_to_csv import sheet                               # noqa: E402

SRC = ROOT / 'data_TW' / '08_家庭收支調查'
OUT = ROOT / 'data' / 'tw_fies.json'

YEARS = list(range(83, 115))
LATEST = 114

# 調查涵蓋的二十個縣市，以最新一年的表頭為準。金門與連江不在調查範圍內。
COUNTIES = ['臺北市', '新北市', '桃園市', '臺中市', '臺南市', '高雄市',
            '基隆市', '新竹市', '嘉義市', '宜蘭縣', '新竹縣', '苗栗縣',
            '彰化縣', '南投縣', '雲林縣', '嘉義縣', '屏東縣', '臺東縣',
            '花蓮縣', '澎湖縣']
NOT_IN_SURVEY = ['金門縣', '連江縣']

# 98 年以前的舊縣市併到今天的名字。臺北縣與桃園縣是整縣改制（改名不合併），
# 臺中、臺南、高雄是縣市合併，合併年的兩欄要用家庭戶數加權才併得起來。
MERGE = {'臺北縣': '新北市', '桃園縣': '桃園市',
         '臺中縣': '臺中市', '臺南縣': '臺南市', '高雄縣': '高雄市'}
# 真的發生合併（而非單純改名）的三個直轄市：這幾個在 98 年以前中位數不可得。
MERGED_PAIR = {'臺中市', '臺南市', '高雄市'}
RENAMED = {'臺北縣': '新北市', '桃園縣': '桃園市'}

BREAK_TENURE = 99      # 住宅所有權拆成四類
BREAK_FLOOR = 112      # 建坪不再含陽台與露臺
BREAK_MERGE = 99       # 縣市改制，表頭從 23 欄變 20 欄

CITY = re.compile(r'[一-鿿]{2,3}[市縣]')
NUM = re.compile(r'-?\d+(?:\.\d+)?$')

# 欄位對到表上的列標籤。用 fullmatch 而不是 in：「消費支出」與「三、消費支出」
# 是兩個不同的東西，前者是彙總列、後者是明細段的段首，用 in 會抓錯。
INCOME_ROWS = {
    'households': r'家庭戶數',
    'persons': r'平均每戶人數',
    'earners': r'平均每戶所得收入者人數',
    'incomeGross': r'所得總額',
    'incomeMean': r'可支配所得\(平均數\)',
    'incomeMedian': r'可支配所得\(中位數\)',
    'incomeSe': r'可支配所得標準差',
    'consume': r'消費支出',
    'saving': r'儲蓄',
    'imputedRent': r'4\.自用住宅設算租金收入',
    'sample': r'樣本戶數',
}
TENURE_ROWS = {
    'own': r'\(1\)自有(?:\(戶內經常居住成員所擁有\))?',
    'kin': r'\(2\)不住在一起的配偶、父母或子女所擁有',
    'rent': r'\([23]\)租押',
    'other': r'\([34]\)其他\(含配住及借用\)',
    'floorMean': r'\d+\.每戶建坪平均數\(坪\)',
    'floorMedian': r'\d+\.每戶建坪中位數\(坪\)',
    'water': r'\d+\.具有自來水設備',
}
# 抽樣誤差照表末附註算：平均數 ±1.96×標準差。那個標準差是平均數的標準誤。
Z = 1.96

# 來源表本身住宅權屬四類相加不等於 100 的年度縣市，逐筆記下實測的缺口。
# 例如 88年南投縣是自有 83.13＋租押 5.44＋其他 9.41＝97.98，短少 2.02 個百分點。
# 主計總處在這幾張表上沒有任何附註解釋這個缺口，本研究也沒有把握說出原因；
# 唯六筆裡有四筆是 88 至 96 年的南投縣，一筆是 91 年的臺中縣，兩地正是 88 年
# 921 震災的重災區，時間上吻合，**這只是觀察，不是查證過的解釋**。
# 這張表存在的用意不是放行，而是把例外一筆一筆點名：容差因此可以收到 0.05，
# 將來要是重新下載後某一筆的缺口變了、或冒出新的一筆，對帳照樣會擋下來。
TENURE_GAP = {
    (88, '南投縣'): -2.02,
    (90, '南投縣'): -1.42,
    (91, '臺中市'): -0.1496,
    (91, '南投縣'): -0.74,
    (95, '臺東縣'): -0.67,
    (96, '南投縣'): -0.32,
}

tally = {'讀入的儲存格': 0, '納入面板': 0,
         '排除_不是縣市欄': 0, '排除_縣市欄但不是數字': 0}


def norm(s):
    return str(s).replace(' ', '').replace('　', '').replace('台', '臺').strip()


def path(name, roc):
    return SRC / f'家庭收支調查_{name}_民國{roc}年.ods'


def by_county(rows, pattern):
    """抓出某一列標籤在各縣市欄的數值。

    這批表把「續一、續二、續三」三個分塊橫向並排在同一列，所以表頭與資料列
    直接 zip 就對得上；108 年那一份改成直向疊三段，於是往上找最近的表頭列，
    兩種版面用同一段程式吃得下。三十二年的家庭戶數對帳全部差 0，證明對得上。
    """
    pat = re.compile(pattern)
    out = {}
    for i, row in enumerate(rows):
        if not any(pat.fullmatch(norm(c)) for c in row):
            continue
        header = None
        for j in range(i - 1, -1, -1):
            if any(norm(c) == '總平均' or CITY.fullmatch(norm(c)) for c in rows[j]):
                header = rows[j]
                break
        if header is None:
            continue
        for name, value in zip(header, row):
            name, value = norm(name), norm(value)
            tally['讀入的儲存格'] += 1
            if not (name == '總平均' or CITY.fullmatch(name)):
                tally['排除_不是縣市欄'] += 1
                continue
            if not NUM.match(value):
                tally['排除_縣市欄但不是數字'] += 1
                continue
            out.setdefault(name, float(value))
            tally['納入面板'] += 1
    return out


def read_year(roc):
    """一個年度的原始縣市值，鍵是該年表上的縣市名（尚未併縣市）。"""
    inc = sheet(path('平均每戶家庭收支按區域別分', roc))
    ten = sheet(path('家庭住宅及主要設備概況按區域別分', roc))
    raw = {}
    for field, pattern in INCOME_ROWS.items():
        raw[field] = by_county(inc, pattern)
    for field, pattern in TENURE_ROWS.items():
        raw[field] = by_county(ten, pattern)
    return raw


def harmonise(roc, raw):
    """把該年的縣市欄併成今天的二十個縣市。

    平均數與比率用家庭戶數加權，戶數本身用相加。中位數與標準差沒有辦法從
    兩個子群回推母群，真的發生合併的三個直轄市在 98 年以前一律 null。
    """
    weights = raw['households']
    merged, problems = {}, []
    for field, values in raw.items():
        acc = {}
        for name, value in values.items():
            if name == '總平均':
                continue
            target = MERGE.get(name, name)
            if target not in COUNTIES:
                problems.append(f'{roc}年出現不認得的縣市欄「{name}」')
                continue
            acc.setdefault(target, []).append((name, value))
        out = {}
        for target, parts in acc.items():
            if len(parts) == 1:
                out[target] = parts[0][1]
            elif field == 'households':
                out[target] = sum(v for _, v in parts)
            elif field in ('incomeMedian', 'incomeSe', 'floorMedian'):
                out[target] = None          # 中位數與標準差併不起來，不編一個數字
            else:
                total = sum(weights[n] for n, _ in parts)
                out[target] = round(sum(v * weights[n] for n, v in parts) / total, 4)
        merged[field] = out
    return merged, problems


def quintiles():
    """最新一年的所得五等分位居住條件。欄位是總平均與第 1 至第 5 分位，位置固定。"""
    def grab(rows, pattern):
        pat = re.compile(pattern)
        for row in rows:
            if any(pat.fullmatch(norm(c)) for c in row):
                nums = [norm(c) for c in row if NUM.match(norm(c))]
                if len(nums) >= 6:
                    return [float(v) for v in nums[:6]]
        return None

    ten = sheet(path('家庭住宅及主要設備概況依可支配所得按戶數五等分位分', LATEST))
    inc = sheet(path('平均每戶家庭收支依可支配所得按戶數五等分位分', LATEST))
    fields = {}
    for field, pattern in TENURE_ROWS.items():
        fields[field] = grab(ten, pattern)
    fields['persons'] = grab(ten, r'平均每戶人數')
    for field in ('incomeMean', 'consume', 'imputedRent'):
        fields[field] = grab(inc, INCOME_ROWS[field])
    out = []
    for q in range(1, 6):
        rec = {'q': q}
        for field, values in fields.items():
            rec[field] = None if values is None else round(values[q], 4)
        out.append(rec)
    return out


def record(name, roc, panel):
    # 底線開頭的是內部用的全國欄，不是縣市欄位，別讓它漏進輸出
    row = {k: v.get(name) for k, v in panel[roc].items() if not k.startswith('_')}
    mean, se = row.get('incomeMean'), row.get('incomeSe')
    row['ci'] = round(Z * se, 1) if (mean and se) else None
    row['ciPct'] = round(Z * se / mean * 100, 2) if (mean and se) else None
    return row


def main():
    panel, problems = {}, []
    for roc in YEARS:
        raw = read_year(roc)
        if not raw['households']:
            sys.exit(f'{roc}年的第2表讀不到家庭戶數，停下來，不要放行')
        merged, bad = harmonise(roc, raw)
        problems += bad

        # ── 對帳一：縣市加總必須等於表上的總平均欄（AGENTS.md §3）──
        total = raw['households'].get('總平均')
        got = sum(merged['households'].values())
        if total is None or abs(got - total) > 1:
            sys.exit(f'{roc}年家庭戶數對不上：縣市加總 {got:,.0f}、'
                     f'表上總平均 {total}，差 {got - (total or 0):,.0f}')
        if len(merged['households']) != len(COUNTIES):
            sys.exit(f'{roc}年併完只剩 {len(merged["households"])} 個縣市，'
                     f'應該是 {len(COUNTIES)} 個')
        panel[roc] = merged
        panel[roc]['_national'] = {k: v.get('總平均') for k, v in raw.items()}

    # ── 對帳二：住宅權屬四類相加必須是 100%，扣掉 TENURE_GAP 點名過的來源缺口 ──
    seen_gap = set()
    for roc in YEARS:
        for name in COUNTIES:
            parts = [panel[roc][f].get(name) or 0 for f in ('own', 'kin', 'rent', 'other')]
            gap = TENURE_GAP.get((roc, name), 0)
            if gap:
                seen_gap.add((roc, name))
            if abs(sum(parts) - 100 - gap) > 0.05:
                problems.append(f'{roc}年{name}的住宅權屬相加是 {sum(parts):.4f}%，'
                                + (f'記錄的來源缺口是 {gap}，對不上'
                                   if gap else '不是 100%，而且不在 TENURE_GAP 名單裡'))
    for key in set(TENURE_GAP) - seen_gap:
        problems.append(f'TENURE_GAP 記了 {key} 的缺口，但這一年這個縣市已經對得上了')

    # ── 對帳三：可支配所得 = 消費支出 + 儲蓄 ──
    for roc in YEARS:
        for name in COUNTIES:
            mean = panel[roc]['incomeMean'].get(name)
            parts = [panel[roc][f].get(name) for f in ('consume', 'saving')]
            if mean and all(p is not None for p in parts) and abs(sum(parts) - mean) > 2:
                problems.append(f'{roc}年{name}：消費支出＋儲蓄 {sum(parts):,.0f} '
                                f'不等於可支配所得 {mean:,.0f}')

    if problems:
        for line in problems[:20]:
            print('  ✗', line)
        sys.exit(f'對帳沒過，共 {len(problems)} 筆。修資料或修解析，不要放寬容差。')

    nat = {k: panel[LATEST]['_national'][k] for k in
           list(INCOME_ROWS) + list(TENURE_ROWS)}
    nat['ci'] = round(Z * nat['incomeSe'], 1)
    nat['ciPct'] = round(Z * nat['incomeSe'] / nat['incomeMean'] * 100, 2)
    nat['series'] = {f: [panel[y]['_national'][f] for y in YEARS]
                     for f in ('incomeMean', 'incomeMedian', 'own', 'kin', 'rent',
                               'other', 'floorMean', 'floorMedian', 'persons',
                               'consume', 'imputedRent')}

    counties = []
    for name in COUNTIES:
        rec = record(name, LATEST, panel)
        rec['name'] = name
        rec['series'] = {f: [panel[y][f].get(name) for y in YEARS]
                         for f in ('incomeMean', 'incomeMedian', 'own', 'kin', 'rent',
                                   'other', 'floorMean', 'floorMedian', 'persons',
                                   'households')}
        counties.append(rec)

    blob = {
        'period': f'民國{LATEST}年（{LATEST + 1911}）',
        'source': '行政院主計總處《家庭收支調查報告》民國83年至114年，第2表、第8表、第10表',
        'years': YEARS,
        'notInSurvey': NOT_IN_SURVEY,
        'z': Z,
        'caveat': ('縣市別樣本有限，主計總處在表末自陳「若據以作縣市排名，不具嚴謹統計'
                   '意義」，誤差幅度從全國的 ±3.9% 到新竹縣的 ±41.7%，讀這份資料要先看'
                   '誤差線再看排序；調查不含金門縣與連江縣；可支配所得與消費支出兩邊都'
                   '含自用住宅設算租金，不是現金所得。'),
        'breaks': [
            {'year': BREAK_TENURE, 'field': 'own',
             'what': '住宅所有權把「自有」拆成自有與不住在一起的配偶、父母或子女所擁有，'
                     '98年自有 87.89%、99年 84.89%，落差是分類改變而非自有率下跌；'
                     '可比的口徑是兩者相加，或直接看非租押比率。'},
            {'year': BREAK_FLOOR, 'field': 'floorMean',
             'what': '建坪的定義從「僅含自家陽台」改成「不含公共設施、陽台及露臺」，'
                     '每戶建坪平均數因此從 111年的 45.1 坪掉到 112年的 40.06 坪，'
                     '同期平均每戶人數只從 2.83 動到 2.79，那 5 坪是量法變了。'},
            {'year': BREAK_MERGE, 'field': 'name',
             'what': '縣市改制，98年以前表上是 23 個縣市。舊資料以家庭戶數加權併入'
                     '今天的縣市；臺中、臺南、高雄三市在 98年以前的所得中位數與標準差'
                     '無法由兩個子群回推，一律 null。'},
        ],
        'national': nat,
        'counties': counties,
        'quintiles': quintiles(),
    }
    OUT.write_text(json.dumps(blob, ensure_ascii=False, indent=1), encoding='utf-8')

    kept = tally['納入面板']
    dropped = sum(v for k, v in tally.items() if k.startswith('排除'))
    if kept + dropped != tally['讀入的儲存格']:
        sys.exit(f'交代不過去：讀入 {tally["讀入的儲存格"]}、納入 {kept}、排除 {dropped}')
    print(f'{OUT.name}：{len(YEARS)} 個年度 × {len(COUNTIES)} 個縣市')
    print(f'  讀入儲存格 {tally["讀入的儲存格"]:,}＝納入 {kept:,}＋'
          + '＋'.join(f'{k[3:]} {v:,}' for k, v in tally.items() if k.startswith('排除')))
    print(f'  {LATEST}年可支配所得中位數：全國 {nat["incomeMedian"]:,.0f} 元、'
          f'誤差 ±{nat["ciPct"]}%')
    print(f'  租押比率：{YEARS[0]}年 {nat["series"]["rent"][0]}% → '
          f'{LATEST}年 {nat["series"]["rent"][-1]}%')


if __name__ == '__main__':
    main()
