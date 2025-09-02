#!/usr/bin/env python3
"""
Generate Avito XML from Snowmobile Database
Uses real product data from the database to generate Avito-format XML
"""
import sqlite3
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal

class AvitoXMLGenerator:
    """Generate Avito XML from snowmobile database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.timestamp = datetime.now()
        
    def get_product_data(self) -> List[Dict[str, Any]]:
        """Get product data from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all products with price information
        query = """
        SELECT 
            p.*,
            pe.price_amount,
            pe.currency,
            pe.malli,
            pe.paketti,
            pe.moottori,
            pe.telamatto,
            pe.kaynnistin,
            pe.mittaristo,
            pe.vari,
            pl.brand as price_brand,
            pl.market
        FROM products p
        LEFT JOIN price_entries pe ON p.sku LIKE '%' || pe.model_code || '%'
        LEFT JOIN price_lists pl ON pe.price_list_id = pl.id
        WHERE p.sku IS NOT NULL
        ORDER BY p.created_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        products = []
        for row in rows:
            product_dict = dict(zip(columns, row))
            
            # Parse JSON fields if they exist
            if product_dict.get('full_specifications'):
                try:
                    product_dict['full_specifications_parsed'] = json.loads(product_dict['full_specifications'])
                except:
                    product_dict['full_specifications_parsed'] = {}
            
            products.append(product_dict)
        
        conn.close()
        return products
    
    def convert_currency(self, price: float, from_currency: str = "EUR") -> int:
        """Convert price to rubles (Avito requirement)"""
        if not price:
            return 0
            
        # EUR to RUB conversion (approximate rate)
        if from_currency.upper() == "EUR":
            return int(price * 100)  # 1 EUR ≈ 100 RUB (approximate)
        elif from_currency.upper() == "RUB":
            return int(price)
        else:
            return int(price * 100)  # Default conversion
    
    def clean_text(self, text: str) -> str:
        """Clean text for XML output"""
        if not text:
            return ""
        
        # Remove None, NaN, null values
        if str(text).lower() in ['none', 'nan', 'null', '']:
            return ""
        
        # Clean up text
        cleaned = str(text).strip()
        
        # Replace XML special characters
        cleaned = cleaned.replace('&', '&amp;')
        cleaned = cleaned.replace('<', '&lt;')
        cleaned = cleaned.replace('>', '&gt;')
        cleaned = cleaned.replace('"', '&quot;')
        cleaned = cleaned.replace("'", '&apos;')
        
        return cleaned
    
    def generate_title(self, product: Dict[str, Any]) -> str:
        """Generate attractive title for Avito listing"""
        parts = []
        
        # Brand
        brand = product.get('price_brand') or 'Ski-Doo'
        parts.append(brand)
        
        # Model name
        model_name = product.get('model_family') or product.get('malli')
        if model_name:
            parts.append(model_name)
        
        # Model code
        if product.get('sku'):
            parts.append(f"({product['sku']})")
        
        # Year
        if product.get('model_year'):
            parts.append(f"{product['model_year']}")
        
        # Package
        if product.get('paketti'):
            parts.append(product['paketti'])
        
        return ' '.join(parts)
    
    def generate_description(self, product: Dict[str, Any]) -> str:
        """Generate detailed description for Avito listing"""
        description_parts = []
        
        # Model information
        model_info = f"Модель: {product.get('model_family', 'Неизвестно')}"
        description_parts.append(model_info)
        
        # Engine info
        if product.get('moottori'):
            description_parts.append(f"Двигатель: {product['moottori']}")
        
        # Track info
        if product.get('telamatto'):
            description_parts.append(f"Гусеница: {product['telamatto']}")
        
        # Starter
        if product.get('kaynnistin'):
            description_parts.append(f"Запуск: {product['kaynnistin']}")
        
        # Display
        if product.get('mittaristo'):
            description_parts.append(f"Приборы: {product['mittaristo']}")
        
        # Color
        if product.get('vari'):
            description_parts.append(f"Цвет: {product['vari']}")
        
        # Full specifications from Claude if available
        full_specs = product.get('full_specifications_parsed', {})
        if full_specs:
            enriched = full_specs.get('enriched', {})
            if enriched.get('market_positioning'):
                description_parts.append(f"\nОписание: {enriched['market_positioning']}")
            
            # Add engine specs
            engine_specs = enriched.get('specifications', {}).get('engine', {})
            if engine_specs:
                if engine_specs.get('displacement'):
                    description_parts.append(f"Объем двигателя: {engine_specs['displacement']} куб.см")
                if engine_specs.get('power_hp'):
                    description_parts.append(f"Мощность: {engine_specs['power_hp']} л.с.")
        
        # Add standard features
        description_parts.append("\n✅ Официальная гарантия")
        description_parts.append("✅ Доставка по России")
        description_parts.append("✅ Сертифицированный дилер BRP")
        
        return "\n".join(description_parts)
    
    def generate_xml_for_product(self, product: Dict[str, Any]) -> ET.Element:
        """Generate XML element for a single product"""
        ad = ET.Element("Ad")
        
        # Required fields
        ad_id = ET.SubElement(ad, "Id")
        ad_id.text = str(product.get('id') or product.get('sku', 'unknown'))
        
        # Title
        title = ET.SubElement(ad, "Title")
        title.text = self.clean_text(self.generate_title(product))
        
        # Description
        description = ET.SubElement(ad, "Description")
        description.text = self.clean_text(self.generate_description(product))
        
        # Price
        price = ET.SubElement(ad, "Price")
        price_amount = product.get('price_amount', 0) or 0
        currency = product.get('currency', 'EUR')
        price_rub = self.convert_currency(price_amount, currency)
        price.text = str(price_rub) if price_rub > 0 else "0"
        
        # Category
        category = ET.SubElement(ad, "Category")
        category.text = "Мотоциклы и мототехника"
        
        # Vehicle type  
        vehicle_type = ET.SubElement(ad, "VehicleType")
        vehicle_type.text = "Снегоходы"
        
        # Address (location)
        address = ET.SubElement(ad, "Address")
        address.text = "Санкт-Петербург"
        
        # Make (manufacturer)
        make = ET.SubElement(ad, "Make")
        make.text = "BRP"
        
        # Model
        model = ET.SubElement(ad, "Model")
        model_name = product.get('model_family') or product.get('malli', 'Неизвестная модель')
        model.text = self.clean_text(model_name)
        
        # Year
        if product.get('model_year'):
            year = ET.SubElement(ad, "Year")
            year.text = str(product['model_year'])
        
        # Engine displacement (if available)
        full_specs = product.get('full_specifications_parsed', {})
        engine_specs = full_specs.get('enriched', {}).get('specifications', {}).get('engine', {})
        if engine_specs.get('displacement'):
            engine_displacement = ET.SubElement(ad, "EngineDisplacement")
            engine_displacement.text = str(engine_specs['displacement'])
        
        # Contact info
        contact_phone = ET.SubElement(ad, "ContactPhone")
        contact_phone.text = "+7 (812) 123-45-67"  # Placeholder
        
        # Images (placeholder - would need actual image URLs)
        images = ET.SubElement(ad, "Images")
        image1 = ET.SubElement(images, "Image")
        image1.set("url", f"https://example.com/snowmobile-{product.get('sku', 'default')}.jpg")
        
        return ad
    
    def generate_avito_xml(self, output_path: str = None) -> str:
        """Generate complete Avito XML file"""
        products = self.get_product_data()
        
        if not products:
            raise ValueError("No products found in database")
        
        print(f"Found {len(products)} products in database")
        
        # Create root XML element
        root = ET.Element("Ads")
        root.set("formatVersion", "3")
        root.set("target", "Avito.ru")
        
        # Process each product
        valid_products = 0
        for product in products:
            try:
                ad_element = self.generate_xml_for_product(product)
                root.append(ad_element)
                valid_products += 1
                print(f"Added product: {product.get('sku')} - {product.get('model_family')}")
            except Exception as e:
                print(f"Error processing product {product.get('sku', 'unknown')}: {e}")
        
        print(f"Generated XML for {valid_products} valid products")
        
        # Create XML tree
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)  # Pretty print
        
        # Set output path
        if not output_path:
            timestamp_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
            output_path = f"results/avito_snowmobiles_{timestamp_str}.xml"
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write XML file
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        print(f"Avito XML generated: {output_path}")
        print(f"File contains {valid_products} snowmobile listings")
        
        return output_path


def main():
    """Generate Avito XML from database"""
    print("="*60)
    print("AVITO XML GENERATOR")
    print("="*60)
    
    db_path = "snowmobile_reconciliation.db"
    
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return
    
    try:
        generator = AvitoXMLGenerator(db_path)
        xml_file = generator.generate_avito_xml()
        
        print(f"\n✅ SUCCESS!")
        print(f"   Avito XML file: {xml_file}")
        print(f"   File size: {Path(xml_file).stat().st_size:,} bytes")
        
        # Show first few lines of generated XML
        print(f"\n📄 Preview of generated XML:")
        print("-" * 40)
        with open(xml_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i < 20:  # Show first 20 lines
                    print(line.rstrip())
                else:
                    print("...")
                    break
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()