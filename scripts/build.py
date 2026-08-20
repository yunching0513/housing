#!/usr/bin/env python3
"""Inline the prepared datasets into the page templates.

輸出兩份，用途不同，不要合併：

    dist/   片段。沒有 doctype 與 head，因為 artifact 發布時平臺會自己包一層，
            自己再包一次會被解析器丟掉。
    site/   完整文件。有 doctype、lang、charset 與分享用的 meta，另外多一條
            跨頁導覽列。這是要放上網站的那一份。

兩份都是單一檔案、資料內嵌、零外部請求。
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
SITE = ROOT / 'site'
SITE_NAME = '社宅該蓋在哪'

# 每一頁列出它要的資料檔。樣式共用，兩頁才不會在視覺上分岔。
PAGES = {
    # 網站根目錄要 index.html，所以入口頁的檔名就是 index.html；
    # 原本叫 index 的「臺灣住宅供需圖」改名 supply，避免兩者搶同一個位置。
    'index.html': ('entry.template.html', {
        '__OV_JSON__': 'tw_overview.json',
    }),
    'supply.html': ('supply.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__POP_JSON__': 'tw_population.json',
        '__HOU_JSON__': 'tw_housing.json',
    }),
    'town.html': ('town.template.html', {
        '__TGEO_JSON__': 'tw_towns.json',
        '__TDAT_JSON__': 'tw_town_data.json',
    }),
    'metro.html': ('metro.template.html', {
        '__TGEO_JSON__': 'tw_towns.json',
        '__TDAT_JSON__': 'tw_town_data.json',
    }),
    'trend.html': ('trend.template.html', {
        '__SER_JSON__': 'tw_moi_series.json',
    }),
    'social.html': ('social.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__SOC_JSON__': 'tw_social_housing.json',
        '__HOU_JSON__': 'tw_housing.json',
    }),
    'signal.html': ('signal.template.html', {
        '__TGEO_JSON__': 'tw_towns.json',
        '__SIG_JSON__': 'tw_signal.json',
    }),
    'build.html': ('build.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__BLD_JSON__': 'tw_social_build.json',
    }),
    'rent.html': ('rent.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__RENT_JSON__': 'tw_rent.json',
    }),
    'county.html': ('county.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__PROF_JSON__': 'tw_county_profile.json',
        '__FIES_JSON__': 'tw_fies.json',
    }),
    'priority.html': ('priority.template.html', {
        '__AFF_JSON__': 'tw_affordability.json',
        '__HOU_JSON__': 'tw_housing.json',
        '__POP_JSON__': 'tw_population.json',
        '__PSER_JSON__': 'tw_pop_series.json',
    }),
}


def esc(text):
    return (text.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))


def page_meta():
    """每一頁的標題與說明，取自 tw_overview.json，不在這裡另寫一份。

    入口頁本身不在那份清單裡（它是清單的容器），所以單獨補一筆。
    """
    ov = json.loads((ROOT / 'data' / 'tw_overview.json').read_text(encoding='utf-8'))
    meta = {p['file']: (p['title'], f"{p['asks']}：{p['says']}") for p in ov['pages']}
    meta['index.html'] = (
        SITE_NAME,
        f"把人實際住在哪跟房子實際空在哪放在同一張圖上。"
        f"{ov['built']['pages']}頁、{ov['built']['sources']}份政府資料、"
        f"{ov['built']['counties']}縣市與{ov['built']['towns']}鄉鎮市區。")
    return meta


def nav_html(current, meta):
    """跨頁導覽。順序與入口頁的問題順序一致，由同一份資料決定。"""
    order = ['index.html'] + [f for f in meta if f != 'index.html']
    items = []
    for f in order:
        title = '入口' if f == 'index.html' else meta[f][0]
        cur = ' aria-current="page"' if f == current else ''
        items.append(f'<a href="{f}"{cur}>{esc(title)}</a>')
    return ('<nav class="sitenav" aria-label="頁面導覽">'
            + ''.join(items) + '</nav>')


def build(out_name, template_name, tokens, meta):
    html = (ROOT / 'src' / template_name).read_text(encoding='utf-8')
    html = html.replace('__SHARED_CSS__', (ROOT / 'src' / 'shared.css').read_text(encoding='utf-8'))
    # 只有畫地圖的頁面會用到，所以這裡是單純的取代，找不到 token 也不算錯。
    html = html.replace('__MAP_ZOOM_JS__', (ROOT / 'src' / 'mapzoom.js').read_text(encoding='utf-8'))
    for token, filename in tokens.items():
        if token not in html:
            sys.exit(f'{template_name} is missing {token}')
        blob = json.dumps(json.loads((ROOT / 'data' / filename).read_text(encoding='utf-8')),
                          ensure_ascii=False, separators=(',', ':'))
        assert '</script' not in blob.lower(), f'{filename} would close the script tag'
        html = html.replace(token, blob)

    DIST.mkdir(exist_ok=True)
    (DIST / out_name).write_text(html, encoding='utf-8')

    # ── 網站版：包成完整文件，並插入導覽列 ──
    title, desc = meta.get(out_name, (out_name, SITE_NAME))
    body = re.sub(r'^<title>.*?</title>\s*', '', html, count=1, flags=re.S)
    assert body.count('<div class="wrap">') == 1, f'{template_name} 的 .wrap 不只一個'
    body = body.replace('<div class="wrap">',
                        '<div class="wrap">\n' + nav_html(out_name, meta), 1)
    # 入口頁的標題就是站名，接一次就好，不要變成「社宅該蓋在哪｜社宅該蓋在哪」
    head_title = esc(title) if title == SITE_NAME else f'{esc(title)}｜{esc(SITE_NAME)}'
    doc = (
        '<!doctype html>\n<html lang="zh-Hant">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{head_title}</title>\n'
        f'<meta name="description" content="{esc(desc)}">\n'
        '<meta property="og:type" content="website">\n'
        f'<meta property="og:site_name" content="{esc(SITE_NAME)}">\n'
        f'<meta property="og:title" content="{esc(title)}">\n'
        f'<meta property="og:description" content="{esc(desc)}">\n'
        '<meta name="twitter:card" content="summary">\n'
        '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    SITE.mkdir(exist_ok=True)
    (SITE / out_name).write_text(doc, encoding='utf-8')
    print(f'  {out_name:14s} dist {len(html.encode()) / 1024:5.0f} KB'
          f'　site {len(doc.encode()) / 1024:5.0f} KB')


def main():
    meta = page_meta()
    print('內嵌並產出：')
    for out_name, (template, tokens) in PAGES.items():
        if (ROOT / 'src' / template).exists():
            build(out_name, template, tokens, meta)
    # Jekyll 會吃掉底線開頭的檔案，這個站沒有那種檔名，放著是為了以後也不會有
    (SITE / '.nojekyll').write_text('', encoding='utf-8')
    print(f'dist/ 給 artifact 發布用（片段），site/ 給網站用（完整文件、含導覽列）')


if __name__ == '__main__':
    main()
