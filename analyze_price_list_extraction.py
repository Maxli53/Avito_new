#!/usr/bin/env python3
"""
PDF Extraction Tool Analysis
Tests Camelot, Tabula, pdfplumber, and PyPDF2 on all price list PDFs
"""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# PDF extraction libraries
import camelot
import tabula
import pdfplumber
import PyPDF2

def analyze_pdf_with_camelot(pdf_path: Path) -> Dict[str, Any]:
    """Analyze PDF table structure with Camelot"""
    try:
        # Try both lattice and stream parsing
        results = {}
        
        # Lattice method (for PDFs with clear table lines)
        try:
            lattice_tables = camelot.read_pdf(str(pdf_path), flavor='lattice', pages='all')
            results['lattice'] = {
                'tables_found': len(lattice_tables),
                'accuracy_scores': [t.accuracy for t in lattice_tables] if lattice_tables else [],
                'sample_data': lattice_tables[0].df.head(3).to_dict() if lattice_tables else None
            }
        except Exception as e:
            results['lattice'] = {'error': str(e)}
        
        # Stream method (for PDFs without clear table lines)
        try:
            stream_tables = camelot.read_pdf(str(pdf_path), flavor='stream', pages='all')
            results['stream'] = {
                'tables_found': len(stream_tables),
                'accuracy_scores': [t.accuracy for t in stream_tables] if stream_tables else [],
                'sample_data': stream_tables[0].df.head(3).to_dict() if stream_tables else None
            }
        except Exception as e:
            results['stream'] = {'error': str(e)}
        
        return results
    except Exception as e:
        return {'error': str(e)}

def analyze_pdf_with_tabula(pdf_path: Path) -> Dict[str, Any]:
    """Analyze PDF table structure with Tabula"""
    try:
        # Get all tables from all pages
        tables = tabula.read_pdf(str(pdf_path), pages='all', multiple_tables=True)
        
        result = {
            'tables_found': len(tables),
            'sample_data': None
        }
        
        if tables and len(tables) > 0:
            # Get sample from first table
            first_table = tables[0]
            result['sample_data'] = first_table.head(3).to_dict()
            result['table_shapes'] = [df.shape for df in tables]
            result['columns'] = [list(df.columns) for df in tables]
        
        return result
    except Exception as e:
        return {'error': str(e)}

def analyze_pdf_with_pdfplumber(pdf_path: Path) -> Dict[str, Any]:
    """Analyze PDF table structure with pdfplumber"""
    try:
        result = {
            'pages': 0,
            'tables_found': 0,
            'sample_data': None,
            'page_info': []
        }
        
        with pdfplumber.open(pdf_path) as pdf:
            result['pages'] = len(pdf.pages)
            
            total_tables = 0
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                page_tables = len(tables)
                total_tables += page_tables
                
                result['page_info'].append({
                    'page': page_num + 1,
                    'tables': page_tables,
                    'text_length': len(page.extract_text() or '')
                })
                
                # Get sample data from first table found
                if tables and result['sample_data'] is None:
                    # Convert table to more readable format
                    table = tables[0]
                    if len(table) > 0:
                        result['sample_data'] = {
                            'headers': table[0] if table[0] else [],
                            'sample_rows': table[1:min(4, len(table))]
                        }
            
            result['tables_found'] = total_tables
        
        return result
    except Exception as e:
        return {'error': str(e)}

def analyze_pdf_with_pypdf2(pdf_path: Path) -> Dict[str, Any]:
    """Analyze PDF structure with PyPDF2 (text extraction only)"""
    try:
        result = {
            'pages': 0,
            'total_text_length': 0,
            'sample_text': '',
            'contains_finnish_terms': False
        }
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            result['pages'] = len(reader.pages)
            
            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                full_text += page_text + "\\n"
            
            result['total_text_length'] = len(full_text)
            result['sample_text'] = full_text[:500]  # First 500 characters
            
            # Check for Finnish terms
            finnish_terms = ['Tuotenro', 'Malli', 'Paketti', 'Moottori', 'Telamatto', 'Käynnistin', 'Mittaristo', 'Väri']
            result['contains_finnish_terms'] = any(term in full_text for term in finnish_terms)
            result['found_finnish_terms'] = [term for term in finnish_terms if term in full_text]
        
        return result
    except Exception as e:
        return {'error': str(e)}

