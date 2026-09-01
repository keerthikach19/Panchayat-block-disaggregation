import urllib.request
import ssl
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://city.imd.gov.in/citywx/assets/index-C8XcC-ir.js', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
    js = res.read().decode('utf-8', errors='replace')

print('JS length:', len(js))
urls = re.findall(r'https?://[a-zA-Z0-9_\-\.\/:\?=&]+', js)
print('URLs in citywx JS:')
for u in sorted(list(set(urls))):
    print('  *', u)

# Search for fetch or axios or endpoints
endpoints = re.findall(r'(?:fetch|get|post)\s*\(\s*[\'\"\`]([^\'\"\`]+)[\'\"\`]', js)
print('Fetch/Get endpoints in JS:')
for ep in sorted(list(set(endpoints))):
    print('  ->', ep)
