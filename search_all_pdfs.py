#!/usr/bin/env python3
"""
Search for AYTS in all PDF files to find the correct location.
"""
import PyPDF2
import glob
from pathlib import Path

def search_ayts_in_all_pdfs():
    """Search for AYTS in all available PDF files"""
    
    pdf_files = glob.glob("data/*.pdf")
    print(f"Searching for AYTS in {len(pdf_files)} PDF files...")
    
    for pdf_path in pdf_files:
        print(f"\n--- Checking: {Path(pdf_path).name} ---")
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                print(f"Pages: {len(pdf_reader.pages)}")
                
                ayts_found = False
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    
                    # Look for AYTS
                    if "AYTS" in text:
                        print(f"AYTS FOUND on page {page_num}!")
                        ayts_found = True
                        
                        # Extract relevant lines
                        lines = text.split('\n')
                        for i, line in enumerate(lines):
                            if "AYTS" in line:
                                print(f"Line: {line.strip()}")
                                # Print context
                                context_start = max(0, i-2)
                                context_end = min(len(lines), i+3)
                                context = lines[context_start:context_end]
                                print("Context:")
                                for ctx_line in context:
                                    print(f"  {ctx_line.strip()}")
                                break
                    
                    # Also look for patterns that might be AYTS
                    if any(pattern in text for pattern in ["25110", "25,110", "Expedition SE", "900 ACE Turbo R"]):
                        print(f"Related content found on page {page_num}")
                        lines = text.split('\n')
                        for line in lines:
                            if any(pattern in line for pattern in ["25110", "25,110", "Expedition SE", "900 ACE Turbo"]):
                                print(f"  Relevant line: {line.strip()}")
                
                if not ayts_found:
                    print("AYTS not found in this PDF")
                    
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

def sample_pdf_content():
    """Sample content from PDFs to understand the format"""
    
    ski_doo_pdfs = [f for f in glob.glob("data/*.pdf") if "SKI-DOO" in f or "SKIDOO" in f]
    
    for pdf_path in ski_doo_pdfs:
        print(f"\n--- Sampling content from: {Path(pdf_path).name} ---")
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Sample first page
                if len(pdf_reader.pages) > 0:
                    first_page = pdf_reader.pages[0]
                    text = first_page.extract_text()
                    print("First page sample:")
                    print(text[:500] + "..." if len(text) > 500 else text)
                
                # Sample last page
                if len(pdf_reader.pages) > 1:
                    last_page = pdf_reader.pages[-1]
                    text = last_page.extract_text()
                    print("\nLast page sample:")
                    print(text[:500] + "..." if len(text) > 500 else text)
                    
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

if __name__ == "__main__":
    # First search for AYTS specifically
    search_ayts_in_all_pdfs()
    
    print("\n" + "="*60)
    print("SAMPLING PDF CONTENT FOR FORMAT ANALYSIS")
    print("="*60)
    
    # Sample content to understand PDF format
    sample_pdf_content()