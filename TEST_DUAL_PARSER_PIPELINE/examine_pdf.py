import fitz  # PyMuPDF
from pathlib import Path
import pdfplumber

def examine_with_pymupdf():
    pdf_path = Path("../data/SKI-DOO_2026-PRICE_LIST.pdf")
    doc = fitz.open(pdf_path)
    
    print("=== PyMuPDF Analysis ===")
    print(f"Total pages: {len(doc)}")
    
    # Examine first few pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        print(f"\n--- Page {page_num + 1} ---")
        
        # Get text
        text = page.get_text()
        print(f"Text length: {len(text)}")
        print("First 500 characters:")
        print(text[:500])
        
        # Find tables
        try:
            tables = page.find_tables()
            print(f"Tables found: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"\nTable {i}:")
                try:
                    table_data = table.extract()
                    if table_data:
                        print(f"Dimensions: {len(table_data)} rows x {len(table_data[0]) if table_data[0] else 0} columns")
                        print("Headers (first row):")
                        print(table_data[0] if table_data else "No data")
                        if len(table_data) > 1:
                            print("Sample data (second row):")
                            print(table_data[1])
                except Exception as e:
                    print(f"Error extracting table: {e}")
        except Exception as e:
            print(f"Error finding tables: {e}")
    
    doc.close()

def examine_with_pdfplumber():
    pdf_path = Path("../data/SKI-DOO_2026-PRICE_LIST.pdf")
    
    print("\n\n=== PDFPlumber Analysis ===")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        for page_num in range(min(3, len(pdf.pages))):
            page = pdf.pages[page_num]
            print(f"\n--- Page {page_num + 1} ---")
            
            # Extract text
            text = page.extract_text()
            print(f"Text length: {len(text) if text else 0}")
            if text:
                print("First 500 characters:")
                print(text[:500])
            
            # Extract tables
            tables = page.extract_tables()
            print(f"Tables found: {len(tables)}")
            
            for i, table in enumerate(tables):
                print(f"\nTable {i}:")
                if table:
                    print(f"Dimensions: {len(table)} rows x {len(table[0]) if table[0] else 0} columns")
                    print("Headers (first row):")
                    print(table[0] if table else "No data")
                    if len(table) > 1:
                        print("Sample data (second row):")
                        print(table[1])

if __name__ == "__main__":
    try:
        examine_with_pymupdf()
    except Exception as e:
        print(f"PyMuPDF examination failed: {e}")
    
    try:
        examine_with_pdfplumber()
    except Exception as e:
        print(f"PDFPlumber examination failed: {e}")