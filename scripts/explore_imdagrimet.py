"""
Explore imdagrimet.gov.in home page for AJAX endpoints, structured forecast data.
"""
import urllib.request
import ssl
import re
import sys
import io
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Fetch imdagrimet.gov.in home page
req = urllib.request.Request('https://imdagrimet.gov.in/', headers=HEADERS)
with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
    html = res.read().decode('utf-8', errors='replace')

print(f"Home page size: {len(html)} bytes")

# Extract all script sources and inline scripts
soup = BeautifulSoup(html, 'html.parser')

# 1. External script sources
print("\n=== External Script Sources ===")
for s in soup.find_all('script', src=True):
    src = s['src']
    if 'google' not in src and 'analytics' not in src and 'jquery' not in src.lower() and 'bootstrap' not in src.lower():
        print(f"  {src}")

# 2. Inline scripts with AJAX or fetch
print("\n=== Inline Scripts with Data Calls ===")
for s in soup.find_all('script'):
    text = s.get_text()
    if any(k in text.lower() for k in ['ajax', 'fetch', 'xmlhttp', 'getjson', '.php', 'forecast', 'rainfall', 'advisory']):
        print(f"  Script ({len(text)} chars):")
        print(f"  {text[:500]}")
        # Extract URLs
        urls = re.findall(r'["\']([^"\']*\.php[^"\']*)["\']', text)
        if urls:
            print(f"  PHP endpoints found: {urls}")
        print()

# 3. All links to PHP pages on this domain
print("\n=== PHP Links on imdagrimet.gov.in ===")
for a in soup.find_all('a', href=True):
    href = a['href']
    if '.php' in href and 'imdagrimet' in href or (href.startswith('/') and '.php' in href):
        print(f"  {a.get_text(strip=True)[:50]} -> {href}")

# 4. Directory listing of /Services/
print("\n=== /Services/ Directory Listing ===")
req2 = urllib.request.Request('https://imdagrimet.gov.in/Services/', headers=HEADERS)
with urllib.request.urlopen(req2, context=ctx, timeout=10) as res2:
    dir_html = res2.read().decode('utf-8', errors='replace')
soup2 = BeautifulSoup(dir_html, 'html.parser')
for a in soup2.find_all('a', href=True):
    href = a['href']
    if href not in ['/', '../', '?C=N;O=D', '?C=M;O=A', '?C=S;O=A', '?C=D;O=A']:
        print(f"  {href}")
