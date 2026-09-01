"""
Deep investigation of imdagrimet.gov.in district bulletin endpoints.
The mausam.imd.gov.in agromet page just provides PDF links to this domain.
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

# ─── TEST 1: Fetch the actual bulletin page from imdagrimet.gov.in ───
print("=" * 80)
print("TEST 1: imdagrimet.gov.in District Bulletin pages")
print("=" * 80)

for district in ["Nashik", "Pune"]:
    url = f"https://imdagrimet.gov.in/Services/DistrictBulletin.php?state=Maharashtra&district={district}&language=English"
    print(f"\n--- {district} Bulletin ---")
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
            raw = res.read()
            content_type = res.headers.get('Content-Type', '')
            print(f"Status: {res.status}")
            print(f"Content-Type: {content_type}")
            print(f"Content-Length: {len(raw)} bytes")
            
            if 'pdf' in content_type.lower():
                fname = f'data/imd_bulletin_{district.lower()}.pdf'
                with open(fname, 'wb') as f:
                    f.write(raw)
                print(f"Saved PDF to {fname}")
                # Check if PDF header is present
                if raw[:4] == b'%PDF':
                    print("  Confirmed: Valid PDF file")
                else:
                    print(f"  First 200 bytes: {raw[:200]}")
            elif 'html' in content_type.lower() or raw[:10].decode('utf-8', errors='replace').strip().startswith('<'):
                html = raw.decode('utf-8', errors='replace')
                fname = f'data/imd_bulletin_{district.lower()}.html'
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(html)
                print(f"Saved HTML to {fname}")
                print(f"Content preview (first 1000 chars):")
                print(html[:1000])
            else:
                print(f"Unknown content type. First 500 bytes:")
                print(raw[:500])
    except Exception as e:
        print(f"FAILED: {e}")

# ─── TEST 2: Explore imdagrimet.gov.in for structured data endpoints ───
print("\n" + "=" * 80)
print("TEST 2: Explore imdagrimet.gov.in for other endpoints")
print("=" * 80)

probe_urls = [
    ("Services landing page", "https://imdagrimet.gov.in/Services/"),
    ("API or data endpoint", "https://imdagrimet.gov.in/api/"),
    ("District Advisory JSON?", "https://imdagrimet.gov.in/Services/getDistrictAdvisory.php?state=Maharashtra&district=Nashik"),
    ("District Weather Data?", "https://imdagrimet.gov.in/Services/getWeatherData.php?state=Maharashtra&district=Nashik"),
    ("Forecast endpoint?", "https://imdagrimet.gov.in/Services/DistrictForecast.php?state=Maharashtra&district=Nashik"),
    ("GKMS Bulletin API?", "https://imdagrimet.gov.in/gkms/bulletin.php?state=Maharashtra&district=Nashik"),
    ("Home page", "https://imdagrimet.gov.in/"),
]

for label, url in probe_urls:
    print(f"\n--- {label} ---")
    print(f"URL: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
            raw = res.read()
            ct = res.headers.get('Content-Type', '')
            print(f"Status: {res.status}, Content-Type: {ct}, Length: {len(raw)}")
            if 'html' in ct.lower() or len(raw) < 50000:
                text = raw.decode('utf-8', errors='replace')
                # Look for structured data, tables, or API references
                if any(k in text.lower() for k in ['forecast', 'rainfall', 'weather', 'advisory']):
                    print("  Contains weather/forecast/advisory content!")
                    # Save it
                    safe = label.replace(" ", "_").replace("/", "").replace("?", "")
                    with open(f'data/imdagrimet_{safe}.html', 'w', encoding='utf-8') as f:
                        f.write(text)
                    # Look for forecast tables
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, 'html.parser')
                    tables = soup.find_all('table')
                    print(f"  Tables found: {len(tables)}")
                    for ti, t in enumerate(tables):
                        rows = t.find_all('tr')
                        if rows:
                            header_text = rows[0].get_text(' | ', strip=True)
                            print(f"  Table {ti}: {len(rows)} rows, header: {header_text[:150]}")
                            # Check for rainfall numbers
                            for r in rows[1:4]:
                                row_text = r.get_text(' | ', strip=True)
                                if any(k in row_text.lower() for k in ['rain', 'mm', 'forecast', 'nashik', 'pune']):
                                    print(f"    Matching row: {row_text[:200]}")
                else:
                    print(f"  Content preview: {text[:200]}")
    except Exception as e:
        print(f"FAILED: {e}")

# ─── TEST 3: Check the PDF bulletin content for structured forecast table ───
print("\n" + "=" * 80)
print("TEST 3: Check if bulletin is actually a rendered HTML page (not just PDF)")
print("=" * 80)

for district in ["Nashik", "Pune"]:
    # Try without download attribute to see if it renders as HTML
    url = f"https://imdagrimet.gov.in/Services/DistrictBulletin.php?state=Maharashtra&district={district}&language=English"
    print(f"\n--- {district}: checking response headers ---")
    try:
        req = urllib.request.Request(url, headers={**HEADERS, 'Accept': 'text/html'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
            ct = res.headers.get('Content-Type', '')
            cl = res.headers.get('Content-Length', 'unknown')
            cd = res.headers.get('Content-Disposition', 'none')
            print(f"Content-Type: {ct}")
            print(f"Content-Length: {cl}")
            print(f"Content-Disposition: {cd}")
            
            raw = res.read(5000)  # Read only first 5KB
            if raw[:4] == b'%PDF':
                print("  Response IS a raw PDF binary")
                # Try to extract text from first page
                text = raw.decode('latin-1', errors='replace')
                # Look for text streams in PDF
                streams = re.findall(r'BT\s*(.*?)\s*ET', text, re.DOTALL)
                if streams:
                    print(f"  Found {len(streams)} text blocks in PDF header")
                    for s in streams[:3]:
                        # Extract Tj/TJ text
                        texts = re.findall(r'\(([^)]+)\)', s)
                        if texts:
                            print(f"    Text: {' '.join(texts[:5])}")
            else:
                html_text = raw.decode('utf-8', errors='replace')
                print(f"  Response is HTML/text. Preview:")
                print(html_text[:500])
    except Exception as e:
        print(f"FAILED: {e}")
