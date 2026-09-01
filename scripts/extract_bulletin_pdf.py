"""
Extract text from the Nashik GKMS PDF bulletin to find the actual
forward-looking forecast table (rainfall categories, dates, etc.)
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pdfplumber', '-q'])
    import pdfplumber

for district in ['nashik', 'pune']:
    pdf_path = f'data/imd_bulletin_{district}.pdf'
    print("=" * 80)
    print(f"  EXTRACTING TEXT FROM: {pdf_path}")
    print("=" * 80)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"  Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                tables = page.extract_tables()
                
                print(f"\n--- Page {page_num + 1} ---")
                if text:
                    print(f"Text ({len(text)} chars):")
                    print(text[:2000])
                    if len(text) > 2000:
                        print("... [truncated]")
                
                if tables:
                    print(f"\nTables found on page {page_num + 1}: {len(tables)}")
                    for ti, table in enumerate(tables):
                        print(f"  Table {ti} ({len(table)} rows):")
                        for ri, row in enumerate(table[:8]):  # Show first 8 rows
                            print(f"    Row {ri}: {row}")
                
                # Only process first 3 pages to keep output manageable
                if page_num >= 2:
                    print(f"\n... (skipping remaining {len(pdf.pages) - 3} pages)")
                    break
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
