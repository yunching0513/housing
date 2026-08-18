#!/usr/bin/env python3
"""從實價登錄的租賃案件算出各縣市的租金中位數。

    python3 scripts/prep_rent.py

資料來源是 data_TW/99-115 不動產買賣及租賃/ 底下的 *_lvr_land_c.xml，
一年一個批次、每批次是同一個春季的三個月視窗（詳見各批次的 build_time.xml
或 build.ttt）。同一個季節逐年比較，季節性已經受控。

為什麼算中位數不算平均：
    租金的分布是右偏的，一筆整棟商辦可以是一般住家的三百倍
    （114 年最高一筆月租 858 萬）。中位數不受極端值影響，
    所以這支程式**不修剪極端值**，只排除明顯的資料錯誤（面積或租金為零）。
    少一道人為判斷，就少一個可以被悄悄調鬆的參數。

三個一定要先講清楚的限制：
  1. 實價登錄的租賃申報**不是市場的隨機樣本**。依租賃住宅市場發展及管理條例，
     負有申報義務的主要是租賃住宅服務業經手的案件；房東自租大多不在裡面。
  2. 樣本量從 102 年的 4,686 筆長到 114 年的 43,036 筆，成長九倍。
     那是申報範圍在變，不是市場在變。**逐年數列不能當市場租金趨勢讀。**
  3. 「出租型態」與「租賃住宅服務」兩個欄位 113 年才出現。
     所以「社宅包租代管 vs 一般」的比較只有 113、114 兩年做得出來。
"""
import collections, json, pathlib, statistics, sys, xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'data_TW' / '99-115 不動產買賣及租賃'
OUT = ROOT / 'data' / 'tw_rent.json'

ALL_COUNTIES = set()          # 由 all_counties() 在 main() 開頭填入
PING = 400 / 121          # 1 坪 = 400/121 平方公尺 ≈ 3.3058
MIN_SAMPLE = 30           # 少於這個數的中位數是雜訊，一律記 null 而不是照算
MIN_RENT = 1000           # 月租低於一千元不是市場成交（0 元、1 元的象徵性租約真的有）
MIN_AREA = 3.0            # 平方公尺。比一個車位還小的「住宅」是登打錯誤

# 每個批次資料夾對到它的資料年。批次期間寫在各資料夾的 build_time.xml／build.ttt，
# 這裡只記年份；完整期間字串由 PERIODS 提供，兩者對不上會在 main() 裡中止。
BATCH_YEAR = {
    'lvr_landxml (12)': 102, 'lvr_landxml (11)': 103, 'lvr_landxml (10)': 104,
    'lvr_landxml (9)': 105, 'lvr_landxml (8)': 106, 'lvr_landxml (7)': 107,
    'lvr_landxml (6)': 108, 'lvr_landxml (5)': 109, 'lvr_landxml (4)': 110,
    'lvr_landxml (3)': 111, 'lvr_landxml (2)': 112, 'lvr_landxml (1)': 113,
    '114不動產成交案件實際資訊（含買賣、租賃及預售屋）': 114,
}
# 租賃案件的訂約／申報日期區間，逐字抄自各批次的 build_time.xml／build.ttt。
PERIODS = {
    102: '102年2月1日至4月30日', 103: '103年2月1日至4月30日',
    104: '104年2月1日至4月30日', 105: '105年2月1日至4月30日',
    106: '106年2月1日至4月30日', 107: '107年2月11日至5月10日',
    108: '108年2月11日至5月10日', 109: '109年2月11日至5月10日',
    110: '110年2月11日至5月10日', 111: '111年2月11日至5月10日',
    112: '112年2月11日至5月10日', 113: '113年2月11日至5月10日',
    114: '114年2月11日至5月10日',
}

