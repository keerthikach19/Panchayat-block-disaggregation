import urllib.request
import ssl
import re
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_live_imd_district_rainfall(msg="D"):
    url = f"https://mausam.imd.gov.in/responsive/rainfallinformation.php?msg={msg}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
        html = res.read().decode('utf-8', errors='replace')
    
    # Extract district objects matching pattern
    pattern = re.compile(
        r'\{\s*"title"\s*:\s*"([^"]+)",\s*"id"\s*:\s*"([^"]+)",\s*"color"\s*:\s*"([^"]+)",\s*"info"\s*:\s*"([^"]*)",\s*"balloonText"\s*:\s*"([^"]+)"\s*\}',
        re.DOTALL
    )
    
    districts = {}
    for m in pattern.finditer(html):
        title, dist_id, color, info, btext = m.groups()
        btext_clean = btext.replace(r'\/', '/')
        
        date_m = re.search(r'Date\s*:\s*([0-9\-]+)', btext_clean)
        act_m = re.search(r'Actual\s*:\s*([0-9\.]+)\s*mm', btext_clean)
        norm_m = re.search(r'Normal\s*:\s*([0-9\.]+)\s*mm', btext_clean)
        dep_m = re.search(r'Departure\s*:\s*([+\-0-9%]+)', btext_clean)
        
        districts[title.upper()] = {
            "district_name": title,
            "district_id": dist_id,
            "color": color,
            "departure": dep_m.group(1) if dep_m else info,
            "date": date_m.group(1) if date_m else None,
            "rainfall_mm": float(act_m.group(1)) if act_m else 0.0,
            "normal_rainfall_mm": float(norm_m.group(1)) if norm_m else 0.0,
            "raw_balloon_text": btext_clean
        }
    return districts

print("=" * 80)
print("FETCHING LIVE IMD DISTRICT RAINFALL DATA")
print("=" * 80)

dist_data = fetch_live_imd_district_rainfall("D")
print(f"Total districts parsed: {len(dist_data)}")

for d in ["NASHIK", "PUNE", "MUMBAI CITY", "MUMBAI SUBURBAN", "THANE", "AHMEDNAGAR", "SOLAPUR", "NAGPUR"]:
    if d in dist_data:
        print(f"\n[DISTRICT: {d}]")
        print(json.dumps(dist_data[d], indent=2))
