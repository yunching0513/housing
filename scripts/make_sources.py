#!/usr/bin/env python3
"""Resolve a curated source list out of the data.gov.tw catalogue into sources.json.

The catalogue export is ~69 MB and changes daily, so it is not committed. This
script freezes the picks — dataset id, title, agency, and every download URL —
into a small manifest that fetch_sources.py can replay anywhere.

    curl -o catalog.csv https://data.gov.tw/datasets/export/csv
    python3 scripts/make_sources.py catalog.csv
"""
import csv, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'sources.json'

COUNTY = (r'新北市|臺北市|桃園[市縣]|臺中[市縣]|臺南[市縣]|高雄[市縣]|基隆市|新竹[市縣]|'
          r'嘉義[市縣]|宜蘭縣|苗栗縣|彰化縣|南投縣|雲林縣|屏東縣|臺東縣|花蓮縣|澎湖縣|金門縣|連江縣')

# Curated picks, by analysis category rather than by agency.
PICKS = [
    # ── 01 人口分布 ──────────────────────────────────────────────────────────
    ('01_人口分布/普查_全國', '10906', '人口及住宅普查（常住人口數及人口密度，99 與 109 年）'),
    ('01_人口分布/普查_全國', '24238', '常住人口數及人口密度'),
    ('01_人口分布/普查_全國', '24759', '住戶數、常住人口數及平均每戶人口數'),
    ('01_人口分布/普查_全國', '24240', '常住人口之年齡結構（不含移工）'),
    ('01_人口分布/普查_全國', '24239', '常住人口之性比例（不含移工）'),
    ('01_人口分布/普查_全國', '24244', '５歲以上常住人口之遷徙情形'),
    ('01_人口分布/普查_全國', '24282', '６歲以上常住人口之工作地及就學地狀況'),
    ('01_人口分布/普查_全國', '24241', '１５歲以上常住人口之教育程度'),
    ('01_人口分布/普查_全國', '24243', '１５歲以上民間常住人口之工作狀況'),
    # ── 02 住宅存量 ──────────────────────────────────────────────────────────
    ('02_住宅存量/普查', '24783', '住宅單位數（含空閒住宅）'),
    ('02_住宅存量/房屋稅籍', '20342', '臺閩地區房屋稅籍所有人歸戶統計表'),
    # ── 03 人口動態（普查十年一次，這裡放年度／月度的替代來源） ─────────────
    ('03_人口動態_電信信令', '160179', '各縣市電信信令人口統計－夜間停留人口'),
    ('03_人口動態_電信信令', '160180', '各縣市電信信令人口統計－日間活動人口'),
    ('03_人口動態_電信信令', '160178', '各縣市電信信令人口統計－特定區域旅次'),
    # 戶籍人口是唯一能做到每月、每村里的序列；戶數尤其重要，住宅需求是以戶計。
    ('03_人口動態_戶籍/村里月報', '8411',  '各村（里）戶籍人口統計月報表'),
    ('03_人口動態_戶籍/村里月報', '77140', '各村（里）戶籍人口統計月報表（新增區域代碼）'),
    ('03_人口動態_戶籍/村里戶數', '77132', '村里戶數、單一年齡人口（新增區域代碼）'),
    ('03_人口動態_戶籍/村里戶數', '32973', '村里戶數、單一年齡人口'),
    ('03_人口動態_戶籍/鄉鎮市區', '8410',  '各鄉鎮市區人口密度'),
    # ── 04 住宅政策 ──────────────────────────────────────────────────────────
    ('04_住宅政策_中央', '73250',  '住宅補貼辦理概況'),
    ('04_住宅政策_中央', '169800', '接受住宅補貼戶次及金額'),
    ('04_住宅政策_中央', '164857', '公益出租人稅賦減徵戶數統計表'),
    ('04_住宅政策_中央', '21232',  '住宅建設下載專區'),
    ('04_住宅政策_中央', '147535', '國有非公用不動產保留供興辦社會住宅清冊'),
    # ── 05 社會住宅（地方政府） ─────────────────────────────────────────────
    ('05_社會住宅_地方', '149652', '桃園市社會住宅名稱與戶數'),
    ('05_社會住宅_地方', '149586', '桃園市社會住宅基地地號及面積表'),
    ('05_社會住宅_地方', '130113', '臺南市社會住宅案地及戶數資料'),
    ('05_社會住宅_地方', '142745', '臺南市社會住宅包租代管辦理廠商資訊'),
    ('05_社會住宅_地方', '155779', '臺北市政府社會住宅包租代管媒合統計資料'),
    ('05_社會住宅_地方', '84140',  '臺中市社會住宅基地地號及面積表'),
    ('05_社會住宅_地方', '166888', '高雄市社會住宅包租代管統計'),
    ('05_社會住宅_地方', '165798', '109 年臺東縣社會住宅'),
]