def analyze_all_price_lists():
    """Analyze all price list PDFs with all extraction tools"""
    price_list_files = [
        "data/SKI-DOO_2026-PRICE_LIST.pdf",
        "data/SKI-DOO_2025-PRICE_LIST.pdf", 
        "data/SKI-DOO_2024-PRICE_LIST.pdf",
        "data/LYNX_2026-PRICE_LIST.pdf",
        "data/LYNX_2025-PRICE_LIST.pdf",
        "data/LYNX_2024-PRICE_LIST.pdf"
    ]
    
    results = {}
    
    print("COMPREHENSIVE PDF EXTRACTION ANALYSIS")
    print("=" * 60)
    
    for pdf_file in price_list_files:
        pdf_path = Path(pdf_file)
        if not pdf_path.exists():
            print(f"SKIPPING {pdf_file} - File not found")
            continue
        
        print(f"\\nAnalyzing: {pdf_path.name}")
        print("-" * 40)
        
        file_results = {}
        
        # Test Camelot
        print("Testing Camelot...")
        camelot_result = analyze_pdf_with_camelot(pdf_path)
        file_results['camelot'] = camelot_result
        
        if 'error' not in camelot_result:
            lattice_tables = camelot_result.get('lattice', {}).get('tables_found', 0)
            stream_tables = camelot_result.get('stream', {}).get('tables_found', 0)
            print(f"  Lattice: {lattice_tables} tables, Stream: {stream_tables} tables")
        else:
            print(f"  ERROR: {camelot_result['error']}")
        
        # Test Tabula
        print("Testing Tabula...")
        tabula_result = analyze_pdf_with_tabula(pdf_path)
        file_results['tabula'] = tabula_result
        
        if 'error' not in tabula_result:
            print(f"  Found: {tabula_result.get('tables_found', 0)} tables")
        else:
            print(f"  ERROR: {tabula_result['error']}")
        
        # Test pdfplumber
        print("Testing pdfplumber...")
        pdfplumber_result = analyze_pdf_with_pdfplumber(pdf_path)
        file_results['pdfplumber'] = pdfplumber_result
        
        if 'error' not in pdfplumber_result:
            print(f"  Pages: {pdfplumber_result.get('pages', 0)}, Tables: {pdfplumber_result.get('tables_found', 0)}")
        else:
            print(f"  ERROR: {pdfplumber_result['error']}")
        
        # Test PyPDF2
        print("Testing PyPDF2...")
        pypdf2_result = analyze_pdf_with_pypdf2(pdf_path)
        file_results['pypdf2'] = pypdf2_result
        
        if 'error' not in pypdf2_result:
            finnish_found = len(pypdf2_result.get('found_finnish_terms', []))
            print(f"  Pages: {pypdf2_result.get('pages', 0)}, Finnish terms: {finnish_found}")
        else:
            print(f"  ERROR: {pypdf2_result['error']}")
        
        results[pdf_file] = file_results
    
    return results

def generate_summary(results: Dict[str, Any]):
    """Generate summary and recommendations"""
    print("\\n" + "=" * 60)
    print("ANALYSIS SUMMARY AND RECOMMENDATIONS")
    print("=" * 60)
    
    tools_success = {'camelot': 0, 'tabula': 0, 'pdfplumber': 0, 'pypdf2': 0}
    best_table_counts = {'camelot': 0, 'tabula': 0, 'pdfplumber': 0}
    
    for pdf_file, file_results in results.items():
        print(f"\\n{Path(pdf_file).name}:")
        
        for tool, result in file_results.items():
            if 'error' not in result:
                tools_success[tool] += 1
                
                if tool == 'camelot':
                    lattice_count = result.get('lattice', {}).get('tables_found', 0)
                    stream_count = result.get('stream', {}).get('tables_found', 0)
                    max_tables = max(lattice_count, stream_count)
                    best_table_counts[tool] += max_tables
                    print(f"  Camelot: {max_tables} tables (L:{lattice_count}, S:{stream_count})")
                
                elif tool == 'tabula':
                    table_count = result.get('tables_found', 0)
                    best_table_counts[tool] += table_count
                    print(f"  Tabula: {table_count} tables")
                
                elif tool == 'pdfplumber':
                    table_count = result.get('tables_found', 0)
                    best_table_counts[tool] += table_count
                    print(f"  pdfplumber: {table_count} tables")
                
                elif tool == 'pypdf2':
                    finnish_count = len(result.get('found_finnish_terms', []))
                    print(f"  PyPDF2: {finnish_count} Finnish terms found")
            else:
                print(f"  {tool}: FAILED - {result['error'][:50]}...")
    
    print(f"\\nSUCCESS RATES:")
    total_files = len(results)
    for tool, success_count in tools_success.items():
        rate = (success_count / total_files) * 100 if total_files > 0 else 0
        print(f"  {tool:12}: {success_count}/{total_files} files ({rate:.1f}%)")
    
    print(f"\\nTOTAL TABLES EXTRACTED:")
    for tool, count in best_table_counts.items():
        print(f"  {tool:12}: {count} total tables")
    
    # Recommendation
    print(f"\\nRECOMMENDATION:")
    if best_table_counts['camelot'] > 0:
        print("✅ USE CAMELOT - Best table extraction performance")
    elif best_table_counts['pdfplumber'] > 0:
        print("✅ USE PDFPLUMBER - Good table detection")
    elif best_table_counts['tabula'] > 0:
        print("✅ USE TABULA - Alternative table extraction")
    else:
        print("⚠️  USE PYPDF2 + REGEX - No table extraction worked, fall back to text parsing")

if __name__ == "__main__":
    results = analyze_all_price_lists()
    generate_summary(results)