"""
Complete Avito Pipeline - End-to-End Implementation
Connects smart extraction -> matching -> validation -> XML generation -> upload
"""

import sqlite3
import json
import ftplib
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Import our pipeline components
from smart_price_extractor import SmartPriceExtractor
from avito_validation_system import AvitoValidationPipeline
from avito_xml_generator import AvitoXMLGenerator, ProductDataMapper

class AvitoFTPUploader:
    """Handles FTP upload to Avito server"""
    
    def __init__(self):
        self.host = "176.126.165.67"
        self.username = "user133859"
        self.password = os.getenv("AVITO_FTP_PASSWORD", "your_ftp_password")
        self.remote_path = "/test_corrected_profile.xml"
    
    def upload_xml(self, xml_content: str, filename: str = None) -> bool:
        """Upload XML content to Avito FTP server"""
        
        if not filename:
            filename = f"snowmobile_catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
        try:
            print(f"Connecting to Avito FTP server: {self.host}")
            
            with ftplib.FTP(self.host) as ftp:
                ftp.login(self.username, self.password)
                print("FTP connection established")
                
                # Upload XML content
                from io import BytesIO
                xml_bytes = xml_content.encode('utf-8')
                xml_buffer = BytesIO(xml_bytes)
                
                ftp.storbinary(f'STOR {self.remote_path}', xml_buffer)
                print(f"XML uploaded successfully: {self.remote_path}")
                
                # Verify upload
                file_list = ftp.nlst()
                if self.remote_path.lstrip('/') in file_list:
                    print("Upload verified on server")
                    return True
                else:
                    print("Upload verification failed")
                    return False
                    
        except Exception as e:
            print(f"FTP upload failed: {e}")
            return False

class ProcessingMonitor:
    """Monitors Avito processing windows and results"""
    
    def __init__(self):
        self.processing_times = ["03:00", "11:00", "19:00"]  # MSK
        
    def get_next_processing_window(self) -> str:
        """Get next Avito processing time"""
        current_hour = datetime.now().hour
        
        for time_str in self.processing_times:
            hour = int(time_str.split(':')[0])
            if current_hour < hour:
                return time_str
        
        # Next day first window
        return self.processing_times[0] + " (next day)"
    
    def wait_for_processing(self):
        """Information about processing wait times"""
        next_window = self.get_next_processing_window()
        print(f"Next Avito processing window: {next_window} MSK")
        print("Processing typically takes 30-60 minutes after the window starts")

class CompletePipelineStats:
    """Track pipeline statistics and performance"""
    
    def __init__(self):
        self.stats = {
            'extraction': {'total': 0, 'success': 0, 'failed': 0},
            'matching': {'total': 0, 'success': 0, 'failed': 0},
            'validation': {'total': 0, 'passed': 0, 'failed': 0},
            'xml_generation': {'total': 0, 'success': 0, 'failed': 0},
            'upload': {'total': 0, 'success': 0, 'failed': 0},
            'start_time': datetime.now(),
            'processing_time': 0
        }
    
    def record_extraction(self, success: bool, count: int = 1):
        self.stats['extraction']['total'] += count
        if success:
            self.stats['extraction']['success'] += count
        else:
            self.stats['extraction']['failed'] += count
    
    def record_validation(self, passed: bool):
        self.stats['validation']['total'] += 1
        if passed:
            self.stats['validation']['passed'] += 1
        else:
            self.stats['validation']['failed'] += 1
    
    def record_xml_generation(self, success: bool):
        self.stats['xml_generation']['total'] += 1
        if success:
            self.stats['xml_generation']['success'] += 1
        else:
            self.stats['xml_generation']['failed'] += 1
    
    def record_upload(self, success: bool):
        self.stats['upload']['total'] += 1
        if success:
            self.stats['upload']['success'] += 1
        else:
            self.stats['upload']['failed'] += 1
    
    def finalize(self):
        self.stats['processing_time'] = (datetime.now() - self.stats['start_time']).total_seconds()
    
    def print_summary(self):
        print("\n" + "="*60)
        print("COMPLETE PIPELINE STATISTICS")
        print("="*60)
        
        for stage, data in self.stats.items():
            if stage in ['start_time', 'processing_time']:
                continue
                
            total = data['total']
            success = data.get('success', data.get('passed', 0))
            failed = data.get('failed', 0)
            
            if total > 0:
                success_rate = (success / total) * 100
                print(f"{stage.upper()}:")
                print(f"  Total: {total}")
                print(f"  Success: {success} ({success_rate:.1f}%)")
                print(f"  Failed: {failed}")
        
        print(f"\nTOTAL PROCESSING TIME: {self.stats['processing_time']:.1f} seconds")
        print("="*60)

