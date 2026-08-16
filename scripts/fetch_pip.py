#!/usr/bin/env python3
"""Discover and download the data files behind a pip.moi.gov.tw statistics page.

**This one has to run on your own machine.** pip.moi.gov.tw、www.nlma.gov.tw and
socialhousing.nlma.gov.tw all sit behind the same F5 web application firewall,
which rejects datacenter IP ranges outright: every path, including /robots.txt,
comes back as a 247-byte `Request Rejected` page with a support ID. A home or
office connection is not blocked, so the same script works there.

Two steps, because guessing a government site's download URLs does not work:

    # 1. look at what the page actually offers
    python3 scripts/fetch_pip.py --url https://pip.moi.gov.tw/Publicize/Info/A4010

    # 2. download what step 1 found
    python3 scripts/fetch_pip.py --url ... --download --out "/path/to/2026 - housing_TW/04_住宅政策_中央"

Step 1 prints, and writes to _discovery.json:
  * every direct file link (.xls/.xlsx/.csv/.ods/.json/.zip/.pdf)
  * every same-host API-ish URL found in inline script (fetch/ajax/axios/url:)
  * whether the page is an ASP.NET postback form (__VIEWSTATE present), which
    means the files are behind a POST and step 2 alone will not reach them

If step 1 finds nothing, the page builds its table from JavaScript after load.
Use scripts/fetch_pip_browser.mjs instead — it drives a real browser and records
the network traffic, which catches the request no matter how it is made.

Standard library only, so a stock macOS python3 runs it with no pip install.
"""
import argparse, hashlib, html, json, pathlib, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
}
DATA_EXT = r'xlsx?|csv|ods|json|zip|pdf|xml|txt'
BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# The WAF's rejection page is short and always shaped the same way. Recognising
# it is the difference between "no files here" and "you were never let in".
REJECTED = re.compile(r'Request Rejected|support ID is', re.I)


def safe(name, limit=110):
    return BAD.sub('_', html.unescape(name)).strip(' .') [:limit] or 'untitled'


def get(url, referer=None):
    h = dict(HEADERS)
    if referer:
        h['Referer'] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read(), dict(r.headers), r.geturl()


def looks_rejected(body):
    return len(body) < 2000 and REJECTED.search(body[:2000].decode('utf-8', 'replace'))


def ext_of(url, ctype, body):
    """These endpoints often serve a CSV from a URL with no extension and no
    Content-Disposition, so fall back to the header and then the bytes."""
    m = re.search(rf'\.({DATA_EXT})(?:$|[?#])', url, re.I)
    if m:
        return '.' + m.group(1).lower()
    for pat, ext in (('sheet|excel', '.xlsx'), ('opendocument', '.ods'), ('csv', '.csv'),
                     ('json', '.json'), ('zip', '.zip'), ('pdf', '.pdf'), ('xml', '.xml')):
        if re.search(pat, ctype, re.I):
            return ext
    head = body[:4]
    if head[:2] == b'PK':                       # xlsx/ods/zip all start here
        return '.zip'
    if head == b'%PDF':
        return '.pdf'
    if body[:1] in (b'{', b'['):
        return '.json'
    if body[:5].lower() == b'<?xml':
        return '.xml'
    # A "download" link that returns a page is a landing page or a login wall,
    # not a file. Naming it .html keeps that visible instead of shipping a .csv
    # full of markup.
    if re.match(rb'\s*<(!doctype html|html)', body[:64], re.I):
        return '.html'
    try:
        body[:4096].decode('utf-8')
        return '.csv' if b',' in body[:4096] else '.txt'
    except UnicodeDecodeError:
        return '.bin'


