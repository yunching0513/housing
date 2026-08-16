#!/usr/bin/env python3
"""Download everything listed in sources.json into a categorised folder tree.

Standard library only, so it runs on a stock macOS Python with no pip install.

    python3 scripts/fetch_sources.py --out "/Users/<you>/2026 - housing_TW"

Re-running skips files already present (use --force to refetch). Every attempt —
success or failure — lands in _metadata/manifest.csv with the source URL, HTTP
status, byte count and SHA-256, so the tree stays auditable.

Two hosts need help, and the script handles both:
  * ws.dgbas.gov.tw serves an incomplete certificate chain. The missing TWCA
    intermediate is fetched from the certificate's own AIA extension and added
    to the trust store — the chain is completed, never bypassed.
  * Several government hosts reject non-browser user agents.
"""
import argparse, csv, hashlib, json, os, pathlib, re, ssl, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}
BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe(name, limit=90):
    return BAD.sub('_', name).strip(' .')[:limit] or 'untitled'


def guess_ext(url, ctype, body):
    m = re.search(r'\.(xml|csv|json|zip|xlsx|xls|ods|geojson|pdf)(?:$|[?#])', url, re.I)
    if m:
        return '.' + m.group(1).lower()
    for key, ext in (('xml', '.xml'), ('json', '.json'), ('csv', '.csv'),
                     ('zip', '.zip'), ('excel', '.xlsx'), ('pdf', '.pdf')):
        if key in (ctype or '').lower():
            return ext
    head = body[:400].lstrip(b'\xef\xbb\xbf')
    if head.startswith(b'<?xml') or head.startswith(b'<'):
        return '.xml'
    if head.startswith(b'{') or head.startswith(b'['):
        return '.json'
    if head.startswith(b'PK'):
        return '.zip'
    return '.csv'


# ── TLS: complete a chain the server fails to send ───────────────────────────
def repair_chain(host, store):
    """Fetch the AIA-published intermediate for `host` and append it to `store`.

    Some Taiwanese government hosts send a leaf without its issuing CA. The
    certificate names where to get it; we follow that pointer rather than
    weakening verification.
    """
    # Must traverse the same path urllib uses: behind an HTTPS proxy the
    # certificate seen through the tunnel differs from the one seen directly.
    proxy = os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY') or ''
    via = ['-proxy', urllib.parse.urlsplit(proxy).netloc] if proxy else []
    try:
        leaf = subprocess.run(
            ['openssl', 's_client', *via, '-connect', f'{host}:443', '-servername', host],
            input=b'', capture_output=True, timeout=40).stdout
        pem = subprocess.run(['openssl', 'x509'], input=leaf,
                             capture_output=True, timeout=20).stdout
        if not pem:
            return False
        text = subprocess.run(['openssl', 'x509', '-noout', '-text'], input=pem,
                              capture_output=True, timeout=20).stdout.decode('utf8', 'replace')
        m = re.search(r'CA Issuers - URI:(\S+)', text)
        if not m:
            return False
        der = urllib.request.urlopen(m.group(1), timeout=40).read()
        for form in ('DER', 'PEM'):
            out = subprocess.run(['openssl', 'x509', '-inform', form],
                                 input=der, capture_output=True, timeout=20).stdout
            if out:
                store.parent.mkdir(parents=True, exist_ok=True)
                with store.open('ab') as fh:
                    fh.write(out)
                print(f'    · 補上 {host} 缺少的中介憑證')
                return True
    except Exception as e:
        print(f'    · 憑證修補失敗 ({host}): {type(e).__name__}')
    return False


def make_ctx(store):
    ctx = ssl.create_default_context()
    if store.exists() and store.stat().st_size:
        ctx.load_verify_locations(cafile=str(store))  # adds to, never replaces, the system store
    return ctx


repaired = {}   # host -> True once its chain has been completed, so we try it only once


