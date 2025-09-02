"""
Validate Extracted Price List Data
Comprehensive validation of all extracted Finnish price list data
"""

import sqlite3
from pathlib import Path

class DataValidator:
    """Validate extracted price list data quality"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db"):
        self.db_path = db_path
    
    def validate_all_data(self):
        """Run comprehensive validation on all extracted data"""
        print("=== COMPREHENSIVE DATA VALIDATION ===\n")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Overall statistics
        print("1. OVERALL STATISTICS:")
        cursor.execute("SELECT COUNT(*) FROM price_entries")
        total_entries = cursor.fetchone()[0]
        print(f"   Total entries: {total_entries}")
        
        # By brand/year
        cursor.execute("""
            SELECT brand, model_year, COUNT(*) 
            FROM price_entries 
            GROUP BY brand, model_year 
            ORDER BY brand, model_year
        """)
        
        print("   Distribution by brand/year:")
        for brand, year, count in cursor.fetchall():
            print(f"     {brand} {year}: {count} entries")
        
        # 2. Data quality metrics
        print(f"\n2. DATA QUALITY METRICS:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN malli IS NOT NULL AND malli != '' THEN 1 END) as with_malli,
                COUNT(CASE WHEN paketti IS NOT NULL AND paketti != '' THEN 1 END) as with_paketti,
                COUNT(CASE WHEN moottori IS NOT NULL AND moottori != '' THEN 1 END) as with_moottori,
                COUNT(CASE WHEN vari IS NOT NULL AND vari != '' THEN 1 END) as with_vari,
                COUNT(CASE WHEN normalized_model_name IS NOT NULL AND normalized_model_name != '' THEN 1 END) as normalized_model,
                COUNT(CASE WHEN normalized_package_name IS NOT NULL AND normalized_package_name != '' THEN 1 END) as normalized_package
            FROM price_entries
        """)
        
        stats = cursor.fetchone()
        total, with_malli, with_paketti, with_moottori, with_vari, norm_model, norm_package = stats
        
        print(f"   Model names (malli): {with_malli}/{total} ({with_malli/total*100:.1f}%)")
        print(f"   Package names (paketti): {with_paketti}/{total} ({with_paketti/total*100:.1f}%)")
        print(f"   Engine specs (moottori): {with_moottori}/{total} ({with_moottori/total*100:.1f}%)")
        print(f"   Colors (vari): {with_vari}/{total} ({with_vari/total*100:.1f}%)")
        print(f"   Normalized models: {norm_model}/{total} ({norm_model/total*100:.1f}%)")
        print(f"   Normalized packages: {norm_package}/{total} ({norm_package/total*100:.1f}%)")
        
        # 3. Model code validation
        print(f"\n3. MODEL CODE VALIDATION:")
        cursor.execute("SELECT COUNT(DISTINCT model_code) FROM price_entries")
        unique_codes = cursor.fetchone()[0]
        print(f"   Unique model codes: {unique_codes}")
        print(f"   Duplicate rate: {(total - unique_codes)/total*100:.1f}%")
        
        # Check for suspicious model codes
        cursor.execute("SELECT model_code, COUNT(*) as count FROM price_entries GROUP BY model_code HAVING count > 1 ORDER BY count DESC LIMIT 10")
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"   Top duplicate model codes:")
            for code, count in duplicates:
                print(f"     {code}: {count} entries")
        
        # 4. Price validation
        print(f"\n4. PRICE VALIDATION:")
        cursor.execute("SELECT MIN(price), MAX(price), AVG(price), COUNT(CASE WHEN price <= 0 THEN 1 END) FROM price_entries")
        min_price, max_price, avg_price, invalid_prices = cursor.fetchone()
        print(f"   Price range: {min_price}€ - {max_price}€")
        print(f"   Average price: {avg_price:.0f}€")
        print(f"   Invalid prices (<=0): {invalid_prices}")
        
        # 5. Brand-specific analysis
        print(f"\n5. BRAND-SPECIFIC ANALYSIS:")
        
        for brand in ['LYNX', 'SKI-DOO']:
            print(f"   {brand}:")
            
            # Most common models for this brand
            cursor.execute("""
                SELECT malli, COUNT(*) as count 
                FROM price_entries 
                WHERE brand = ? AND malli IS NOT NULL 
                GROUP BY malli 
                ORDER BY count DESC 
                LIMIT 5
            """, (brand,))
            
            models = cursor.fetchall()
            if models:
                print(f"     Top models:")
                for model, count in models:
                    print(f"       {model}: {count} entries")
            
            # Price range by brand
            cursor.execute("SELECT MIN(price), MAX(price), AVG(price) FROM price_entries WHERE brand = ?", (brand,))
            brand_min, brand_max, brand_avg = cursor.fetchone()
            print(f"     Price range: {brand_min}€ - {brand_max}€ (avg: {brand_avg:.0f}€)")
        
        # 6. Sample quality check
        print(f"\n6. SAMPLE QUALITY CHECK:")
        print("   Best quality entries (with all fields):")
        cursor.execute("""
            SELECT brand, model_year, model_code, malli, paketti, moottori, vari, price 
            FROM price_entries 
            WHERE malli IS NOT NULL AND paketti IS NOT NULL AND moottori IS NOT NULL 
            ORDER BY RANDOM() 
            LIMIT 5
        """)
        
        for entry in cursor.fetchall():
            brand, year, code, malli, paketti, moottori, vari, price = entry
            print(f"     {brand} {year} | {code}: {malli} + {paketti} ({moottori}) - {price}€")
        
        print(f"\n   Minimal entries (only model code + price):")
        cursor.execute("""
            SELECT brand, model_year, model_code, malli, paketti, price 
            FROM price_entries 
            WHERE (malli IS NULL OR malli = '') AND (paketti IS NULL OR paketti = '')
            ORDER BY RANDOM() 
            LIMIT 5
        """)
        
        for entry in cursor.fetchall():
            brand, year, code, malli, paketti, price = entry
            print(f"     {brand} {year} | {code}: {malli or 'None'} + {paketti or 'None'} - {price}€")
        
        # 7. Readiness for matching
        print(f"\n7. MATCHING READINESS ASSESSMENT:")
        
        # Count entries suitable for each matching tier
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN malli IS NOT NULL AND malli != '' THEN 1 END) as tier1_ready,
                COUNT(CASE WHEN normalized_model_name IS NOT NULL AND normalized_model_name != '' THEN 1 END) as tier2_ready,
                COUNT(CASE WHEN (malli IS NOT NULL AND malli != '') OR (normalized_model_name IS NOT NULL AND normalized_model_name != '') THEN 1 END) as bert_ready
            FROM price_entries
        """)
        
        total, tier1, tier2, bert = cursor.fetchone()
        
        print(f"   Tier 1 (Exact matching) ready: {tier1}/{total} ({tier1/total*100:.1f}%)")
        print(f"   Tier 2 (BERT semantic) ready: {bert}/{total} ({bert/total*100:.1f}%)")
        print(f"   Overall matching readiness: {bert}/{total} ({bert/total*100:.1f}%)")
        
        # 8. Final assessment
        print(f"\n8. FINAL ASSESSMENT:")
        
        if bert/total >= 0.8:
            print("   [EXCELLENT] 80%+ entries ready for BERT matching")
        elif bert/total >= 0.6:
            print("   [GOOD] 60%+ entries ready for matching")
        elif bert/total >= 0.4:
            print("   [FAIR] 40%+ entries ready for matching - improvement needed")
        else:
            print("   [POOR] <40% entries ready - significant extraction issues")
        
        if unique_codes == total:
            print("   [EXCELLENT] All model codes are unique")
        elif unique_codes/total >= 0.95:
            print("   [GOOD] 95%+ unique model codes")
        else:
            print("   [WARNING] Significant duplicate model codes detected")
        
        if invalid_prices == 0:
            print("   [EXCELLENT] All prices valid")
        else:
            print(f"   [WARNING] {invalid_prices} invalid price entries")
        
        conn.close()
        
        return {
            'total_entries': total,
            'matching_ready_percent': bert/total*100,
            'unique_code_percent': unique_codes/total*100,
            'data_quality_score': (bert/total + unique_codes/total) / 2 * 100
        }

if __name__ == "__main__":
    validator = DataValidator()
    results = validator.validate_all_data()