# 住宅類建物型態。店面、辦公商業大樓、廠辦、工廠、倉庫、農舍、其他一律排除：
# 一間店面的租金跟一戶住家的租金放在同一個中位數裡，那個中位數就沒有意義了。
RESIDENTIAL = {
    '住宅大樓(11層含以上有電梯)', '華廈(10層含以下有電梯)',
    '公寓(5樓含以下無電梯)', '透天厝', '套房(1房1廳1衛)',
}
NON_RESIDENTIAL = {'店面(店鋪)', '辦公商業大樓', '廠辦', '工廠', '倉庫', '農舍', '其他', ''}

# 交易標的的用語 113 年換過一次（建物／房地(土地+建物) → 租賃房屋），
# 所以這裡列的是「要排除的」而不是「要保留的」，換皮不會讓篩選失效。
SUBJECT_DROP = {'土地', '車位'}
SUBJECT_KNOWN = SUBJECT_DROP | {
    '建物', '房地(土地+建物)', '房地(土地+建物)+車位', '租賃房屋', '租賃房屋+車位',
}

# 出租型態：整棟（戶）與獨立套房各自是一個「可以住一戶的完整單元」，
# 分租套房／雅房是一個單元裡的一個房間，兩者的月租金不能放進同一個中位數。
UNIT_KIND = {
    '整棟(戶)出租': 'whole', '獨立套房': 'studio',
    '分租套房': 'room', '分租雅房': 'room',
    '分層出租': 'floor', '': 'unknown',
}
# 租賃住宅服務：社宅包租代管的租金是政策價（房東減租、政府補貼），
# 跟一般案件混在一起算，就等於用政策價去描述市場。
SERVICE_GROUP = {
    '社會住宅包租轉租': 'social', '社會住宅代管': 'social',
    '一般轉租': 'agency', '一般代管': 'agency', '一般包租': 'agency',
    '': 'other',
}


def all_counties():
    """22 個縣市的權威清單以普查為準，不在這支程式裡另寫一份。

    manifest 的縣市名只要有一個對不上（例如又出現「臺北縣」），就會在 main() 中止，
    而不是安靜地多出一個沒人看得到的縣市。
    """
    census = ROOT / 'data' / 'tw_housing.json'
    if not census.exists():
        sys.exit('缺少 data/tw_housing.json，請先跑 python3 scripts/prep_housing.py')
    return {c['name'] for c in json.loads(census.read_text(encoding='utf-8'))['counties']}


def num(text):
    """把欄位轉成數字。空白與非數字一律當 0，由呼叫端決定要不要排除。"""
    try:
        return float((text or '').strip() or 0)
    except ValueError:
        return 0.0


def county_of(folder):
    """從批次的 manifest.csv 讀出每個檔案是哪個縣市。

    不自己寫一份「a 是臺北市」的對照表：那份表放久了會跟資料脫節，
    而 manifest 是跟著資料一起發布的，錯了會當場對不上普查的縣市名。
    """
    out = {}
    man = folder / 'manifest.csv'
    if not man.exists():
        sys.exit(f'{folder.name} 少了 manifest.csv，無法判斷檔案屬於哪個縣市')
    for line in man.read_text(encoding='utf-8-sig').splitlines()[1:]:
        parts = line.split(',')
        if len(parts) < 3 or not parts[0].endswith('_lvr_land_c.xml'):
            continue
        out[parts[0]] = parts[-1].replace('不動產租賃', '').strip()
    return out


