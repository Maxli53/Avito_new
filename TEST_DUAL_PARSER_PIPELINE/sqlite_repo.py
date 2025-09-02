import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from src.models.domain import PriceList, PriceEntry, ProcessingStatus

logger = logging.getLogger(__name__)

class SQLiteRepository:
    """Simplified SQLite repository for testing"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db"):
        self.db_path = db_path
    
    async def create_price_list(self, price_list: PriceList):
        """Create a price list record"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO price_lists (id, filename, brand, market, model_year, total_entries, 
                                       processed_entries, failed_entries, status, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(price_list.id),
                price_list.filename,
                price_list.brand,
                price_list.market,
                price_list.model_year,
                price_list.total_entries,
                price_list.processed_entries,
                price_list.failed_entries,
                price_list.status.value,
                price_list.uploaded_at.isoformat() if price_list.uploaded_at else None
            ))
            conn.commit()
            logger.info(f"Created price list: {price_list.id}")
        finally:
            conn.close()
    
    async def get_price_list(self, price_list_id: UUID) -> Optional[PriceList]:
        """Get a price list by ID"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, brand, market, model_year, total_entries,
                       processed_entries, failed_entries, status, uploaded_at
                FROM price_lists WHERE id = ?
            """, (str(price_list_id),))
            
            row = cursor.fetchone()
            if row:
                return PriceList(
                    id=UUID(row[0]),
                    filename=row[1],
                    brand=row[2],
                    market=row[3],
                    model_year=row[4],
                    total_entries=row[5],
                    processed_entries=row[6],
                    failed_entries=row[7],
                    status=ProcessingStatus(row[8]),
                    uploaded_at=datetime.fromisoformat(row[9]) if row[9] else None
                )
            return None
        finally:
            conn.close()
    
    async def create_price_entry(self, entry: PriceEntry):
        """Create a price entry"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO price_entries (
                    id, price_list_id, model_code, malli, paketti, moottori, telamatto,
                    kaynnistin, mittaristo, kevatoptiot, vari, price, currency,
                    market, brand, model_year, catalog_lookup_key, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(entry.id),
                str(entry.price_list_id),
                entry.model_code,
                entry.malli,
                entry.paketti,
                entry.moottori,
                entry.telamatto,
                entry.kaynnistin,
                entry.mittaristo,
                entry.kevatoptiot,
                entry.vari,
                float(entry.price),
                entry.currency,
                entry.market,
                entry.brand,
                entry.model_year,
                entry.catalog_lookup_key,
                entry.status.value,
                entry.created_at.isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to create price entry: {e}")
            raise
        finally:
            conn.close()
    
    async def update_price_list_stats(self, price_list_id: UUID, **kwargs):
        """Update price list statistics"""
        conn = sqlite3.connect(self.db_path)
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field == 'status' and hasattr(value, 'value'):
                    update_fields.append(f"{field} = ?")
                    values.append(value.value)
                else:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if update_fields:
                query = f"UPDATE price_lists SET {', '.join(update_fields)} WHERE id = ?"
                values.append(str(price_list_id))
                conn.execute(query, values)
                conn.commit()
        finally:
            conn.close()