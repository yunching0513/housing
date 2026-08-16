#!/usr/bin/env python3
"""Inline the prepared datasets into the page template.

The artifact CSP blocks every external request, so the geometry and the
population table have to travel inside the HTML itself.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / 'src' / 'index.template.html'
OUT = ROOT / 'dist' / 'index.html'


def main():
    html = TEMPLATE.read_text(encoding='utf-8')
    for token, src in (
        ('__GEO_JSON__', ROOT / 'data' / 'tw_counties.json'),
        ('__POP_JSON__', ROOT / 'data' / 'tw_population.json'),
        ('__HOU_JSON__', ROOT / 'data' / 'tw_housing.json'),
    ):
        if token not in html:
            sys.exit(f'template is missing {token}')
        blob = json.dumps(json.loads(src.read_text(encoding='utf-8')),
                          ensure_ascii=False, separators=(',', ':'))
        assert '</script' not in blob.lower(), f'{src.name} would close the script tag'
        html = html.replace(token, blob)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print(f'{OUT.relative_to(ROOT)}: {len(html.encode()) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