def fetch(url, store, tries=3):
    """Return (status, body, ctype). status is an int, or a string on failure."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=90, context=make_ctx(store)) as r:
                return r.status, r.read(), r.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e:   # subclass of URLError — must come first
            body = e.read()
            if e.code == 403 and b'Just a moment' in body[:400]:
                return 'cloudflare', b'', ''      # JS challenge; a real browser is required
            if attempt == tries - 1:
                return e.code, b'', ''
        except urllib.error.URLError as e:
            # urllib wraps the TLS failure, so unwrap before deciding to repair.
            reason = e.reason
            if isinstance(reason, ssl.SSLCertVerificationError) and 'local issuer' in str(reason):
                host = urllib.parse.urlsplit(url).hostname
                if not repaired.get(host) and repair_chain(host, store):
                    repaired[host] = True
                    continue
                return 'tls', b'', ''
            if attempt == tries - 1:
                return f'URLError:{type(reason).__name__}', b'', ''
        except Exception as e:
            if attempt == tries - 1:
                return type(e).__name__, b'', ''
        time.sleep(2 ** attempt)
    return 'unknown', b'', ''


def merge(prior, rows):
    """Prior attempts plus this run's, newest wins per URL — so a scoped or
    interrupted run never erases what earlier runs recorded as still missing."""
    out = dict(prior)
    for r in rows:
        out[r['來源網址']] = r
    return list(out.values())


def write_manifest(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'data_TW'), help='目的資料夾')
    ap.add_argument('--force', action='store_true', help='已存在的檔案也重新下載')
    ap.add_argument('--sources', default=str(ROOT / 'sources.json'))
    ap.add_argument('--skip', help='略過分類符合此正規式的項目，例如 03_人口動態_戶籍')
    args = ap.parse_args()

    out = pathlib.Path(args.out).expanduser()
    meta = out / '_metadata'
    meta.mkdir(parents=True, exist_ok=True)
    store = meta / 'extra-ca.pem'
    sources = json.loads(pathlib.Path(args.sources).read_text(encoding='utf-8'))

    # Resume at URL granularity. Every prior row is carried forward — including
    # failures, so the manifest keeps reporting what is still missing — but only
    # the 200s are treated as done and skipped.
    prior, done, rows = {}, {}, []
    book = meta / 'manifest.csv'
    if book.exists() and not args.force:
        for r in csv.DictReader(book.open(encoding='utf-8-sig')):
            prior[r['來源網址']] = r
            if r['狀態'] == '200' and (out / r['檔案']).exists():
                done[r['來源網址']] = r

    ok, skipped, failed = 0, 0, []
    for i, e in enumerate(sources, 1):
        if args.skip and re.search(args.skip, e['category']):
            continue
        folder = out / e['category']
        folder.mkdir(parents=True, exist_ok=True)
        for url in e['urls']:
            year = re.search(r'[aA](\d{3})\.xml$', url)
            base = safe(e['title']) + (f'_{year.group(1)}民國年' if year else '')
            if url in done:
                skipped += 1
                continue

            status, body, ctype = fetch(url, store)
            stamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
            if status == 200 and body:
                path = folder / (base + guess_ext(url, ctype, body))
                n = 2
                while path.exists() and not args.force:
                    path = folder / f'{base}({n}){guess_ext(url, ctype, body)}'
                    n += 1
                path.write_bytes(body)
                digest = hashlib.sha256(body).hexdigest()
                ok += 1
                print(f'[{i}/{len(sources)}] ✓ {e["category"]}/{path.name}  {len(body):,}B')
                rel = str(path.relative_to(out))
            else:
                digest, rel = '', ''
                failed.append((e['title'], url, status))
                print(f'[{i}/{len(sources)}] ✗ {e["title"]}  ({status})')
            rows.append({
                '分類': e['category'], '資料集名稱': e['title'],
                '資料集識別碼': e.get('dataset_id') or '', '提供機關': e.get('agency', ''),
                '更新頻率': e.get('update', ''), '檔案': rel, '來源網址': url,
                '狀態': status, '位元組': len(body), 'SHA256': digest, '下載時間_UTC': stamp,
            })
            if len(rows) % 25 == 0:
                write_manifest(book, merge(prior, rows))   # checkpoint for resume

    write_manifest(book, merge(prior, rows))

    print(f'\n成功 {ok} ・ 略過 {skipped} ・ 失敗 {len(failed)}')
    if failed:
        print('\n以下需要在本機瀏覽器環境重抓（多為 Cloudflare 人機驗證）：')
        for t, u, s in failed:
            print(f'  [{s}] {t}\n        {u}')
    print(f'\n清單：{meta / "manifest.csv"}')


if __name__ == '__main__':
    main()
