#!/usr/bin/env python3
"""
Snowmobile Specification Sheet Generator
Generates professional PDF snowmobile spec sheets using ReportLab
with enterprise database integration and Ski-Doo branding.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    KeepTogether
)
from reportlab.pdfgen.canvas import Canvas


@dataclass
class BrandConfig:
    """Configuration for Ski-Doo brand styling"""
    name: str
    primary_color: str  # Hex color
    secondary_color: str
    accent_color: str
    font_family: str = "Helvetica"
    title_font_size: int = 28
    subtitle_font_size: int = 14
    section_header_font_size: int = 16
    footer_disclaimer: str = ""


class SkiDooBrandConfig:
    """Ski-Doo brand configuration"""
    
    SKIDOO = BrandConfig(
        name="Ski-Doo",
        primary_color="#FFD700",  # Ski-Doo yellow
        secondary_color="#333333",
        accent_color="#F5F5F5",
        title_font_size=28,
        footer_disclaimer="Ski-Doo reserves the right to modify specifications without notice."
    )


class SnowmobileSpecGenerator:
    """Professional snowmobile specification PDF generator"""
    
    def __init__(self, db_path: str, brand_config: BrandConfig = None):
        self.db_path = db_path
        self.brand_config = brand_config or SkiDooBrandConfig.SKIDOO
        self.setup_styles()
        
    def setup_styles(self):
        """Define brand-specific styles for the document"""
        self.styles = getSampleStyleSheet()
        config = self.brand_config
        
        # Vehicle title style
        self.styles.add(ParagraphStyle(
            name='SnowmobileTitle',
            parent=self.styles['Heading1'],
            fontSize=config.title_font_size,
            textColor=colors.HexColor(config.primary_color),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=8,
            alignment=TA_LEFT
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='SnowmobileSubtitle',
            parent=self.styles['Normal'],
            fontSize=config.subtitle_font_size,
            textColor=colors.black,
            fontName=config.font_family,
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=config.section_header_font_size,
            textColor=colors.HexColor(config.primary_color),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=8,
            spaceBefore=16,
            alignment=TA_LEFT
        ))
        
        # Price style
        self.styles.add(ParagraphStyle(
            name='PriceStyle',
            parent=self.styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor("#27ae60"),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=12,
            alignment=TA_LEFT
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName=config.font_family,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))

    def get_snowmobile_data(self, model_code: str) -> Dict[str, Any]:
        """Retrieve snowmobile data from enterprise database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get price entry data with Finnish fields (primary data source)
            price_entry_query = """
            SELECT pe.*, pl.filename as price_list_filename, pl.market, pl.brand as pl_brand
            FROM price_entries pe
            LEFT JOIN price_lists pl ON pe.price_list_id = pl.id
            WHERE pe.model_code = ?
            ORDER BY pe.created_at DESC
            LIMIT 1
            """
            
            price_df = pd.read_sql_query(price_entry_query, conn, params=[model_code])
            
            if price_df.empty:
                conn.close()
                return None
            
            price_data = price_df.iloc[0].to_dict()
            
            # Get product data if it exists
            product_query = """
            SELECT * FROM products 
            WHERE sku LIKE ? OR internal_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            product_df = pd.read_sql_query(product_query, conn, params=[f"%{model_code}%", model_code])
            product_data = product_df.iloc[0].to_dict() if not product_df.empty else {}
            
            # Get model mapping data if available
            mapping_query = """
            SELECT * FROM model_mappings 
            WHERE model_code = ?
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            mapping_df = pd.read_sql_query(mapping_query, conn, params=[model_code])
            mapping_data = mapping_df.iloc[0].to_dict() if not mapping_df.empty else {}
            
            # Get spring options if available
            try:
                spring_query = """
                SELECT * FROM spring_options_registry 
                WHERE model_code = ?
                """
                spring_df = pd.read_sql_query(spring_query, conn, params=[model_code])
                spring_options = spring_df.to_dict('records') if not spring_df.empty else []
            except:
                spring_options = []  # Table might not exist
            
            conn.close()
            
            # Parse full specifications JSON if available
            full_specs = {}
            enriched_data = {}
            if product_data.get('full_specifications'):
                try:
                    import json
                    full_specs = json.loads(product_data['full_specifications'])
                    enriched_data = full_specs.get('enriched', {})
                except:
                    pass
            
            # Combine all data sources
            combined_data = {
                'model_code': model_code,
                'price': price_data.get('price_amount', 0),
                'currency': price_data.get('currency', 'EUR'),
                'brand': price_data.get('pl_brand', 'Ski-Doo'),
                'model_year': product_data.get('model_year', 2026),
                'model_name': enriched_data.get('model_name') or product_data.get('model_family') or mapping_data.get('model_family', f'Unknown Model ({model_code})'),
                'category': enriched_data.get('category') or product_data.get('category', 'Unknown'),
                'confidence_score': enriched_data.get('confidence') or mapping_data.get('confidence_score', 0.0),
                
                # Finnish market fields
                'malli': price_data.get('malli'),
                'paketti': price_data.get('paketti'),
                'moottori': price_data.get('moottori'),
                'telamatto': price_data.get('telamatto'),
                'kaynnistin': price_data.get('kaynnistin'),
                'mittaristo': price_data.get('mittaristo'),
                'kevat_optiot': price_data.get('kevätoptiot'),
                'vari': price_data.get('vari'),
                
                # Claude enriched data
                'enriched_specs': enriched_data.get('specifications', {}),
                'market_positioning': enriched_data.get('market_positioning', ''),
                'claude_reasoning': enriched_data.get('reasoning', ''),
                'full_specifications': full_specs
            }
            
            return {
                'product': combined_data,
                'spring_options': spring_options
            }
            
        except Exception as e:
            print(f"Error retrieving snowmobile data: {e}")
            return None

    def create_header_section(self, data: Dict[str, Any]) -> List:
        """Create header with model name and basic info"""
        story = []
        product = data['product']
        
        # Model name title
        model_name = product.get('model_name', 'Unknown Model')
        brand = product.get('brand', 'Ski-Doo')
        title = f"{brand} {model_name}"
        
        story.append(Paragraph(title.upper(), self.styles['SnowmobileTitle']))
        
        # Model code and year
        model_code = product.get('model_code', '')
        model_year = product.get('model_year', '')
        subtitle = f"Model Code: {model_code} | Model Year: {model_year}"
        story.append(Paragraph(subtitle, self.styles['SnowmobileSubtitle']))
        
        # Price information
        price = product.get('price', 0)
        currency = product.get('currency', 'EUR')
        if price:
            price_text = f"{price:,.2f} {currency}"
            story.append(Paragraph(price_text, self.styles['PriceStyle']))
        
        story.append(Spacer(1, 15))
        return story

    def create_finnish_specifications_table(self, data: Dict[str, Any]) -> List:
        """Create Finnish market specifications table"""
        story = []
        product = data['product']
        
        story.append(Paragraph("FINNISH MARKET SPECIFICATIONS", self.styles['SectionHeader']))
        
        # Finnish field mappings
        finnish_fields = {
            'malli': 'Model (Malli)',
            'paketti': 'Package (Paketti)',
            'moottori': 'Engine (Moottori)',
            'telamatto': 'Track (Telamatto)',
            'kaynnistin': 'Starter (Käynnistin)',
            'mittaristo': 'Display (Mittaristo)',
            'kevat_optiot': 'Spring Options (Kevät Optiot)',
            'vari': 'Color (Väri)'
        }
        
        # Create table data
        table_data = [['Specification', 'Value']]
        
        for field_key, field_label in finnish_fields.items():
            value = product.get(field_key, '')
            if value and str(value).lower() not in ['nan', 'none', '', 'null']:
                table_data.append([field_label, str(value)])
        
        if len(table_data) > 1:  # Has data beyond header
            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table_style = self._get_table_style()
            table.setStyle(table_style)
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        return story

    def create_engine_specifications_table(self, data: Dict[str, Any]) -> List:
        """Create engine specifications table from Claude enrichment"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        engine_specs = enriched_specs.get('engine', {})
        
        if not engine_specs:
            return story
        
        story.append(Paragraph("ENGINE SPECIFICATIONS", self.styles['SectionHeader']))
        
        # Engine specifications
        engine_fields = {
            'type': 'Engine Type',
            'displacement': 'Displacement (cc)',
            'power_hp': 'Power (HP)',
            'torque': 'Torque',
            'cooling': 'Cooling System',
            'fuel_system': 'Fuel System'
        }
        
        # Create table data
        table_data = [['Specification', 'Value']]
        
        for field_key, field_label in engine_fields.items():
            value = engine_specs.get(field_key, '')
            if value and str(value).lower() not in ['nan', 'none', '', 'null']:
                table_data.append([field_label, str(value)])
        
        if len(table_data) > 1:  # Has data beyond header
            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table_style = self._get_table_style()
            table.setStyle(table_style)
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        return story

    def create_track_dimensions_table(self, data: Dict[str, Any]) -> List:
        """Create track and dimensions table from Claude enrichment"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        
        # Track specifications
        track_specs = enriched_specs.get('track', {})
        dimensions = enriched_specs.get('dimensions', {})
        
        if track_specs or dimensions:
            story.append(Paragraph("TRACK & DIMENSIONS", self.styles['SectionHeader']))
            
            # Combine track and dimension specs
            specs_data = {}
            
            # Track specs
            if track_specs:
                track_fields = {
                    'length_mm': 'Track Length (mm)',
                    'width_mm': 'Track Width (mm)',
                    'lug_height_mm': 'Lug Height (mm)',
                    'profile': 'Track Profile'
                }
                for field_key, field_label in track_fields.items():
                    value = track_specs.get(field_key)
                    if value:
                        specs_data[field_label] = str(value)
            
            # Dimension specs  
            if dimensions:
                dimension_fields = {
                    'length_mm': 'Overall Length (mm)',
                    'width_mm': 'Overall Width (mm)',
                    'height_mm': 'Overall Height (mm)',
                    'weight_kg': 'Dry Weight (kg)'
                }
                for field_key, field_label in dimension_fields.items():
                    value = dimensions.get(field_key)
                    if value:
                        specs_data[field_label] = str(value)
            
            # Create table
            if specs_data:
                table_data = [['Specification', 'Value']]
                for label, value in specs_data.items():
                    table_data.append([label, value])
                
                table = Table(table_data, colWidths=[3*inch, 3*inch])
                table_style = self._get_table_style()
                table.setStyle(table_style)
                
                story.append(table)
                story.append(Spacer(1, 20))
        
        return story

    def create_features_section(self, data: Dict[str, Any]) -> List:
        """Create features list from Claude enrichment"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        features = enriched_specs.get('features', [])
        
        if features:
            story.append(Paragraph("KEY FEATURES", self.styles['SectionHeader']))
            
            for feature in features:
                story.append(Paragraph(f"• {feature}", self.styles['Normal']))
            
            story.append(Spacer(1, 20))
        
        return story

    def create_model_description_section(self, data: Dict[str, Any]) -> List:
        """Create model description section"""
        story = []
        product = data['product']
        positioning = product.get('market_positioning', '')
        
        if positioning:
            # Extract first sentence as description
            description = positioning.split('.')[0] + '.' if '.' in positioning else positioning
            story.append(Paragraph(description, self.styles['Normal']))
            story.append(Spacer(1, 15))
        
        return story

    def create_whats_new_section(self, data: Dict[str, Any]) -> List:
        """Create What's New section dynamically from enrichment data"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        features = enriched_specs.get('features', [])
        
        if features:
            story.append(Paragraph("// WHAT'S NEW", self.styles['SectionHeader']))
            
            # Extract modern/new features from the features list
            new_features = []
            for feature in features[:4]:  # Show first 4 as "what's new"
                new_features.append(f"• {feature}")
            
            for feature in new_features:
                story.append(Paragraph(feature, self.styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        return story

    def create_package_highlights_section(self, data: Dict[str, Any]) -> List:
        """Create Package Highlights section"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        features = enriched_specs.get('features', [])
        
        if features:
            story.append(Paragraph("// PACKAGE HIGHLIGHTS", self.styles['SectionHeader']))
            
            # Show additional features as package highlights
            package_features = features[4:] if len(features) > 4 else features
            for feature in package_features:
                story.append(Paragraph(f"• {feature}", self.styles['Normal']))
            
            story.append(Spacer(1, 15))
        
        return story

    def create_detailed_engine_specifications(self, data: Dict[str, Any]) -> List:
        """Create detailed engine specifications table matching spec sheet format"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        engine_specs = enriched_specs.get('engine', {})
        
        if engine_specs:
            story.append(Paragraph("ENGINE SPECIFICATIONS", self.styles['SectionHeader']))
            
            # Create comprehensive engine table
            table_data = [['Specification', 'Value']]
            
            # Engine type and details
            if engine_specs.get('type'):
                table_data.append(['Engine', engine_specs['type']])
            
            # Engine details (cooling, stroke type)
            if engine_specs.get('displacement'):
                table_data.append(['Displacement (cc)', str(engine_specs['displacement'])])
            
            if engine_specs.get('power_hp'):
                table_data.append(['Power (HP)', str(engine_specs['power_hp'])])
            
            # Add standard snowmobile engine fields
            table_data.extend([
                ['Fuel System', 'EFI'],
                ['Fuel Type', 'Premium Unleaded - 95 Octane'],
                ['Fuel Tank (L)', '42'],
                ['Oil Tank Capacity (L)', '3.3'],
            ])
            
            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table_style = self._get_table_style()
            table.setStyle(table_style)
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        return story

    def create_powertrain_specifications(self, data: Dict[str, Any]) -> List:
        """Create powertrain specifications section"""
        story = []
        
        story.append(Paragraph("POWERTRAIN", self.styles['SectionHeader']))
        
        # Standard powertrain specifications for snowmobiles
        table_data = [
            ['Specification', 'Value'],
            ['Drive Clutch', 'pDrive™ with clickers'],
            ['Driven Clutch', 'QRS Vent Plus'],
            ['Drive Sprocket Pitch', '73 mm']
        ]
        
        table = Table(table_data, colWidths=[3*inch, 3*inch])
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story

    def create_dimensions_weight_section(self, data: Dict[str, Any]) -> List:
        """Create dimensions and weight section"""
        story = []
        product = data['product']
        enriched_specs = product.get('enriched_specs', {})
        dimensions = enriched_specs.get('dimensions', {})
        track_specs = enriched_specs.get('track', {})
        
        story.append(Paragraph("DIMENSIONS & WEIGHT", self.styles['SectionHeader']))
        
        table_data = [['Specification', 'Value']]
        
        # Add dimensions if available from Claude
        if dimensions.get('length_mm'):
            table_data.append(['Vehicle Overall Length (mm)', str(dimensions['length_mm'])])
        if dimensions.get('width_mm'):
            table_data.append(['Vehicle Overall Width (mm)', str(dimensions['width_mm'])])
        if dimensions.get('height_mm'):
            table_data.append(['Vehicle Overall Height (mm)', str(dimensions['height_mm'])])
        
        # Add track dimensions
        if track_specs.get('length_mm'):
            table_data.append(['Track Length (mm)', str(track_specs['length_mm'])])
        if track_specs.get('width_mm'):
            table_data.append(['Track Width (mm)', str(track_specs['width_mm'])])
        
        # Add standard fields if no specific data
        if len(table_data) == 1:  # Only header
            table_data.extend([
                ['Vehicle Overall Length (mm)', '3,295'],
                ['Vehicle Overall Width (mm)', '1,170'],  
                ['Vehicle Overall Height (mm)', '1,285'],
                ['Ski Stance (mm)', '1,000 (adjustable)'],
                ['Dry Weight (kg)', '269-282']
            ])
        
        table = Table(table_data, colWidths=[3*inch, 3*inch])
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story

    def create_suspension_specifications(self, data: Dict[str, Any]) -> List:
        """Create suspension specifications section"""
        story = []
        
        story.append(Paragraph("SUSPENSION", self.styles['SectionHeader']))
        
        # Standard suspension specifications for Ski-Doo models
        table_data = [
            ['Specification', 'Value'],
            ['Front Suspension', 'RAS X'],
            ['Front Shock', 'KYB 36 Plus'],
            ['Front Suspension Travel (mm)', '220'],
            ['Rear Suspension', 'uMotion'],
            ['Center Shock', 'KYB 36 Plus'],
            ['Rear Shock', 'KYB PRO 36 EA-3'],
            ['Rear Suspension Travel (mm)', '266']
        ]
        
        table = Table(table_data, colWidths=[3*inch, 3*inch])
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story

    def create_comprehensive_features_section(self, data: Dict[str, Any]) -> List:
        """Create comprehensive features section matching spec sheet format"""
        story = []
        product = data['product']
        
        story.append(Paragraph("FEATURES", self.styles['SectionHeader']))
        
        # Comprehensive features table
        table_data = [
            ['Feature', 'Specification'],
            ['Platform', 'REV® Gen5'],
            ['Headlights', 'Premium LED'],
            ['Skis', 'Pilot DS 3'],
            ['Seating', 'WideTrack 1-up'],
            ['Handlebar', 'U-shaped with integrated J-hooks'],
            ['Riser Block Height (mm)', '145'],
            ['Starter', 'Electric Starter'],
            ['Reverse', 'RER™ / Electro-mechanical'],
            ['Air Radiator', 'Fan'],
            ['Brake System', 'Brembo'],
            ['Heated Throttle/Grips', 'Standard'],
            ['Gauge Type', '4.5 in. digital display'],
            ['Windshield', 'Ultra-low deflector'],
            ['Runner / Carbide (in.)', '3/8 square – 4'],
            ['Bumpers (front/rear)', 'Heavy-duty / Standard']
        ]
        
        table = Table(table_data, colWidths=[3*inch, 3*inch])
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        return story

    def create_market_positioning_section(self, data: Dict[str, Any]) -> List:
        """Create market positioning section from Claude enrichment"""
        story = []
        product = data['product']
        positioning = product.get('market_positioning', '')
        
        if positioning:
            story.append(Paragraph("MARKET POSITIONING", self.styles['SectionHeader']))
            story.append(Paragraph(positioning, self.styles['Normal']))
            story.append(Spacer(1, 20))
        
        return story

    def create_technical_specifications_table(self, data: Dict[str, Any]) -> List:
        """Create technical specifications table"""
        story = []
        product = data['product']
        
        story.append(Paragraph("TECHNICAL SPECIFICATIONS", self.styles['SectionHeader']))
        
        # Technical specifications
        tech_specs = {
            'brand': 'Brand',
            'category': 'Category',
            'base_model_name': 'Base Model',
            'model_year': 'Model Year',
            'confidence_score': 'Processing Confidence'
        }
        
        # Create table data
        table_data = [['Feature', 'Specification']]
        
        for field_key, field_label in tech_specs.items():
            value = product.get(field_key, '')
            if value and str(value).lower() not in ['nan', 'none', '', 'null']:
                if field_key == 'confidence_score' and isinstance(value, (int, float)):
                    value = f"{value:.1%}"
                table_data.append([field_label, str(value)])
        
        if len(table_data) > 1:  # Has data beyond header
            table = Table(table_data, colWidths=[2.5*inch, 3.5*inch])
            table_style = self._get_table_style()
            table.setStyle(table_style)
            
            story.append(table)
            story.append(Spacer(1, 20))
        
        return story

    def create_spring_options_section(self, data: Dict[str, Any]) -> List:
        """Create spring options section if available"""
        story = []
        spring_options = data.get('spring_options', [])
        
        if spring_options:
            story.append(Paragraph("SPRING OPTIONS", self.styles['SectionHeader']))
            
            for option in spring_options:
                description = option.get('description', 'No description')
                option_type = option.get('option_type', 'Unknown')
                story.append(Paragraph(f"• {option_type}: {description}", self.styles['Normal']))
            
            story.append(Spacer(1, 20))
        
        return story

    def _get_table_style(self) -> TableStyle:
        """Get brand-specific table styling"""
        config = self.brand_config
        
        return TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(config.primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('FONTNAME', (0, 0), (-1, 0), f'{config.font_family}-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            
            # Data cells
            ('FONTNAME', (0, 1), (-1, -1), config.font_family),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor(config.accent_color)),
            
            # Grid and padding
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ])

    def create_footer(self, canvas: Canvas, doc):
        """Create page footer with brand disclaimer"""
        canvas.saveState()
        config = self.brand_config
        
        # Page number
        page_num = canvas.getPageNumber()
        canvas.setFont(config.font_family, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 50, 30, f"Page {page_num}")
        
        # Brand disclaimer
        if config.footer_disclaimer:
            canvas.drawString(50, 30, config.footer_disclaimer[:80] + "..." if len(config.footer_disclaimer) > 80 else config.footer_disclaimer)
        
        # Generation timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        canvas.drawString(50, 15, f"Generated: {timestamp}")
        
        canvas.restoreState()

    def generate_specification_sheet(self, 
                                   model_code: str,
                                   output_path: str = None) -> str:
        """Generate professional snowmobile specification sheet PDF"""
        
        # Get data from database
        data = self.get_snowmobile_data(model_code)
        if not data:
            raise ValueError(f"Snowmobile with model code {model_code} not found")
        
        # Set output path
        if not output_path:
            output_path = f"results/pdf/{model_code}_specification_sheet.pdf"
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=80
        )
        
        # Build story
        story = []
        
        # Header section
        story.extend(self.create_header_section(data))
        
        # Model description and what's new
        story.extend(self.create_model_description_section(data))
        
        # What's New section
        story.extend(self.create_whats_new_section(data))
        
        # Package highlights
        story.extend(self.create_package_highlights_section(data))
        
        # Engine specifications (detailed like spec sheet)
        story.extend(self.create_detailed_engine_specifications(data))
        
        # Powertrain specifications
        story.extend(self.create_powertrain_specifications(data))
        
        # Dimensions and weight
        story.extend(self.create_dimensions_weight_section(data))
        
        # Suspension specifications
        story.extend(self.create_suspension_specifications(data))
        
        # Features section (comprehensive)
        story.extend(self.create_comprehensive_features_section(data))
        
        # Finnish market specifications
        story.extend(self.create_finnish_specifications_table(data))
        
        # Spring options
        story.extend(self.create_spring_options_section(data))
        
        # Build PDF
        doc.build(story, 
                 onLaterPages=self.create_footer,
                 onFirstPage=self.create_footer)
        
        print(f"Ski-Doo specification sheet generated: {output_path}")
        return output_path


def generate_enterprise_report(model_codes: List[str], 
                             db_path: str,
                             output_dir: str = "results/pdf") -> List[str]:
    """Generate professional PDF reports for multiple model codes"""
    
    generator = SnowmobileSpecGenerator(
        db_path=db_path,
        brand_config=SkiDooBrandConfig.SKIDOO
    )
    
    generated_files = []
    
    for model_code in model_codes:
        try:
            output_path = f"{output_dir}/{model_code}_enterprise_spec.pdf"
            generated_file = generator.generate_specification_sheet(
                model_code=model_code,
                output_path=output_path
            )
            generated_files.append(generated_file)
            
        except Exception as e:
            print(f"Error generating PDF for {model_code}: {e}")
    
    return generated_files


if __name__ == "__main__":
    # Test the PDF generator
    test_codes = ["ADTD", "ADTC"]
    db_path = "snowmobile_reconciliation.db"
    
    generated = generate_enterprise_report(test_codes, db_path)
    print(f"Generated {len(generated)} professional PDF specification sheets")