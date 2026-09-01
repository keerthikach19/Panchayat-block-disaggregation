import urllib.request
import ssl
import json
import sys
import io
import re
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*'
}

def make_req(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as res:
            raw = res.read().decode('utf-8', errors='replace')
            status = res.status
            try:
                data = json.loads(raw)
                return status, True, data, raw
            except:
                return status, False, None, raw
    except Exception as e:
        return 0, False, None, str(e)

print("=" * 80)
print("TESTING PUBLIC NO-AUTH IMD MAUSAM / CITY / NOWCAST FEEDS")
print("=" * 80)

candidate_urls = [
    # 1. District Warning GeoJSON / Data
    ("District Warning GIS Data", "https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php"),
    # 2. District Nowcast GIS Data
    ("District Nowcast GIS Data", "https://mausam.imd.gov.in/responsive/districtWiseNowcastGIS.php"),
    # 3. Station Nowcast GIS Data
    ("Station Nowcast GIS Data", "https://mausam.imd.gov.in/responsive/stationWiseNowcastGIS.php"),
    # 4. District Rainfall Data
    ("District Rainfall realized", "https://mausam.imd.gov.in/responsive/districtRainfall_realized.php"),
    ("District Rainfall monitoring", "https://mausam.imd.gov.in/responsive/rainfallinformation.php"),
    # 5. City Weather Live JSON
    ("City Weather Pune", "https://city.imd.gov.in/citywx/city_weather.php?id=43063"),
    ("City Weather Nashik", "https://city.imd.gov.in/citywx/city_weather.php?id=43003"),
    # 6. Mausamgram Forecast API / Feed
    ("Mausamgram Nashik", "https://mausamgram.imd.gov.in/api/forecast?lat=19.997&lon=73.789"),
    # 7. Open data feeds
    ("IMD RSS / Warning XML", "https://mausam.imd.gov.in/backend/assets/district_warning/district_warning.json"),
    ("IMD Nowcast JSON", "https://mausam.imd.gov.in/backend/assets/nowcast/district_nowcast.json"),
    ("IMD Rainfall JSON", "https://mausam.imd.gov.in/backend/assets/rainfall/district_rainfall.json"),
]

for label, url in candidate_urls:
    print(f"\n--- Testing: {label} ---")
    print(f"URL: {url}")
    s, is_json, data, raw = make_req(url)
    print(f"Status: {s}, Is JSON: {is_json}, Length: {len(raw)}")
    if is_json:
        if isinstance(data, list):
            print(f"  JSON List with {len(data)} items.")
            matches = [item for item in data if any(k in json.dumps(item).lower() for k in ['nashik', 'nasik', 'pune'])]
            print(f"  Found {len(matches)} Nashik/Pune items!")
            if matches:
                print("  Sample Match:", json.dumps(matches[0], indent=2)[:400])
        elif isinstance(data, dict):
            print(f"  JSON Dict with keys: {list(data.keys())[:10]}")
            matches = []
            for k, v in data.items():
                if any(x in str(k).lower() or x in str(v).lower() for x in ['nashik', 'nasik', 'pune']):
                    matches.append((k, v))
            print(f"  Found {len(matches)} matching keys/values!")
            if matches:
                print("  Sample Match:", matches[0])
            else:
                print("  Sample Content:", json.dumps(data, indent=2)[:300])
    elif raw and ('nashik' in raw.lower() or 'pune' in raw.lower() or '<html' in raw.lower()):
        print(f"  HTML/Text Content (first 300 chars): {raw[:300].replace(chr(10), ' ')}")
    else:
        print(f"  Response: {raw[:200]}")