class CompletePipeline:
    """Complete end-to-end Avito pipeline"""
    
    def __init__(self, db_path: str = "snowmobile_reconciliation.db"):
        self.db_path = db_path
        
        # Initialize components
        print("Initializing complete Avito pipeline...")
        self.extractor = SmartPriceExtractor(db_path=db_path)
        self.validator = AvitoValidationPipeline()
        self.mapper = ProductDataMapper()
        self.xml_generator = AvitoXMLGenerator()
        self.uploader = AvitoFTPUploader()
        self.monitor = ProcessingMonitor()
        self.stats = CompletePipelineStats()
        
        print("Pipeline initialization complete")
    
    def run_complete_pipeline(self, extract_data: bool = True, upload_xml: bool = False) -> Dict[str, Any]:
        """Run the complete pipeline end-to-end"""
        
        print("\n" + "="*60)
        print("STARTING COMPLETE AVITO PIPELINE")
        print("="*60)
        
        try:
            # Step 1: Data Extraction (if requested)
            if extract_data:
                print("\n1. EXTRACTING PRICE LIST DATA...")
                extraction_result = self.extractor.extract_all_price_lists()
                self.stats.record_extraction(
                    success=extraction_result['total_articles'] > 0,
                    count=extraction_result['total_articles']
                )
            else:
                print("\n1. SKIPPING EXTRACTION - Using existing database data")
            
            # Step 2: Load Products from Database
            print("\n2. LOADING PRODUCTS FROM DATABASE...")
            products = self._load_products_from_database()
            print(f"Loaded {len(products)} products from database")
            
            if not products:
                print("No products found in database. Run with extract_data=True first.")
                return {'success': False, 'error': 'No products available'}
            
            # Step 3: Validation & XML Generation
            print(f"\n3. VALIDATING AND GENERATING XML FOR {len(products)} PRODUCTS...")
            validated_products = []
            xml_products = []
            
            for i, product in enumerate(products, 1):
                print(f"Processing product {i}/{len(products)}: {product.get('model_code', 'UNKNOWN')}")
                
                # Map to XML format
                xml_data = self.mapper.map_product_to_xml_data(product)
                
                # Validate
                validation_result = self.validator.validate_xml_ready_data(xml_data)
                self.stats.record_validation(validation_result.success)
                
                if validation_result.success:
                    validated_products.append(product)
                    xml_products.append(xml_data)
                    self.stats.record_xml_generation(True)
                else:
                    print(f"  FAILED VALIDATION: {product.get('model_code')}")
                    for error in validation_result.errors:
                        print(f"    ERROR: {error}")
                    self.stats.record_xml_generation(False)
            
            print(f"\nValidated {len(validated_products)} out of {len(products)} products")
            
            # Step 4: Generate Final XML
            if xml_products:
                print("\n4. GENERATING FINAL XML...")
                final_xml = self.xml_generator.generate_xml(xml_products)
                print(f"Generated XML with {len(xml_products)} products ({len(final_xml)} characters)")
                
                # Save XML to file
                xml_filename = f"avito_snowmobiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                xml_path = Path(xml_filename)
                
                with open(xml_path, 'w', encoding='utf-8') as f:
                    f.write(final_xml)
                
                print(f"XML saved to: {xml_path.absolute()}")
                
                # Step 5: Upload (if requested)
                if upload_xml:
                    print("\n5. UPLOADING TO AVITO FTP...")
                    upload_success = self.uploader.upload_xml(final_xml, xml_filename)
                    self.stats.record_upload(upload_success)
                    
                    if upload_success:
                        print("Upload successful!")
                        self.monitor.wait_for_processing()
                    else:
                        print("Upload failed!")
                else:
                    print("\n5. SKIPPING UPLOAD - Set upload_xml=True to upload")
                
                # Finalize and show stats
                self.stats.finalize()
                self.stats.print_summary()
                
                return {
                    'success': True,
                    'products_processed': len(products),
                    'products_validated': len(validated_products),
                    'xml_generated': True,
                    'xml_file': str(xml_path.absolute()),
                    'xml_size': len(final_xml),
                    'uploaded': upload_xml and upload_success if upload_xml else False,
                    'stats': self.stats.stats
                }
            else:
                print("\nNo valid products found - cannot generate XML")
                return {'success': False, 'error': 'No valid products'}
                
        except Exception as e:
            print(f"\nPIPELINE ERROR: {e}")
            return {'success': False, 'error': str(e)}
    
    def _load_products_from_database(self) -> List[Dict[str, Any]]:
        """Load product data from database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get products with smart extractor data
        cursor.execute("""
            SELECT model_code, brand, model_year, malli, paketti, moottori, telamatto,
                   kaynnistin, mittaristo, vari, price, extraction_method
            FROM price_entries 
            WHERE extraction_method = 'smart_extractor'
            ORDER BY brand, model_year, malli, paketti
        """)
        
        products = []
        for row in cursor.fetchall():
            product = {
                'model_code': row[0],
                'brand': row[1],
                'year': row[2],
                'malli': row[3],
                'paketti': row[4],
                'moottori': row[5],
                'telamatto': row[6],
                'kaynnistin': row[7],
                'mittaristo': row[8],
                'vari': row[9],
                'price': row[10],
                'extraction_method': row[11]
            }
            products.append(product)
        
        conn.close()
        return products
    
    def validate_single_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single product and show detailed results"""
        
        print(f"Validating product: {product_data.get('model_code', 'UNKNOWN')}")
        
        # Map to XML format
        xml_data = self.mapper.map_product_to_xml_data(product_data)
        
        # Validate
        result = self.validator.validate_xml_ready_data(xml_data)
        
        return {
            'product': product_data,
            'xml_data': xml_data,
            'validation': {
                'success': result.success,
                'errors': result.errors,
                'warnings': result.warnings,
                'suggestions': result.suggestions
            }
        }

def main():
    """Main pipeline execution"""
    
    # Initialize pipeline
    pipeline = CompletePipeline()
    
    # Run with options
    result = pipeline.run_complete_pipeline(
        extract_data=False,  # Use existing database data
        upload_xml=False     # Set to True when ready to upload
    )
    
    if result['success']:
        print(f"\n🎉 PIPELINE SUCCESS!")
        print(f"Generated XML file: {result['xml_file']}")
        print(f"Products processed: {result['products_processed']}")
        print(f"Products validated: {result['products_validated']}")
    else:
        print(f"\n❌ PIPELINE FAILED: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()