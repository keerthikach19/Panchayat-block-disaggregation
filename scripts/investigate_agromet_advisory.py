"""
Investigate IMD Agromet Advisory District Page for forward-looking forecast data.
Target: https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php
"""
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

BASE_URL = "https://mausam.imd.gov.in/responsive"

# ─── TEST 1: Main agromet advisory page (no auth) ───
print("=" * 80)
print("TEST 1: Fetch main agromet advisory page")
print("=" * 80)

url = f"{BASE_URL}/agromet_adv_ser_district_current_en.php"
print(f"URL: {url}")

try:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
        html = res.read().decode('utf-8', errors='replace')
        print(f"HTTP Status: {res.status}")
        print(f"Content-Length: {len(html)} bytes")
        
        # Save full HTML for inspection
        with open('data/imd_agromet_advisory_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved full HTML to data/imd_agromet_advisory_page.html")
        
        # Extract script blocks — the earlier background task found AJAX calls here
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"\nTotal <script> blocks: {len(scripts)}")
        
        for i, s in enumerate(scripts):
            if any(k in s.lower() for k in ['selectstate', 'selectdistrict', 'ajax', 'xmlhttp', 'fetch', 'agrometinformation']):
                print(f"\n--- Script Block {i} (relevant) ---")
                print(s[:1500])
                print("..." if len(s) > 1500 else "")
        
        # Extract <select> / <option> elements for state/district dropdowns
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        selects = soup.find_all('select')
        print(f"\nTotal <select> dropdowns: {len(selects)}")
        for sel in selects:
            sel_id = sel.get('id', sel.get('name', 'unnamed'))
            opts = sel.find_all('option')
            print(f"\n  Dropdown: {sel_id} ({len(opts)} options)")
            # Find Maharashtra option
            for opt in opts:
                val = opt.get('value', '')
                text = opt.get_text(strip=True)
                if any(k in text.lower() for k in ['maharashtra', 'mh', 'nashik', 'pune']):
                    print(f"    MATCH: value='{val}' text='{text}'")
            # Show first 5 options as sample
            if len(opts) > 0:
                print(f"    First 5 options: {[(o.get('value',''), o.get_text(strip=True)) for o in opts[:5]]}")

except Exception as e:
    print(f"FAILED: {e}")

# ─── TEST 2: Try the AJAX sub-endpoint directly ───
print("\n" + "=" * 80)
print("TEST 2: Test AJAX sub-endpoints for Maharashtra districts")
print("=" * 80)

# From the script block we already captured, the AJAX calls are:
# Step 1 (state -> districts): agrometinformation/district_current_en_get.php?s=MAHARASHTRA&step1=true
# Step 2 (district -> bulletin): agrometinformation/district_current_en_get.php?s=NASHIK&step2=true

for label, params in [
    ("Step1: Maharashtra districts", "s=MAHARASHTRA&step1=true"),
    ("Step1: Maharashtra districts (lowercase)", "s=maharashtra&step1=true"),
    ("Step2: Nashik bulletin", "s=NASHIK&step2=true"),
    ("Step2: Pune bulletin", "s=PUNE&step2=true"),
]:
    ajax_url = f"{BASE_URL}/agrometinformation/district_current_en_get.php?{params}"
    print(f"\n--- {label} ---")
    print(f"URL: {ajax_url}")
    try:
        req = urllib.request.Request(ajax_url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
            raw = res.read().decode('utf-8', errors='replace')
            print(f"Status: {res.status}, Length: {len(raw)}")
            # Save if substantial
            safe_label = label.replace(" ", "_").replace(":", "")
            with open(f'data/imd_agromet_{safe_label}.html', 'w', encoding='utf-8') as f:
                f.write(raw)
            print(f"Saved to data/imd_agromet_{safe_label}.html")
            # Show preview
            print(f"Content preview (first 800 chars):")
            print(raw[:800])
    except Exception as e:
        print(f"FAILED: {e}")