# County breakdowns of these census tables give 鄉鎮市區 detail — the level social
# housing siting actually happens at.
COUNTY_TABLES = [
    '住宅單位數',
    '常住人口數及人口密度',
    '住戶數、常住人口數及平均每戶人口數',
    '５歲以上常住人口之遷徙情形',
    '６歲以上常住人口之工作地及就學地狀況',
]

EXTRA = [{
    'category': '06_地理圖資',
    'dataset_id': None,
    'title': '臺灣縣市界圖資（2010 年界線）',
    'agency': 'g0v twgeojson',
    'update': '不定期',
    'urls': ['https://raw.githubusercontent.com/g0v/twgeojson/master/json/twCounty2010.geo.json'],
}]

# ── 08 家庭收支調查（民國83年至114年）───────────────────────────────────────
# 這一批不在 data.gov.tw 的目錄裡，是報告頁的直接連結，所以走 EXTRA 而非 PICKS。
#   https://www.stat.gov.tw/News.aspx?n=3908&sms=11530
# 一律取 .ods/.odt 不取 .xls/.doc：後者是 OLE2 二進位，沒有第三方套件讀不動；
# 前者是 zip 內含 content.xml，用內建函式庫就拆得開（AGENTS.md §4）。
#
# 檔案散在兩個位置，同一年還會混用，找不出規律，所以逐年照抄目錄頁上的實際連結：
#   U＝ .../001/Upload/463/relfile/11530/{編號}/    W＝ .../win/fies/doc/result/{民國年}/a11/
FIES_U = 'https://ws.dgbas.gov.tw/001/Upload/463/relfile/11530/{sid}'
FIES_W = 'https://ws.dgbas.gov.tw/win/fies/doc/result/{roc}/a11'
FIES_SID = {
    114: '236588', 113: '235198', 112: '233680', 111: '231908', 110: '230826', 109: '235896',
    108: '210988', 107: '210987', 106: '210986', 105: '210985', 104: '210984', 103: '210983',
    102: '210982', 101: '210981', 100: '210980', 99: '210979', 98: '210978', 97: '210977',
    96: '210976', 95: '210975', 94: '210974', 93: '210973', 92: '210972', 91: '210971',
    90: '210970', 89: '210969', 88: '210968', 87: '210966', 86: '210965', 85: '210964',
    84: '210963', 83: '210962',
}

# 橫斷面表：17 張，83 至 114 年檔名完全一致（數字是印刷本的頁碼，不是表次）。
# 表次反而逐年變動，例如「所得收入者平均每人所得來源按職業別分」早年排第三表、
# 近年排第二表，所以檔名只留內容不留表次，同一張表三十二年才串得起來。
# 61、101、117 這三張在民國 90 年代之前還多切一層「都市化程度別」，欄位會比較多。
FIES_CROSS = [
    ('45',  '平均每戶家庭收支按戶內人數分'),
    ('49',  '平均每戶家庭收支按區域別分'),
    ('61',  '平均每戶家庭收支按農家非農家分'),
    ('65',  '平均每戶家庭收支按經濟戶長職業別分'),
    ('73',  '平均每戶家庭收支按家庭組織型態別分'),
    ('77',  '平均每戶家庭收支依可支配所得按戶數五等分位分'),
    ('81',  '平均每戶可支配所得及消費支出按五等分位及戶長性別年齡教育程度分'),
    ('87',  '家庭戶數按所得總額組別及經濟戶長性別分'),
    ('89',  '家庭住宅及主要設備概況按區域別分'),
    ('101', '家庭住宅及主要設備概況按農家非農家分'),
    ('105', '家庭住宅及主要設備概況依可支配所得按戶數五等分位分'),
    ('111', '所得收入者平均每人所得來源按區域別分'),
    ('117', '所得收入者平均每人所得來源按農家非農家分'),
    ('119', '所得收入者平均每人所得來源按職業別分'),
    ('123', '所得收入者平均每人所得來源依可支配所得按五等分位分'),
    ('125', '所得收入者平均每人可支配所得按五等分位及性別年齡教育程度分'),
    ('129', '所得收入者人數按性別及可支配所得組別分'),
]
# 108 年的橫斷面表沒放進 Upload，只有舊路徑找得到；主計總處自己的目錄頁也是連舊路徑。
FIES_CROSS_W = {108}

