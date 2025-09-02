import asyncio
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from sqlite_repo import SQLiteRepository
from comprehensive_parser import extract_comprehensive_ski_doo_data
from src.models.domain import PriceList, ProcessingStatus

async def main():
    print("=== SKI-DOO 2026 Price List Extraction Test ===\n")
    
    # Initialize database repository
    db_repo = SQLiteRepository("snowmobile_reconciliation.db")
    
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
        market="FI",
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
    
    # Extract using comprehensive parser
    print("Starting comprehensive extraction...")
    start_time = datetime.now()
    
    try:
        entries = extract_comprehensive_ski_doo_data(pdf_path)
        
        if not entries:
            print("No entries extracted!")
            return
        
        print(f"\nExtracted {len(entries)} entries successfully!")
        
        # Store entries in database
        stored_count = 0
        failed_count = 0
        
        for entry_data in entries:
            try:
                # Set price_list_id
                entry_data['price_list_id'] = price_list_id
                
                # Convert to database format
                from src.models.domain import PriceEntry
                
                entry = PriceEntry(
                    id=entry_data['id'],
                    price_list_id=entry_data['price_list_id'],
                    model_code=entry_data['model_code'],
                    malli=entry_data['malli'],
                    paketti=entry_data['paketti'],
                    moottori=entry_data['moottori'],
                    telamatto=entry_data['telamatto'],
                    kaynnistin=entry_data['kaynnistin'],
                    mittaristo=entry_data['mittaristo'],
                    kevatoptiot=entry_data['kevatoptiot'],
                    vari=entry_data['vari'],
                    price=entry_data['price'],
                    currency=entry_data['currency'],
                    market=entry_data['market'],
                    brand=entry_data['brand'],
                    model_year=entry_data['model_year'],
                    catalog_lookup_key=entry_data['catalog_lookup_key'],
                    status=ProcessingStatus.EXTRACTED,
                    created_at=datetime.now()
                )
                
                await db_repo.create_price_entry(entry)
                stored_count += 1
                
            except Exception as e:
                print(f"Failed to store entry {entry_data.get('model_code', 'unknown')}: {e}")
                failed_count += 1
                continue
        
        # Update price list statistics
        await db_repo.update_price_list_stats(
            price_list_id,
            total_entries=len(entries),
            processed_entries=stored_count,
            failed_entries=failed_count,
            status=ProcessingStatus.COMPLETED
        )
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"\n=== EXTRACTION COMPLETE ===")
        print(f"Total entries extracted: {len(entries)}")
        print(f"Successfully stored: {stored_count}")
        print(f"Failed to store: {failed_count}")
        print(f"Processing time: {processing_time:.0f}ms")
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
    
    # Query and display first 10 entries from database
    print(f"\n=== FIRST 10 ENTRIES FROM DATABASE ===")
    
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT model_code, malli, paketti, moottori, telamatto, kaynnistin, 
               mittaristo, kevatoptiot, vari, price, currency, market, brand, model_year
        FROM price_entries 
        WHERE price_list_id = ?
        ORDER BY model_code
        LIMIT 10
    """, (str(price_list_id),))
    
    entries = cursor.fetchall()
    if entries:
        print("\nCode | Model     | Package        | Engine             | Track      | Starter | Display          | Options    | Color              | Price")
        print("-" * 160)
        
        for entry in entries:
            model_code = entry[0] or ""
            malli = (entry[1] or "")[:9]
            paketti = (entry[2] or "")[:14] 
            moottori = (entry[3] or "")[:18]
            telamatto = (entry[4] or "")[:10]
            kaynnistin = (entry[5] or "")[:7]
            mittaristo = (entry[6] or "")[:16]
            kevatoptiot = (entry[7] or "")[:10]
            vari = (entry[8] or "")[:18]
            price = entry[9]
            currency = entry[10]
            
            print(f"{model_code:<4} | {malli:<9} | {paketti:<14} | {moottori:<18} | {telamatto:<10} | {kaynnistin:<7} | {mittaristo:<16} | {kevatoptiot:<10} | {vari:<18} | {price} {currency}")
    else:
        print("No entries found in database")
    
    conn.close()
    
    # Show database statistics
    print(f"\n=== DATABASE STATISTICS ===")
    conn = sqlite3.connect("snowmobile_reconciliation.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM price_entries WHERE price_list_id = ?", (str(price_list_id),))
    total_entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT model_code) FROM price_entries WHERE price_list_id = ?", (str(price_list_id),))
    unique_models = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT malli) FROM price_entries WHERE price_list_id = ?", (str(price_list_id),))
    unique_mallis = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(price) FROM price_entries WHERE price_list_id = ?", (str(price_list_id),))
    avg_price = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(price), MAX(price) FROM price_entries WHERE price_list_id = ?", (str(price_list_id),))
    min_price, max_price = cursor.fetchone()
    
    print(f"Total entries in database: {total_entries}")
    print(f"Unique model codes: {unique_models}")
    print(f"Unique model names: {unique_mallis}")
    print(f"Price range: {min_price}€ - {max_price}€")
    print(f"Average price: {avg_price:.2f}€")
    
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())