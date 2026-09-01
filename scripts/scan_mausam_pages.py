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

# Test district weather report on mausam.imd.gov.in
test_pages = [
    'https://mausam.imd.gov.in/responsive/districtWeatherReport.php',
    'https://mausam.imd.gov.in/responsive/rainfallinformation.php',
    'https://mausam.imd.gov.in/responsive/districtRainfall.php',
    'https://mausam.imd.gov.in/responsive/stateRainfall.php',
    'https://mausam.imd.gov.in/responsive/awsData.php',
    'https://mausam.imd.gov.in/responsive/stationWiseNowcastGIS.php',
    'https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php',
    'https://mausam.imd.gov.in/responsive/nowcast.php',
    'https://mausam.imd.gov.in/responsive/radar.php',
    'https://mausam.imd.gov.in/responsive/monsoon.php',
    'https://mausam.imd.gov.in/responsive/agro_advisory.php',
    'https://mausam.imd.gov.in/responsive/satellite.php',
]

for p in test_pages:
    try:
        req = urllib.request.Request(p, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
            html = res.read().decode('utf-8', errors='replace')
            print(f"[OK 200] {p} (Length: {len(html)})")
            # Look for AJAX or data calls
            scripts = re.findall(r'<script[^>]*src=[\'\"]([^\'\"]+)[\'\"]', html)
            data_calls = re.findall(r'(?:url|fetch|getJSON|ajax|src)\s*[:=\(]\s*[\'\"]([^\'\"]+\.(?:php|json|geojson|csv|txt))[\'\"]', html)
            if data_calls:
                print("   Data calls:", list(set(data_calls))[:5])
    except Exception as e:
        print(f"[FAIL] {p} -> {e}")