# 歷年表：每一年的報告都附一份，內容是到當年為止的完整序列，後一年是前一年的超集，
# 所以只取最新的 114 年，不逐年重複收三十份一模一樣的東西。
FIES_YEAR_LATEST = 114
FIES_SERIES = [
    ('Index',  '重要指標'),
    ('Year01', '所得總額與可支配所得'),
    ('Year02', '所得總額按來源別分'),
    ('Year03', '戶數五等分位組之平均每戶可支配所得'),
    ('Year04', '戶數五等分位組之所得分配比與所得差距'),
    ('Year05', '人數五等分位組之所得差距'),
    ('Year06', '政府對家庭移轉收支對所得分配之影響'),
    ('Year07', '戶數十等分位組分界點之可支配所得'),
    ('Year08', '人數十等分位組分界點之可支配所得'),
    ('Year09', '世界各國家地區所得分配狀況'),
    ('Year10', '可支配所得消費支出及儲蓄'),
    ('Year11', '戶數五等分位組之平均每戶消費支出'),
    ('Year12', '戶數五等分位組之平均每戶儲蓄'),
    ('Year13', '平均每戶及每位所得收入者之可支配所得按性別分'),
    ('Year14', '家庭消費支出結構按消費型態分'),
    ('Year15', '農家與非農家平均每戶及每人可支配所得'),
    ('Year16', '農家平均每戶所得總額按來自農業與非農業分'),
    ('Year17', '所得收入者五等分位組之可支配所得分配比與所得差距'),
    ('Year18', '所得收入者十等分位組分界點之可支配所得'),
    ('Year19', '所得收入者平均每人可支配所得及中位數所得按行業別分'),
    ('Year20', '所得收入者平均每人可支配所得及中位數所得按職業別分'),
    ('Year21', '所得收入者平均每人可支配所得及中位數所得按教育程度別分'),
    ('Year22', '所得收入者之基本所得及人數按縣內縣外工作地點分'),
    ('Year23', '所得收入者人數與按年齡組別及性別之分配'),
    ('Year24', '家庭住宅狀況'),
    ('Year25', '家庭主要設備普及率'),
    ('Year26', '年中戶數與平均每戶人數就業人數按農家非農家分'),
    ('Year27', '戶數五等分位組之平均每戶人數與就業人數'),
    ('Year28', '家庭戶數按戶內人口規模別之分配'),
    ('Year29', '就業者平均每人基本所得按職業別分'),
]

# 附錄逐年都收，理由是定義本身會變。每戶居住坪數的平均數在 110 年是 45.0 坪、
# 112 年只剩 40.1 坪，兩年掉掉近 5 坪，要判斷那是真實變化還是改了定義或抽樣，
# 只能翻當年的《調查方法》與《名詞解釋》，翻最新一版沒有用。
FIES_DOC_NAME = {
    'Preface': '前言', 'Analysis': '綜合分析', 'Definec': '附錄_名詞解釋',
    'Methodc': '附錄_調查方法', 'Appendce': '附錄_未刊印之結果表',
    'Questc': '附錄_調查表格式', 'appendix5': '附錄_高所得者所得占比',
    'appendix6': '附錄_我國綜合所得稅申報統計',
    'preface': '前言', 'methodc': '附錄_調查方法',   # 84、85、96、97 年的手誤檔名
}
# 各年提供的附錄不同：83 至 103 年六份，104 年起多了高所得者所得占比，
# 109 至 110 年再多一份綜合所得稅申報統計，111 年起又收掉。
# 前綴 * 表示這一份放在 U，其餘放在 W；少數幾份的大小寫與位置跟同年其他份不一致
# （97 年的 methodc、96 年的 preface 之類），是上傳時的手誤，照實記，不要用規則推。
FIES_DOCS = {
    114: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5',
    113: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5',
    112: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5',
    111: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5',
    110: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5 *appendix6',
    109: '*Preface *Analysis *Definec *Methodc *Appendce *Questc *appendix5 *appendix6',
    108: 'Preface *Analysis Definec Methodc Appendce Questc appendix5',
    107: 'Preface *Analysis Definec Methodc Appendce Questc appendix5',
    106: 'Preface Analysis Definec Methodc Appendce Questc appendix5',
    105: 'Preface Analysis Definec Methodc Appendce Questc appendix5',
    104: 'Preface Analysis Definec Methodc Appendce Questc appendix5',
    103: 'Preface Analysis Definec Methodc Appendce Questc',
    102: 'Preface Analysis Definec Methodc Appendce Questc',
    101: 'Preface Analysis Definec Methodc Appendce Questc',
    100: 'Preface Analysis Definec Methodc Appendce Questc',
    99: 'Preface Analysis Definec Methodc Appendce Questc',
    98: 'Preface Analysis Definec Methodc Appendce Questc',
    97: '*Preface Analysis Definec *methodc Appendce Questc',
    96: '*preface Analysis Definec Methodc Appendce Questc',
    95: 'Preface Analysis Definec Methodc Appendce Questc',
    94: 'Preface Analysis Definec Methodc Appendce Questc',
    93: 'Preface Analysis Definec Methodc Appendce Questc',
    92: 'Preface Analysis Definec Methodc Appendce Questc',
    91: 'Preface Analysis Definec Methodc Appendce Questc',
    90: 'Preface Analysis Definec Methodc Appendce Questc',
    89: 'Preface Analysis Definec Methodc Appendce Questc',
    88: 'Preface Analysis Definec Methodc Appendce Questc',
    87: 'Preface Analysis Definec Methodc Appendce Questc',
    86: 'Preface Analysis Definec Methodc Appendce Questc',
    85: 'Preface Analysis Definec *methodc Appendce Questc',
    84: '*preface Analysis Definec Methodc Appendce Questc',
    83: 'Preface Analysis Definec Methodc Appendce Questc',
}


