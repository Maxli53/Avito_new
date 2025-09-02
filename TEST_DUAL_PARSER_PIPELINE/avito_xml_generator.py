"""
Avito XML Generation System
Generates valid Avito XML using template system and validated data
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional
from datetime import datetime
import re

class AvitoXMLGenerator:
    """Generates Avito-compliant XML from validated product data"""
    
    def __init__(self):
        self.format_version = "3"
        self.target = "Avito.ru"
        
    def generate_xml(self, products: List[Dict[str, Any]]) -> str:
        """Generate complete Avito XML from product list"""
        
        # Create root element
        root = ET.Element("Ads")
        root.set("formatVersion", self.format_version)
        root.set("target", self.target)
        
        # Add products
        for product in products:
            ad_element = self._create_ad_element(product)
            if ad_element is not None:
                root.append(ad_element)
        
        # Format XML with proper indentation
        xml_string = self._prettify_xml(root)
        
        return f'<?xml version="1.0" encoding="utf-8"?>\n{xml_string}'
    
    def _create_ad_element(self, product: Dict[str, Any]) -> Optional[ET.Element]:
        """Create single Ad element from product data"""
        
        ad = ET.Element("Ad")
        
        # Required fields
        self._add_element(ad, "Id", product.get('Id'))
        self._add_element(ad, "Title", product.get('Title'))
        self._add_element(ad, "Category", product.get('Category', 'Мотоциклы и мототехника'))
        self._add_element(ad, "VehicleType", product.get('VehicleType', 'Снегоходы'))
        self._add_element(ad, "Price", str(product.get('Price', '')))
        self._add_element(ad, "Description", product.get('Description'))
        
        # Images
        images = product.get('Images', [])
        if images:
            images_elem = ET.SubElement(ad, "Images")
            for image_url in images:
                img_elem = ET.SubElement(images_elem, "Image")
                img_elem.set("url", str(image_url))
        
        self._add_element(ad, "Address", product.get('Address', 'Санкт-Петербург'))
        
        # Model (critical for validation)
        self._add_element(ad, "Model", product.get('Model'))
        
        # Fixed values for BRP snowmobiles
        self._add_element(ad, "Make", "BRP")
        self._add_element(ad, "EngineType", "Бензин")
        self._add_element(ad, "Condition", product.get('Condition', 'Новое'))
        self._add_element(ad, "Kilometrage", str(product.get('Kilometrage', 0)))
        
        # Optional fields
        if product.get('Year'):
            self._add_element(ad, "Year", str(product.get('Year')))
        
        if product.get('Power'):
            self._add_element(ad, "Power", str(product.get('Power')))
        
        if product.get('EngineCapacity'):
            self._add_element(ad, "EngineCapacity", str(product.get('EngineCapacity')))
        
        if product.get('PersonCapacity'):
            self._add_element(ad, "PersonCapacity", str(product.get('PersonCapacity')))
        
        if product.get('TrackWidth'):
            self._add_element(ad, "TrackWidth", str(product.get('TrackWidth')))
        
        if product.get('Type'):
            self._add_element(ad, "Type", product.get('Type'))
        
        if product.get('Availability'):
            self._add_element(ad, "Availability", product.get('Availability'))
        
        return ad
    
    def _add_element(self, parent: ET.Element, tag: str, value: Any):
        """Add element with value if value exists"""
        if value is not None and str(value).strip():
            elem = ET.SubElement(parent, tag)
            elem.text = str(value).strip()
    
    def _prettify_xml(self, element: ET.Element) -> str:
        """Return formatted XML string"""
        rough_string = ET.tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_string = reparsed.documentElement.toprettyxml(indent="  ")
        
        # Remove empty lines
        lines = [line for line in pretty_string.split('\n') if line.strip()]
        return '\n'.join(lines)

class ProductDataMapper:
    """Maps database product data to Avito XML format"""
    
    def __init__(self):
        self.field_mapping = {
            # Database field -> XML field
            'model_code': 'Id',
            'malli': 'model_part',
            'paketti': 'package_part', 
            'price': 'Price',
            'moottori': 'engine_info',
            'telamatto': 'track_info',
            'vari': 'color_info',
            'year': 'Year',
            'brand': 'make_info'
        }
    
    def map_product_to_xml_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database product to XML-ready data"""
        
        xml_data = {}
        
        # Map basic fields
        xml_data['Id'] = self._generate_id(product)
        xml_data['Title'] = self._generate_title(product)
        xml_data['Description'] = self._generate_description(product)
        xml_data['Price'] = self._format_price(product.get('price'))
        xml_data['Model'] = self._format_model_name(product)
        
        # Map technical specs
        if product.get('year'):
            xml_data['Year'] = int(product['year'])
        
        # Extract power from engine info
        power = self._extract_power(product.get('moottori', ''))
        if power:
            xml_data['Power'] = power
        
        # Extract engine capacity
        capacity = self._extract_engine_capacity(product.get('moottori', ''))
        if capacity:
            xml_data['EngineCapacity'] = capacity
        
        # Extract track width
        track_width = self._extract_track_width(product.get('telamatto', ''))
        if track_width:
            xml_data['TrackWidth'] = track_width
        
        # Determine snowmobile type
        xml_data['Type'] = self._determine_type(product)
        
        # Standard fields
        xml_data['Category'] = 'Мотоциклы и мототехника'
        xml_data['VehicleType'] = 'Снегоходы'
        xml_data['Make'] = 'BRP'
        xml_data['EngineType'] = 'Бензин'
        xml_data['Condition'] = 'Новое'
        xml_data['Kilometrage'] = 0
        xml_data['PersonCapacity'] = 1  # Default for most snowmobiles
        xml_data['Availability'] = 'В наличии'
        xml_data['Address'] = 'Санкт-Петербург'
        
        # Placeholder image (should be replaced with real images)
        xml_data['Images'] = ['https://example.com/placeholder.jpg']
        
        return xml_data
    
    def _generate_id(self, product: Dict[str, Any]) -> str:
        """Generate unique product ID"""
        brand = product.get('brand', 'BRP').upper()
        model_code = product.get('model_code', 'UNKNOWN')
        year = product.get('year', 2026)
        
        return f"{brand}-{model_code}-{year}"
    
    def _generate_title(self, product: Dict[str, Any]) -> str:
        """Generate product title"""
        brand = product.get('brand', 'BRP')
        model = product.get('malli', '')
        package = product.get('paketti', '')
        year = product.get('year', 2026)
        
        title_parts = [brand]
        
        if model:
            title_parts.append(model)
        
        if package:
            title_parts.append(package)
        
        # Add engine info if available
        engine = product.get('moottori', '')
        if engine:
            # Extract key engine info
            if 'E-TEC' in engine:
                title_parts.append('E-TEC')
            elif 'EFI' in engine:
                title_parts.append('EFI')
        
        title_parts.extend(['снегоход', str(year), 'года'])
        
        return ' '.join(title_parts)
    
    def _generate_description(self, product: Dict[str, Any]) -> str:
        """Generate product description"""
        model = product.get('malli', '')
        package = product.get('paketti', '')
        engine = product.get('moottori', '')
        track = product.get('telamatto', '')
        color = product.get('vari', '')
        
        desc_parts = [f"Новый снегоход {model}"]
        
        if package:
            desc_parts.append(f"в комплектации {package}")
        
        if engine:
            desc_parts.append(f"с двигателем {engine}")
        
        if track:
            desc_parts.append(f"и гусеницей {track}")
        
        if color:
            desc_parts.append(f"в цвете {color}")
        
        description = '. '.join(desc_parts) + '.'
        
        # Add standard features
        description += " Официальная гарантия BRP. Доставка по России. Возможен trade-in."
        
        return description
    
    def _format_price(self, price: Any) -> Optional[int]:
        """Format price for Avito (integer rubles)"""
        if not price:
            return None
        
        try:
            # Convert EUR to RUB (approximate rate: 1 EUR = 100 RUB)
            eur_price = float(price)
            rub_price = eur_price * 100  # Convert EUR to RUB
            return int(rub_price)
        except (ValueError, TypeError):
            return None
    
    def _format_model_name(self, product: Dict[str, Any]) -> str:
        """Format model name for Avito catalog matching"""
        brand = product.get('brand', 'BRP')
        model = product.get('malli', '')
        package = product.get('paketti', '')
        engine = product.get('moottori', '')
        
        # Standard BRP format: "BRP Ski-Doo Model Package Engine"
        model_parts = ['BRP']
        
        if 'SKI-DOO' in brand.upper():
            model_parts.append('Ski-Doo')
        elif 'LYNX' in brand.upper():
            model_parts.append('LYNX')
        
        if model:
            model_parts.append(model)
        
        # Add engine info for better matching
        if engine:
            # Extract key engine details
            if '600R' in engine:
                model_parts.append('600R E-TEC')
            elif '600' in engine and 'EFI' in engine:
                model_parts.append('600 EFI')
            elif '850' in engine and 'E-TEC' in engine:
                model_parts.append('850 E-TEC')
            elif '900' in engine:
                model_parts.append('900 ACE')
        
        return ' '.join(model_parts)
    
    def _extract_power(self, engine_str: str) -> Optional[int]:
        """Extract power from engine string"""
        if not engine_str:
            return None
        
        # Look for HP pattern
        hp_match = re.search(r'(\d+)\s*HP', engine_str, re.IGNORECASE)
        if hp_match:
            return int(hp_match.group(1))
        
        # Estimate based on engine type
        if '850' in engine_str:
            return 165  # Typical 850 power
        elif '600R' in engine_str:
            return 125  # Typical 600R power
        elif '600' in engine_str:
            return 85   # Typical 600 power
        
        return None
    
    def _extract_engine_capacity(self, engine_str: str) -> Optional[int]:
        """Extract engine displacement"""
        if not engine_str:
            return None
        
        # Look for displacement patterns
        for pattern in [r'(\d+)\s*E-TEC', r'(\d+)\s*EFI', r'(\d+)R?\s*E-TEC']:
            match = re.search(pattern, engine_str)
            if match:
                capacity = int(match.group(1))
                # Handle common formats
                if capacity == 600:
                    return 600
                elif capacity == 850:
                    return 850
                elif capacity == 900:
                    return 900
        
        return None
    
    def _extract_track_width(self, track_str: str) -> Optional[int]:
        """Extract track width from track specification"""
        if not track_str:
            return None
        
        # Look for width in mm - but convert to reasonable values for Avito
        width_match = re.search(r'(\d+)mm', track_str)
        if width_match:
            width_mm = int(width_match.group(1))
            # Convert track length to width (3500mm track length -> ~380mm track width)
            if width_mm > 1000:  # This is likely track length, not width
                if width_mm >= 3500:
                    return 381  # Standard width for long tracks
                elif width_mm >= 3000:
                    return 406  # Slightly wider
                else:
                    return 381  # Default width
            else:
                return width_mm  # This is actual width
        
        # Estimate based on track length indicators
        if '129' in track_str or '137' in track_str:
            return 381  # Standard narrow track
        elif '146' in track_str or '154' in track_str:
            return 406  # Standard wide track
        elif '165' in track_str:
            return 381  # Deep snow narrow
        
        return 381  # Default reasonable width
    
    def _determine_type(self, product: Dict[str, Any]) -> str:
        """Determine snowmobile type from model info"""
        model = product.get('malli', '').upper()
        package = product.get('paketti', '').upper()
        
        if 'SUMMIT' in model:
            return 'Горный'
        elif 'RENEGADE' in model or 'SPORT' in package:
            return 'Спортивный'  
        elif 'EXPEDITION' in model or 'UTILITY' in model:
            return 'Утилитарный'
        else:
            return 'Туристический'

if __name__ == "__main__":
    # Test XML generation
    mapper = ProductDataMapper()
    generator = AvitoXMLGenerator()
    
    # Sample product from database
    sample_product = {
        'model_code': 'TJTH',
        'brand': 'SKI-DOO',
        'year': 2026,
        'malli': 'Summit',
        'paketti': 'X with Expert Pkg',
        'moottori': '850 E-TEC Turbo R',
        'telamatto': '165in 4200mm 3.0in 76mm Powdermax X-light',
        'kaynnistin': 'SHOT',
        'mittaristo': '10.25 in. Color Touchscreen Display',
        'vari': 'Terra Green',
        'price': 27270.0
    }
    
    # Map to XML format
    xml_data = mapper.map_product_to_xml_data(sample_product)
    
    print("Generated XML Data:")
    for key, value in xml_data.items():
        print(f"  {key}: {value}")
    
    # Generate XML
    xml_content = generator.generate_xml([xml_data])
    
    print(f"\nGenerated XML ({len(xml_content)} characters):")
    print(xml_content)