def read_batch(folder, year, tally):
    """讀一個批次的所有租賃檔，回傳通過篩選的紀錄。"""
    rows = []
    names = county_of(folder)
    for xml in sorted(folder.glob('?_lvr_land_c.xml')):
        county = names.get(xml.name)
        if not county:
            sys.exit(f'{folder.name}/{xml.name} 不在 manifest 裡')
        for _, el in ET.iterparse(xml, events=('end',)):
            if el.tag != '租賃':
                continue          # 不要 clear 子元素，會把父元素的內容一起清掉
            tally['讀入'] += 1

            subject = (el.findtext('交易標的') or '').strip()
            if subject not in SUBJECT_KNOWN:
                sys.exit(f'{year} 年出現沒看過的交易標的「{subject}」，'
                         f'欄位定義可能改了，先確認再放行')
            kind = (el.findtext('建物型態') or '').strip()
            if kind and kind not in RESIDENTIAL and kind not in NON_RESIDENTIAL:
                sys.exit(f'{year} 年出現沒看過的建物型態「{kind}」，先確認再放行')

            if subject in SUBJECT_DROP:
                tally['排除：純土地或純車位'] += 1
            elif kind not in RESIDENTIAL:
                tally['排除：非住宅類建物'] += 1
            else:
                # 總額元與建物總面積都是「含車位」的，扣掉才是房子本身的租金與面積。
                # 驗證方式：單價元平方公尺 ×（總面積−車位面積）≈ 總額−車位總額。
                rent = num(el.findtext('總額元')) - num(el.findtext('車位總額元'))
                area = (num(el.findtext('建物總面積平方公尺'))
                        - num(el.findtext('車位面積平方公尺')))
                if rent < MIN_RENT:
                    tally['排除：租金低於一千元'] += 1
                elif area < MIN_AREA:
                    tally['排除：面積小於三平方公尺'] += 1
                else:
                    town = (el.findtext('鄉鎮市區') or '').strip().replace('台', '臺')
                    rows.append({
                        'county': county,
                        'town': None if town == county else town,
                        'rent': rent,
                        'ping': rent / (area / PING),
                        'area': area / PING,
                        'unit': UNIT_KIND.get((el.findtext('出租型態') or '').strip()),
                        'svc': SERVICE_GROUP.get((el.findtext('租賃住宅服務') or '').strip()),
                    })
                    tally['納入'] += 1
            el.clear()
    return rows


def stats(rows):
    """一組紀錄的三個中位數。樣本不足就整組記 null，不要給一個看起來像數字的雜訊。"""
    n = len(rows)
    if n < MIN_SAMPLE:
        return {'n': n, 'rent': None, 'ping': None, 'area': None}
    med = lambda key: statistics.median(r[key] for r in rows)
    out = {'n': n, 'rent': round(med('rent')), 'ping': round(med('ping')),
           'area': round(med('area'), 1)}
    # 中位數必須落在最小與最大之間。這一條抓的是分組寫錯、把兩組資料混在一起。
    for key in ('rent', 'ping'):
        lo, hi = min(r[key] for r in rows), max(r[key] for r in rows)
        assert lo <= out[key] <= hi, f'{key} 的中位數 {out[key]} 落在 [{lo}, {hi}] 之外'
    return out


def group(rows, field, value):
    return [r for r in rows if r[field] == value]


def grid(rows):
    """出租型態 × 社宅與否的交叉表。

    為什麼一定要交叉而不能只給邊際：114 年有六成的申報案件是社宅包租代管，
    所以「某縣市的整戶月租中位數」其實大半是政策價，直接當市場租金讀會低估。
    分開放，讀的人才知道自己在看哪一個。
    """
    out = {}
    for unit in ('all', 'whole', 'studio', 'room'):
        pool = rows if unit == 'all' else group(rows, 'unit', unit)
        out[unit] = {
            'all': stats(pool),
            'social': stats(group(pool, 'svc', 'social')),
            'nonSocial': stats([r for r in pool if r['svc'] != 'social']),
        }
    return out