def fies():
    """民國83年至114年家庭收支調查的檔案清單。

    檔名把年度擺在最後：`家庭收支調查_{表名}_民國{年}年.ods`。
    這樣同一張表的三十二年會排在一起，一個萬用字元就抓得到整條年度序列；
    年度擺前面的話，臺北市的資料會夾在 100 年與 83 年中間，反而不好用。
    """
    out = []
    for roc, sid in FIES_SID.items():
        u, w = FIES_U.format(sid=sid), FIES_W.format(roc=roc)
        picks = [(w if roc in FIES_CROSS_W else u, stem, name, 'ods')
                 for stem, name in FIES_CROSS]
        picks += [((u if s.startswith('*') else w), s.lstrip('*'),
                   FIES_DOC_NAME[s.lstrip('*')], 'odt')
                  for s in FIES_DOCS[roc].split()]
        if roc == FIES_YEAR_LATEST:
            picks += [(u, stem, '歷年_' + name, 'ods') for stem, name in FIES_SERIES]
        out += [{
            'category': '08_家庭收支調查',
            'dataset_id': None,
            'title': f'家庭收支調查_{name}_民國{roc}年',
            'agency': '行政院主計總處',
            'update': '每年',
            'urls': [f'{base}/{stem}.{ext}'],
        } for base, stem, name, ext in picks]
    return out


EXTRA += fies()


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'catalog.csv')
    csv.field_size_limit(10 ** 9)
    rows = {r['資料集識別碼']: r for r in csv.DictReader(src.open(encoding='utf-8-sig'))}

    def entry(cat, did, title=None):
        r = rows.get(did)
        if not r:
            print(f'  !! dataset {did} not in catalogue', file=sys.stderr)
            return None
        return {
            'category': cat,
            'dataset_id': did,
            'title': title or r['資料集名稱'],
            'catalogue_title': r['資料集名稱'],
            'agency': r['提供機關'],
            'update': r['更新頻率'],
            'urls': [u.strip() for u in r['資料下載網址'].split(';') if u.strip()],
        }

    out = [e for e in (entry(c, d, t) for c, d, t in PICKS) if e]

    pat = re.compile(COUNTY)
    for r in rows.values():
        nm = r['資料集名稱']
        m = pat.match(nm)
        if not m or nm[m.end():] not in COUNTY_TABLES:
            continue
        if '/open/Cen/' not in r['資料下載網址'] and 'ws.dgbas' not in r['資料下載網址']:
            continue
        e = entry(f'01_人口分布/普查_縣市/{m.group(0)}'
                  if nm[m.end():] != '住宅單位數' else f'02_住宅存量/普查_縣市/{m.group(0)}',
                  r['資料集識別碼'])
        if e:
            out.append(e)

    out.extend(EXTRA)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')

    files = sum(len(e['urls']) for e in out)
    print(f'{OUT.name}: {len(out)} 個資料集 / {files} 個檔案')
    for cat in sorted({e['category'].split('/')[0] for e in out}):
        n = sum(len(e['urls']) for e in out if e['category'].startswith(cat))
        print(f'  {cat:24s} {n:4d} 檔')


if __name__ == '__main__':
    main()
