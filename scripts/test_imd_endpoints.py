import urllib.request
import ssl
import json
import sys
import io

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
print("TEST 1: Check City Forecast Mapping to discover Nashik & Pune IDs")
print("=" * 80)
s, is_json, data, raw = make_req("https://api.imd.gov.in/api/v1/cityforecast_mapping")
print(f"Status: {s}, Is JSON: {is_json}")
if is_json and isinstance(data, list):
    print(f"Total mapped stations: {len(data)}")
    for item in data:
        name = str(item.get('Station_Name', item.get('station_name', ''))).lower()
        state = str(item.get('State_Name', item.get('state_name', ''))).lower()
        if any(k in name for k in ['nashik', 'nasik', 'pune', 'poona']) or ('maharashtra' in state and any(k in name for k in ['nashik', 'pune'])):
            print("  Found Station:", item)
elif raw:
    print("Raw sample:", raw[:500])

print("\n" + "=" * 80)
print("TEST 2: Test candidate endpoints for Nashik and Pune")
print("=" * 80)

test_urls = [
    # City Forecast
    ("City Forecast (All/Nashik/Pune)", "https://api.imd.gov.in/api/v1/cityforecast"),
    # District Rainfall
    ("District Rainfall", "https://api.imd.gov.in/api/v1/districtrainfall"),
    # State District Rainfall Forecast
    ("State District Rainfall Forecast", "https://api.imd.gov.in/api/v1/state_district_rainfall_forecast"),
    # District Nowcast
    ("District Nowcast", "https://api.imd.gov.in/api/v1/districtnowcast"),
    # District Warning
    ("District Warning", "https://api.imd.gov.in/api/v1/districtwarning"),
    # Current Weather
    ("Current Wx", "https://api.imd.gov.in/api/v1/current_wx"),
    # AWS Data Mapping
    ("AWS Data Mapping", "https://api.imd.gov.in/api/v1/aws_data_mapping"),
    # AWS Data
    ("AWS Data", "https://api.imd.gov.in/api/v1/aws_data")
]

for label, url in test_urls:
    print(f"\n--- Testing: {label} ({url}) ---")
    s, is_json, data, raw = make_req(url)
    print(f"HTTP Status: {s}, Is JSON: {is_json}, Length: {len(raw)}")
    if is_json:
        if isinstance(data, list):
            print(f"  Returned List with {len(data)} items.")
            # Search for Nashik or Pune in list
            mh_matches = []
            for item in data:
                item_str = json.dumps(item).lower()
                if 'nashik' in item_str or 'nasik' in item_str or 'pune' in item_str:
                    mh_matches.append(item)
            print(f"  Matching Nashik/Pune items: {len(mh_matches)}")
            if mh_matches:
                print("  Sample Match:", json.dumps(mh_matches[0], indent=2)[:600])
            elif data:
                print("  Sample First Item:", json.dumps(data[0], indent=2)[:300])
        elif isinstance(data, dict):
            print(f"  Returned Dict with keys: {list(data.keys())}")
            print("  Sample content:", json.dumps(data, indent=2)[:400])
    else:
        print(f"  Raw response (first 300 chars): {raw[:300]}")