def main():
    if not SRC.is_dir():
        sys.exit(f'找不到 {SRC.relative_to(ROOT)}')

    global ALL_COUNTIES
    ALL_COUNTIES = all_counties()
    tally = collections.Counter()
    by_year = {}
    for folder_name, year in sorted(BATCH_YEAR.items(), key=lambda kv: kv[1]):
        folder = SRC / folder_name
        if not folder.is_dir():
            sys.exit(f'找不到批次資料夾 {folder_name}')
        by_year[year] = read_batch(folder, year, tally)
        print(f'  {year} 年（{PERIODS[year]}）：納入 {len(by_year[year]):,} 筆')

    assert set(by_year) == set(PERIODS), '批次年份與期間對照表對不上'
    latest = max(by_year)
    rows = by_year[latest]

    # 對帳①：讀入的每一筆都必須落在「納入」或某一個排除原因裡，不能憑空消失。
    moved = sum(v for k, v in tally.items() if k != '讀入')
    assert moved == tally['讀入'], f'讀入 {tally["讀入"]:,} 筆，只交代了 {moved:,} 筆'

    counties = []
    for name in sorted({r['county'] for r in rows}):
        mine = group(rows, 'county', name)
        rec = {'name': name, **stats(mine)}
        rec['series'] = [{'year': y, **stats(group(by_year[y], 'county', name))}
                         for y in sorted(by_year)]
        # 出租型態與租賃住宅服務兩個欄位 113 年才出現，所以交叉表只有最新這年有。
        rec['grid'] = grid(mine)
        counties.append(rec)
    # 沒有任何申報案件的縣市也要列出來，否則頁面會靜靜少一格，
    # 讀的人分不出是「沒有資料」還是「我漏看了」。
    absent = sorted(ALL_COUNTIES - {c['name'] for c in counties})
    counties += [{'name': n, 'n': 0, 'rent': None, 'ping': None, 'area': None,
                  'series': [{'year': y, 'n': 0, 'rent': None, 'ping': None,
                              'area': None} for y in sorted(by_year)],
                  'grid': grid([])} for n in absent]

    # 對帳②：各縣市筆數加總必須等於全國筆數。
    assert sum(c['n'] for c in counties) == len(rows), '縣市筆數加總對不上全國'
    assert {c['name'] for c in counties} == ALL_COUNTIES, '縣市清單與普查對不上'

    # 鄉鎮市區只給最新這一年。整棟（戶）出租另外算一組：全部案件的每坪租金會被
    # 分租雅房拉高（一個房間的單價本來就比一整戶高），拿去比較縣市內部落差會失真。
    towns = []
    for key in sorted({(r['county'], r['town']) for r in rows if r['town']}):
        mine = [r for r in rows if (r['county'], r['town']) == key]
        if len(mine) >= MIN_SAMPLE:
            towns.append({'county': key[0], 'name': key[1], **stats(mine),
                          'whole': stats(group(mine, 'unit', 'whole'))})

    national = {**stats(rows), 'grid': grid(rows),
                'series': [{'year': y, **stats(by_year[y])} for y in sorted(by_year)],
                'byService': {g: stats(group(rows, 'svc', g))
                              for g in ('social', 'agency', 'other')}}

    data = {
        'period': PERIODS[latest],
        'periods': {str(y): PERIODS[y] for y in sorted(by_year)},
        'years': sorted(by_year),
        'source': '內政部不動產成交案件實際資訊（實價登錄）租賃案件',
        'minSample': MIN_SAMPLE,
        'caveat': ('申報義務主要落在租賃住宅服務業經手的案件，房東自租大多不在裡面；'
                   '樣本量十三年成長九倍是申報範圍在變，逐年數列不能當市場租金趨勢讀。'),
        'national': national,
        'counties': counties,
        'towns': towns,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')),
                   encoding='utf-8')

    print()
    for k in ('讀入', '納入', '排除：純土地或純車位', '排除：非住宅類建物',
              '排除：租金低於一千元', '排除：面積小於三平方公尺'):
        print(f'  {k:<22}{tally[k]:>9,}')
    print(f'\n{OUT.relative_to(ROOT)}：{len(counties)} 縣市、{len(towns)} 鄉鎮市區'
          f'（樣本 ≥ {MIN_SAMPLE}）')
    print(f'  {latest} 年全國月租金中位數 {national["rent"]:,} 元、'
          f'每坪 {national["ping"]:,} 元、面積 {national["area"]} 坪')
    w = national['grid']['whole']
    print(f'  整棟（戶）出租 {w["all"]["n"]:,} 筆：社宅包租代管每坪 {w["social"]["ping"]:,} 元、'
          f'非社宅每坪 {w["nonSocial"]["ping"]:,} 元')


if __name__ == '__main__':
    main()
