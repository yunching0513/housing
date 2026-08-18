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
    'overview.html': ('overview.template.html', {
        '__OV_JSON__': 'tw_overview.json',
    }),
    'index.html': ('index.template.html', {
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
    }),
    'priority.html': ('priority.template.html', {
        '__AFF_JSON__': 'tw_affordability.json',
        '__HOU_JSON__': 'tw_housing.json',
        '__POP_JSON__': 'tw_population.json',
        '__PSER_JSON__': 'tw_pop_series.json',
    }),
}


def build(out_name, template_name, tokens):
    html = (ROOT / 'src' / template_name).read_text(encoding='utf-8')
    html = html.replace('__SHARED_CSS__', (ROOT / 'src' / 'shared.css').read_text(encoding='utf-8'))
    # Only the pages that draw a map ask for it, so this is a plain replace with
    # no error if the token is absent.
    html = html.replace('__MAP_ZOOM_JS__', (ROOT / 'src' / 'mapzoom.js').read_text(encoding='utf-8'))
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
