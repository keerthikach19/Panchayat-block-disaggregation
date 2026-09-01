import urllib.request
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(
    'https://mausam.imd.gov.in/responsive/apis.php',
    headers={'User-Agent': 'Mozilla/5.0'}
)
with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
    html = res.read().decode('utf-8', errors='replace')

soup = BeautifulSoup(html, 'html.parser')
with open('data/imd_apis_dump.txt', 'w', encoding='utf-8') as f:
    f.write(soup.get_text('\n', strip=True))

print("Dumped", len(html), "bytes to data/imd_apis_dump.txt")
