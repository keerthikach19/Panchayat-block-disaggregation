import urllib.request
import ssl
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def check_url(url):
    print(f"\n--- Checking: {url} ---")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=12) as res:
            raw = res.read().decode('utf-8', errors='replace')
            print(f"Status: {res.status}, Length: {len(raw)}")
            try:
                data = json.loads(raw)
                print("JSON Type:", type(data))
                if isinstance(data, dict):
                    print("Keys:", list(data.keys())[:10])
                    if 'features' in data:
                        print("Features count:", len(data['features']))
                        # Search for Nashik or Pune
                        matches = [f for f in data['features'] if any(k in json.dumps(f.get('properties', {})).lower() for k in ['nashik', 'nasik', 'pune'])]
                        print(f"Found {len(matches)} Nashik/Pune features!")
                        if matches:
                            print("Sample match properties:", json.dumps(matches[0].get('properties', {}), indent=2))
                return data
            except Exception as e:
                print("Not JSON:", e)
                print("Sample text:", raw[:300])
    except Exception as e:
        print("Error:", e)

check_url("https://mausam.imd.gov.in/responsive/nowcast.geojson")
check_url("https://mausam.imd.gov.in/imd_latest/contents/district_shapefiles/india_gj_2024.geojson")
check_url("https://mausam.imd.gov.in/imd_latest/contents/district_shapefiles/DISTRICT_F-2.json")
