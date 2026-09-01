import sys
import io
import re
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('data/imd_api_reference.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

print("=" * 75)
print("  COMPLETE IMD API ENDPOINTS EXTRACTED FROM OFFICIAL REFERENCE")
print("=" * 75)

# Find all headings or list items
urls = re.findall(r'https://api\.imd\.gov\.in/api/v1/[a-zA-Z0-9_\-\?=&]+', html)
unique_urls = sorted(list(set(urls)))

for u in unique_urls:
    print("  *", u)

print("\n" + "=" * 75)
print("  DETAILED ENDPOINT SPECIFICATIONS")
print("=" * 75)

# Let's search for endpoint blocks
divs = soup.find_all(['div', 'section', 'article', 'li'])
for u in unique_urls:
    base = u.split('?')[0]
    print(f"\n[ENDPOINT] {u}")
    # Find occurrences in text
    for tag in soup.find_all(string=re.compile(re.escape(base))):
        parent = tag.find_parent(['div', 'li', 'p', 'table', 'tr', 'td'])
        if parent:
            print("  Context:", parent.get_text(' ', strip=True)[:250])
            break
