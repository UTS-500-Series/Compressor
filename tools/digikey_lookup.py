#!/usr/bin/env python3
"""Enrich digikey-upload.csv with DigiKey part numbers, stock and pricing.

    export DIGIKEY_CLIENT_ID=...          # from developer.digikey.com, your app's keys
    export DIGIKEY_CLIENT_SECRET=...
    python3 tools/digikey_lookup.py                       # -> digikey-priced.csv
    python3 tools/digikey_lookup.py --raw NE5532P         # dump one response verbatim

Credentials are read from the environment and never written to disk or into any output
file. Responses are cached in .digikey-cache.json so re-runs cost nothing.

WHAT IT WILL AND WILL NOT DECIDE
  Lines that already carry a manufacturer part number are resolved to a specific DigiKey
  part: stock, price at your order quantity, datasheet.
  Lines that do not - every resistor and capacitor - get the top few CANDIDATES listed
  instead, and are left for you to choose. A 10k resistor has hundreds of orderable
  variants differing in tolerance, tempco, power and body size; picking one automatically
  would put a part number in the file that nobody actually chose.

The v4 response schema is read defensively: if DigiKey has moved a field, --raw prints a
whole response so the extraction below can be corrected in a couple of minutes.
"""
import os, sys, json, time, csv, argparse, urllib.request, urllib.parse, urllib.error

TOKEN_URL = 'https://api.digikey.com/v1/oauth2/token'
SEARCH_URL = 'https://api.digikey.com/products/v4/search/keyword'
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.digikey-cache.json')
# UTS is in Sydney; change if you are ordering into another DigiKey site.
SITE, CURRENCY = 'AU', 'AUD'


def creds():
    cid, sec = os.environ.get('DIGIKEY_CLIENT_ID'), os.environ.get('DIGIKEY_CLIENT_SECRET')
    if not cid or not sec:
        sys.exit(
            'No DigiKey credentials in the environment.\n\n'
            '  1. Sign in at https://developer.digikey.com and create an Organisation\n'
            '  2. Add a Production app; tick the Product Information API\n'
            '  3. Copy its Client ID and Client Secret, then:\n\n'
            '       export DIGIKEY_CLIENT_ID=...\n'
            '       export DIGIKEY_CLIENT_SECRET=...\n\n'
            'Keep them in your shell profile or a .env you do not commit - never in the\n'
            'repository, and never pasted into a chat.')
    return cid, sec


def token(cid, sec):
    body = urllib.parse.urlencode({'client_id': cid, 'client_secret': sec,
                                   'grant_type': 'client_credentials'}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())['access_token']
    except urllib.error.HTTPError as e:
        sys.exit('Token request failed (%s). Check the client ID/secret and that the app\n'
                 'has the Product Information API enabled.\n%s'
                 % (e.code, e.read().decode()[:400]))


def search(tok, cid, keywords, limit=5):
    body = json.dumps({'Keywords': keywords, 'Limit': limit, 'Offset': 0}).encode()
    req = urllib.request.Request(SEARCH_URL, data=body, headers={
        'Authorization': 'Bearer ' + tok, 'X-DIGIKEY-Client-Id': cid,
        'X-DIGIKEY-Locale-Site': SITE, 'X-DIGIKEY-Locale-Currency': CURRENCY,
        'Content-Type': 'application/json'})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        return {'_error': '%s %s' % (e.code, e.read().decode()[:200])}


def dig(d, *path, default=None):
    """Walk nested dict/list keys, returning default rather than raising."""
    for k in path:
        if isinstance(d, list):
            d = d[k] if isinstance(k, int) and len(d) > k else None
        elif isinstance(d, dict):
            d = d.get(k)
        else:
            return default
        if d is None:
            return default
    return d


def price_at(variation, qty):
    """Unit price at the first break at or below qty."""
    breaks = dig(variation, 'StandardPricing', default=[]) or []
    best = None
    for b in sorted(breaks, key=lambda x: x.get('BreakQuantity', 0)):
        if b.get('BreakQuantity', 0) <= qty:
            best = b
    return (best or (breaks[0] if breaks else {})).get('UnitPrice')


