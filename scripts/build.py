#!/usr/bin/env python3
"""Inline the prepared datasets into the page template.

The artifact CSP blocks every external request, so the geometry and the
population table have to travel inside the HTML itself.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Each page lists the data files it needs. The stylesheet is shared so the two
# pages cannot drift apart visually.
PAGES = {
    'index.html': ('index.template.html', {
        '__GEO_JSON__': 'tw_counties.json',
        '__POP_JSON__': 'tw_population.json',
        '__HOU_JSON__': 'tw_housing.json',
    }),
    'town.html': ('town.template.html', {
        '__TGEO_JSON__': 'tw_towns.json',
        '__TDAT_JSON__': 'tw_town_data.json',
    }),
}


def build(out_name, template_name, tokens):
    html = (ROOT / 'src' / template_name).read_text(encoding='utf-8')
    html = html.replace('__SHARED_CSS__', (ROOT / 'src' / 'shared.css').read_text(encoding='utf-8'))
    for token, filename in tokens.items():
        if token not in html:
            sys.exit(f'{template_name} is missing {token}')
        blob = json.dumps(json.loads((ROOT / 'data' / filename).read_text(encoding='utf-8')),
                          ensure_ascii=False, separators=(',', ':'))
        assert '</script' not in blob.lower(), f'{filename} would close the script tag'
        html = html.replace(token, blob)
    out = ROOT / 'dist' / out_name
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'{out.relative_to(ROOT)}: {len(html.encode()) / 1024:.0f} KB')


def main():
    for out_name, (template, tokens) in PAGES.items():
        if (ROOT / 'src' / template).exists():
            build(out_name, template, tokens)


if __name__ == '__main__':
    main()