def discover(page_url):
    body, hdrs, final = get(page_url)
    if looks_rejected(body):
        sys.exit(
            '被防火牆擋下（Request Rejected）。這台機器的 IP 不被接受。\n'
            '在自己的電腦、一般網路環境下執行同一行指令即可。')
    text = body.decode('utf-8', 'replace')

    def absolute(u):
        return urllib.parse.urljoin(final, html.unescape(u.strip()))

    # 1. anchors and iframes pointing at a data file
    files = {}
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         text, re.I | re.S):
        href, label = m.group(1), re.sub(r'<[^>]+>', '', m.group(2))
        if re.search(rf'\.({DATA_EXT})(?:$|[?#])', href, re.I) or 'download' in href.lower():
            files[absolute(href)] = ' '.join(label.split())[:120]
    for m in re.finditer(rf'(?:src|href)\s*=\s*["\']([^"\']+\.(?:{DATA_EXT})[^"\']*)["\']',
                         text, re.I):
        files.setdefault(absolute(m.group(1)), '')

    # 2. URLs written inside inline script — the usual home of an XHR endpoint
    host = urllib.parse.urlsplit(final).netloc
    api = set()
    for m in re.finditer(r'''["'](/[^"'\s]{4,200}|https?://[^"'\s]{8,200})["']''', text):
        u = m.group(1)
        if re.search(r'\.(png|jpe?g|gif|svg|ico|css|js|woff2?|ttf|map)(?:$|[?#])', u, re.I):
            continue
        # Keep endpoint-shaped URLs, not page routes. 'data' and 'list' alone
        # match every navigation link on a statistics site, so they are out.
        if not (re.search(r'api|export|download|json|ashx|handler|getdata|query', u, re.I)
                or re.search(rf'\.({DATA_EXT})(?:$|[?#])', u, re.I)
                or '?' in u):
            continue
        a = absolute(u)
        if urllib.parse.urlsplit(a).netloc == host:
            api.add(a)

    # 3. ASP.NET postback state — if this is present the table is behind a POST
    form = {}
    for name in ('__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION', '__RequestVerificationToken'):
        if re.search(rf'name="{name}"', text):
            form[name] = True
    posts = sorted(set(re.findall(r'__doPostBack\(\s*[\'"]([^\'"]+)', text)))

    titles = re.findall(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    return {
        'url': page_url, 'finalUrl': final,
        'title': ' '.join(html.unescape(titles[0]).split()) if titles else '',
        'bytes': len(body), 'contentType': hdrs.get('Content-Type', ''),
        'files': [{'url': u, 'label': l} for u, l in sorted(files.items())],
        'apiCandidates': sorted(api),
        'aspNetForm': sorted(form),
        'postbackTargets': posts[:40],
    }


def download(found, out_dir, referer):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, f in enumerate(found['files'], 1):
        url = f['url']
        try:
            body, hdrs, final = get(url, referer=referer)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f'  [{i}] 失敗 {url}\n      {e}')
            rows.append({'url': url, 'status': f'ERROR:{e}', 'bytes': 0, 'sha256': ''})
            continue
        if looks_rejected(body):
            print(f'  [{i}] 被擋 {url}')
            rows.append({'url': url, 'status': 'REJECTED', 'bytes': 0, 'sha256': ''})
            continue
        # Prefer the server's own filename; fall back to the link text.
        cd = hdrs.get('Content-Disposition', '')
        m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
        name = urllib.parse.unquote(m.group(1)) if m else ''
        if not name:
            name = pathlib.PurePosixPath(urllib.parse.urlsplit(final).path).name
        if not name or '.' not in name:
            name = f"{f['label'] or 'download'}{ext_of(url, hdrs.get('Content-Type', ''), body)}"
        path = out / safe(name)
        path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        print(f'  [{i}] {path.name}　{len(body):,} bytes')
        rows.append({'url': url, 'status': 200, 'bytes': len(body), 'sha256': sha,
                     'file': path.name})
    (out / '_pip_manifest.json').write_text(json.dumps(
        {'fetchedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
         'page': found['finalUrl'], 'items': rows}, ensure_ascii=False, indent=2),
        encoding='utf-8')
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', required=True, help='pip.moi.gov.tw 上的統計頁網址')
    ap.add_argument('--download', action='store_true', help='下載步驟 1 找到的檔案')
    ap.add_argument('--out', default='.', help='下載目的資料夾')
    a = ap.parse_args()

    found = discover(a.url)
    print(f"標題：{found['title'] or '（無）'}")
    print(f"回應：{found['bytes']:,} bytes　{found['contentType']}\n")

    print(f"直接可下載的檔案：{len(found['files'])} 個")
    for f in found['files']:
        print(f"  {f['label'] or '（無標題）'}\n    {f['url']}")
    print(f"\n可能的資料端點：{len(found['apiCandidates'])} 個")
    for u in found['apiCandidates'][:30]:
        print(f'  {u}')
    if found['aspNetForm']:
        print(f"\n★ 這是 ASP.NET 表單頁（{'、'.join(found['aspNetForm'])}）。"
              '\n  檔案很可能藏在 POST 後面，單靠這支程式抓不到，'
              '\n  請改用 scripts/fetch_pip_browser.mjs。')
        if found['postbackTargets']:
            print('  __doPostBack 目標：' + '、'.join(found['postbackTargets'][:10]))
    if not found['files'] and not found['apiCandidates']:
        print('\n★ 什麼都沒找到，表示表格是載入後用 JavaScript 產生的。'
              '\n  請改用 scripts/fetch_pip_browser.mjs。')

    outdir = pathlib.Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / '_discovery.json').write_text(
        json.dumps(found, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n完整結果寫入 {outdir / '_discovery.json'}")

    if a.download:
        if not found['files']:
            sys.exit('沒有可直接下載的檔案，先看上面的訊息。')
        print(f'\n下載 {len(found["files"])} 個檔案到 {outdir}：')
        download(found, outdir, referer=found['finalUrl'])


if __name__ == '__main__':
    main()