def summarise(product, qty):
    """Pull the fields we care about out of one v4 product."""
    vs = dig(product, 'ProductVariations', default=[]) or []
    # prefer a through-hole/bulk variation that is actually in stock
    v = next((x for x in vs if (x.get('QuantityAvailableforPackageType') or 0) >= qty), vs[0] if vs else {})
    return {
        'dk': v.get('DigiKeyProductNumber') or dig(product, 'DigiKeyPartNumber', default=''),
        'mfr': dig(product, 'Manufacturer', 'Name', default=''),
        'mpn': product.get('ManufacturerProductNumber') or product.get('ManufacturerPartNumber') or '',
        'stock': product.get('QuantityAvailable') or v.get('QuantityAvailableforPackageType') or 0,
        'unit': price_at(v, qty),
        'min': v.get('MinimumOrderQuantity') or '',
        'status': dig(product, 'ProductStatus', 'Status', default=''),
        'url': product.get('ProductUrl') or '',
        'datasheet': product.get('DatasheetUrl') or '',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='digikey-upload.csv')
    ap.add_argument('--out', default='digikey-priced.csv')
    ap.add_argument('--raw', help='dump one raw response for this keyword and exit')
    ap.add_argument('--candidates', type=int, default=3,
                    help='how many options to list for lines with no part number')
    args = ap.parse_args()

    cid, sec = creds()
    tok = token(cid, sec)

    if args.raw:
        print(json.dumps(search(tok, cid, args.raw, limit=2), indent=2)[:6000])
        return

    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE))

    rows = list(csv.DictReader(open(args.inp)))
    out = []
    total = 0.0
    unpriced = 0
    for r in rows:
        qty = int(r['Quantity'])
        mpn, desc = r['Manufacturer Part Number'].strip(), r['Description']
        key = mpn or desc
        if not key or r['Customer Reference'] == 'panel':
            out.append({**r, 'DigiKey Part Number': '', 'Stock': '', 'Unit Price': '',
                        'Line Total': '', 'Candidates': '', 'Datasheet': ''})
            continue
        if key not in cache:
            cache[key] = search(tok, cid, key, limit=max(args.candidates, 1))
            time.sleep(0.4)                     # be polite; the API is rate limited
        res = cache[key]
        products = dig(res, 'Products', default=[]) or []
        if res.get('_error') or not products:
            out.append({**r, 'DigiKey Part Number': '', 'Stock': 'no match', 'Unit Price': '',
                        'Line Total': '', 'Candidates': res.get('_error', 'no results'),
                        'Datasheet': ''})
            unpriced += 1
            continue

        if mpn:
            s = summarise(products[0], qty)
            line = (s['unit'] or 0) * qty
            total += line
            out.append({**r, 'DigiKey Part Number': s['dk'], 'Stock': s['stock'],
                        'Unit Price': s['unit'], 'Line Total': round(line, 2),
                        'Candidates': '%s %s' % (s['mfr'], s['status']),
                        'Datasheet': s['datasheet']})
        else:
            # no part chosen yet: offer options, do not pick one
            opts = []
            for p in products[:args.candidates]:
                s = summarise(p, qty)
                opts.append('%s | %s %s | stock %s | %s' %
                            (s['dk'], s['mfr'], s['mpn'], s['stock'], s['unit']))
            out.append({**r, 'DigiKey Part Number': '', 'Stock': '',
                        'Unit Price': '', 'Line Total': '',
                        'Candidates': ' ;; '.join(opts), 'Datasheet': ''})
            unpriced += 1

    json.dump(cache, open(CACHE, 'w'))
    cols = list(rows[0].keys()) + ['DigiKey Part Number', 'Stock', 'Unit Price',
                                   'Line Total', 'Candidates', 'Datasheet']
    with open(args.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print('wrote %s' % args.out)
    print('  priced   : %d lines, %.2f %s' % (len(rows) - unpriced, total, CURRENCY))
    print('  to choose: %d lines have candidates listed but no part selected' % unpriced)
    print('  NOTE: the total covers only the lines with a part number. It is not a quote.')


if __name__ == '__main__':
    main()
