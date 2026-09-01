import urllib.request
import ssl
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0'}

for page in ['districtWiseNowcastGIS.php', 'districtWiseWarningGIS.php', 'stationWiseNowcastGIS.php', 'rainfallinformation.php']:
    url = f'https://mausam.imd.gov.in/responsive/{page}'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as res:
            html = res.read().decode('utf-8', errors='replace')
            print(f'=== Page: {page} ===')
            # Look for fetch, $.ajax, $.get, urls, .json, .geojson
            matches = re.findall(r'(https?://[^\s\'\"\<\>\)]+|\/[^\s\'\"\<\>\)]+\.(?:json|geojson|php|txt|csv|xml)|assets\/[^\s\'\"\<\>\)]+|api\/[^\s\'\"\<\>\)]+)', html)
            unique = sorted(list(set(matches)))
            for m in unique:
                if any(x in m.lower() for x in ['data', 'json', 'geojson', 'nowcast', 'warning', 'rain', 'api']):
                    print('  *', m)
    except Exception as e:
        print(f'Error fetching {page}: {e}')
