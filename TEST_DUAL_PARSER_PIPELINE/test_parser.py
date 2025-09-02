import asyncio
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from sqlite_repo import SQLiteRepository
from src.services.price_extractor import PriceListExtractor
from src.models.domain import PriceList, ProcessingStatus

async def main():
    # Initialize database repository
    db_repo = SQLiteRepository("snowmobile_reconciliation.db")
    
    # Create price list extractor
    extractor = PriceListExtractor(db_repo)
    
    # PDF path
    pdf_path = Path("../data/SKI-DOO_2026-PRICE_LIST.pdf")
    
    if not pdf_path.exists():
        print(f"PDF file not found at {pdf_path}")
        return
    
    # Create a price list record first
    price_list_id = uuid4()
    price_list = PriceList(
        id=price_list_id,
        filename="SKI-DOO_2026-PRICE_LIST.pdf",
        market="US",
        brand="SKI-DOO",
        model_year=2026,
        status=ProcessingStatus.PENDING,
        uploaded_at=datetime.now(),
        total_entries=0,
        processed_entries=0
    )
    
    # Store the price list
    await db_repo.create_price_list(price_list)
    print(f"Created price list record with ID: {price_list_id}")
    
    # Extract from PDF
    print("Starting extraction...")
    result = await extractor.extract_from_pdf(pdf_path, price_list_id)
    
    if result.success:
        print(f"Extraction successful!")
        print(f"Entries extracted: {result.entries_extracted}")
        print(f"Processing time: {result.processing_time_ms}ms")
        print(f"Confidence score: {result.confidence_score}")
    else:
        print(f"Extraction failed: {result.error_message}")
    
    # Query first 10 entries
    print("\nFirst 10 price entries:")
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT model_code, malli, price, currency, market, brand, model_year
        FROM price_entries 
        WHERE price_list_id = ?
        ORDER BY created_at
        LIMIT 10
    """, (str(price_list_id),))
    
    entries = cursor.fetchall()
    if entries:
        print("Model Code | Model | Price | Currency | Market | Brand | Year")
        print("-" * 70)
        for entry in entries:
            print(f"{entry[0]:<10} | {entry[1]:<15} | {entry[2]:<8} | {entry[3]:<8} | {entry[4]:<6} | {entry[5]:<8} | {entry[6]}")
    else:
        print("No entries found")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())