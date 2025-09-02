#!/usr/bin/env python3
"""
Unified Vehicle Specification Sheet Generator
Generates professional PDF vehicle spec sheets for multiple brands (Lynx, Ski-Doo, etc.)
using ReportLab and SQL database data with configurable brand styling.
"""

import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, mm, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, KeepTogether, Frame, PageTemplate
)
from reportlab.pdfgen.canvas import Canvas


@dataclass
class BrandConfig:
    """Configuration for brand-specific styling and layout"""
    name: str
    primary_color: str  # Hex color code
    secondary_color: str
    accent_color: str
    logo_path: Optional[str] = None
    font_family: str = "Helvetica"
    title_font_size: int = 36
    subtitle_font_size: int = 14
    section_header_font_size: int = 16
    whats_new_header: str = "// WHAT'S NEW"
    package_header: str = "// PACKAGE HIGHLIGHTS"
    use_two_column_layout: bool = True
    footer_disclaimer: str = ""


class BrandConfigs:
    """Predefined brand configurations"""
    
    LYNX = BrandConfig(
        name="Lynx",
        primary_color="#E60000",  # Lynx red
        secondary_color="#333333",
        accent_color="#F5F5F5",
        title_font_size=36,
        footer_disclaimer="BRP reserves the right to modify, change, or discontinue this product at any time without incurring obligation."
    )
    
    SKIDOO = BrandConfig(
        name="Ski-Doo",
        primary_color="#FFD700",  # Ski-Doo yellow
        secondary_color="#333333", 
        accent_color="#F5F5F5",
        title_font_size=32,
        whats_new_header="// WHAT'S NEW",
        package_header="// PACKAGE HIGHLIGHTS",
        footer_disclaimer="Ski-Doo reserves the right to modify specifications without notice."
    )
    
    @classmethod
    def get_config(cls, brand_name: str) -> BrandConfig:
        """Get brand configuration by name"""
        configs = {
            "lynx": cls.LYNX,
            "ski-doo": cls.SKIDOO,
            "skidoo": cls.SKIDOO
        }
        return configs.get(brand_name.lower(), cls.LYNX)


class UnifiedVehicleSpecGenerator:
    """Unified generator for professional vehicle specification PDFs"""
    
    def __init__(self, db_path: str = "vehicles.db", brand_config: Optional[BrandConfig] = None):
        self.db_path = db_path
        self.brand_config = brand_config or BrandConfigs.LYNX
        self.setup_styles()
        
    def setup_styles(self):
        """Define brand-specific styles for the document"""
        self.styles = getSampleStyleSheet()
        config = self.brand_config
        
        # Page title style
        self.styles.add(ParagraphStyle(
            name='VehicleTitle',
            parent=self.styles['Heading1'],
            fontSize=config.title_font_size,
            textColor=colors.HexColor(config.primary_color),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='VehicleSubtitle',
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
        
        # What's New header
        self.styles.add(ParagraphStyle(
            name='WhatsNewHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor(config.primary_color),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=6,
            spaceBefore=12,
            alignment=TA_LEFT
        ))
        
        # Package highlights header
        self.styles.add(ParagraphStyle(
            name='PackageHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor(config.primary_color),
            fontName=f'{config.font_family}-Bold',
            spaceAfter=6,
            spaceBefore=12,
            alignment=TA_LEFT
        ))
        
        # Bullet point style
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName=config.font_family,
            spaceAfter=3,
            leftIndent=12,
            alignment=TA_LEFT
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName=f'{config.font_family}-Bold',
            textColor=colors.white,
            alignment=TA_CENTER
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

    def get_vehicle_data(self, vehicle_id: int) -> Dict[str, Any]:
        """Retrieve complete vehicle data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get vehicle basic info
            vehicle_query = """
            SELECT v.*, m.name as model_name, m.platform as model_platform
            FROM vehicles v
            LEFT JOIN models m ON v.model_id = m.id
            WHERE v.id = ?
            """
            vehicle_df = pd.read_sql_query(vehicle_query, conn, params=[vehicle_id])
            
            if vehicle_df.empty:
                return {'vehicle': None, 'engines': [], 'specifications': {}}
            
            # Get engine data
            engine_query = """
            SELECT * FROM engines WHERE vehicle_id = ?
            """
            engine_df = pd.read_sql_query(engine_query, conn, params=[vehicle_id])
            
            # Get additional specifications (if tables exist)
            specifications = {}
            try:
                specs_tables = ['powertrain', 'dimensions', 'suspension', 'features']
                for table in specs_tables:
                    spec_query = f"SELECT * FROM {table} WHERE vehicle_id = ?"
                    spec_df = pd.read_sql_query(spec_query, conn, params=[vehicle_id])
                    if not spec_df.empty:
                        specifications[table] = spec_df.to_dict('records')
            except Exception:
                pass  # Tables might not exist
            
            conn.close()
            
            return {
                'vehicle': vehicle_df.iloc[0].to_dict(),
                'engines': engine_df.to_dict('records'),
                'specifications': specifications
            }
            
        except Exception as e:
            print(f"Error retrieving vehicle data: {e}")
            return {'vehicle': None, 'engines': [], 'specifications': {}}

    def create_header_section(self, vehicle_data: Dict[str, Any]) -> List:
        """Create the main header section with vehicle title and description"""
        story = []
        vehicle = vehicle_data['vehicle']
        
        # Vehicle title
        title = vehicle.get('model_name', 'Unknown Model')
        story.append(Paragraph(title.upper(), self.styles['VehicleTitle']))
        
        # Vehicle description/tagline
        if vehicle.get('description'):
            story.append(Paragraph(vehicle['description'], self.styles['VehicleSubtitle']))
        
        return story

    def create_whats_new_section(self, vehicle_data: Dict[str, Any]) -> List:
        """Create the What's New section"""
        story = []
        vehicle = vehicle_data['vehicle']
        
        # Section header
        story.append(Paragraph(self.brand_config.whats_new_header, self.styles['WhatsNewHeader']))
        
        # For demo purposes, create some sample "what's new" items
        # In practice, this would come from the database
        whats_new_items = [
            "Enhanced suspension system",
            "New digital display technology", 
            "Improved fuel efficiency",
            "Updated styling and colors"
        ]
        
        for item in whats_new_items:
            story.append(Paragraph(f"• {item}", self.styles['BulletPoint']))
        
        story.append(Spacer(1, 12))
        return story

    def create_package_highlights_section(self, vehicle_data: Dict[str, Any]) -> List:
        """Create the Package Highlights section"""
        story = []
        vehicle = vehicle_data['vehicle']
        
        # Section header
        story.append(Paragraph(self.brand_config.package_header, self.styles['PackageHeader']))
        
        # Extract highlights from vehicle data
        highlights = []
        if vehicle.get('skis'):
            highlights.append(f"• {vehicle['skis']} skis")
        if vehicle.get('brake_system'):
            highlights.append(f"• {vehicle['brake_system']} brake system")
        if vehicle.get('headlights'):
            highlights.append(f"• {vehicle['headlights']} headlights")
        if vehicle.get('gauge_type'):
            highlights.append(f"• {vehicle['gauge_type']} display")
        if vehicle.get('heated_grips'):
            highlights.append(f"• {vehicle['heated_grips']} grips")
        
        for highlight in highlights:
            story.append(Paragraph(highlight, self.styles['BulletPoint']))
        
        story.append(Spacer(1, 12))
        return story

    def create_engine_specifications_table(self, vehicle_data: Dict[str, Any]) -> List:
        """Create detailed engine specifications table"""
        story = []
        engines = vehicle_data['engines']
        
        if not engines:
            return story
        
        # Table header
        story.append(Paragraph("ENGINE SPECIFICATIONS", self.styles['SectionHeader']))
        
        # Define fields to display
        engine_fields = {
            'name': 'Engine',
            'displacement_info': 'Displacement', 
            'bore_stroke': 'Bore × Stroke',
            'max_rpm': 'Maximum RPM',
            'carburation': 'Fuel System',
            'fuel_type': 'Fuel Type',
            'fuel_tank_capacity': 'Fuel Tank (L)',
            'oil_capacity': 'Oil Capacity (L)'
        }
        
        # Create table data
        table_data = []
        
        # Header row
        header_row = ['Specification']
        for engine in engines:
            engine_name = engine.get('name', 'Engine')
            header_row.append(engine_name)
        table_data.append(header_row)
        
        # Data rows
        for field_key, field_label in engine_fields.items():
            row = [field_label]
            for engine in engines:
                value = engine.get(field_key, '')
                if value and str(value).lower() not in ['nan', 'none', '']:
                    row.append(str(value))
                else:
                    row.append('—')
            table_data.append(row)
        
        # Calculate column widths
        num_engines = len(engines)
        col_widths = [3*inch] + [2*inch] * num_engines
        
        # Create table
        table = Table(table_data, colWidths=col_widths)
        
        # Apply brand-specific styling
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        return story

    def create_vehicle_specifications_table(self, vehicle_data: Dict[str, Any]) -> List:
        """Create vehicle specifications table"""
        story = []
        vehicle = vehicle_data['vehicle']
        
        story.append(Paragraph("VEHICLE SPECIFICATIONS", self.styles['SectionHeader']))
        
        # Define vehicle specifications
        vehicle_specs = {
            'platform': 'Platform',
            'dry_weight': 'Dry Weight (kg)',
            'starter': 'Starter',
            'reverse': 'Reverse',
            'seating': 'Seating',
            'handlebar': 'Handlebar',
            'riser_height': 'Riser Height (mm)',
            'windshield': 'Windshield',
            'usb_port': 'USB Port',
            'heated_grips': 'Heated Grips'
        }
        
        # Create table data
        table_data = [['Feature', 'Specification']]
        
        for field_key, field_label in vehicle_specs.items():
            value = vehicle.get(field_key, '')
            if value and str(value).lower() not in ['nan', 'none', 'false']:
                if isinstance(value, bool) and value:
                    value = 'Yes'
                elif isinstance(value, bool):
                    value = 'No'
                table_data.append([field_label, str(value)])
        
        # Create table
        table = Table(table_data, colWidths=[3*inch, 2*inch])
        table_style = self._get_table_style()
        table.setStyle(table_style)
        
        story.append(table)
        story.append(Spacer(1, 20))
        return story

    def _get_table_style(self) -> TableStyle:
        """Get brand-specific table styling"""
        config = self.brand_config
        
        return TableStyle([
            # Header row styling
            ('BACKGROUND', (1, 0), (-1, 0), colors.HexColor(config.primary_color)),
            ('TEXTCOLOR', (1, 0), (-1, 0), colors.white),
            ('FONTNAME', (1, 0), (-1, 0), f'{config.font_family}-Bold'),
            ('FONTSIZE', (1, 0), (-1, 0), 10),
            
            # First column styling (field names)
            ('FONTNAME', (0, 1), (0, -1), config.font_family),
            ('FONTSIZE', (0, 1), (0, -1), 9),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor(config.accent_color)),
            
            # Data cells
            ('FONTNAME', (1, 1), (-1, -1), config.font_family),
            ('FONTSIZE', (1, 1), (-1, -1), 9),
            
            # Grid lines and padding
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ])

    def add_vehicle_image(self, story: List, vehicle_data: Dict[str, Any], image_path: str):
        """Add vehicle image to the document"""
        if Path(image_path).exists():
            try:
                img = Image(image_path, width=6*inch, height=3*inch)
                img.hAlign = 'LEFT'
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception as e:
                print(f"Warning: Could not load image {image_path}: {e}")

    def create_footer(self, canvas: Canvas, doc):
        """Create page footer with brand-specific styling"""
        canvas.saveState()
        config = self.brand_config
        
        # Page number
        page_num = canvas.getPageNumber()
        canvas.setFont(config.font_family, 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 50, 30, f"Page {page_num}")
        
        # Brand disclaimer
        if config.footer_disclaimer:
            canvas.drawString(50, 30, config.footer_disclaimer)
        
        canvas.restoreState()

    def generate_spec_sheet(self, 
                          vehicle_id: int, 
                          output_path: str = "vehicle_spec.pdf", 
                          image_path: Optional[str] = None) -> str:
        """Generate complete vehicle specification sheet PDF"""
        
        # Get data from database
        vehicle_data = self.get_vehicle_data(vehicle_id)
        if not vehicle_data or vehicle_data['vehicle'] is None:
            raise ValueError(f"Vehicle with ID {vehicle_id} not found")
        
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
        
        # Add vehicle image if provided
        if image_path:
            self.add_vehicle_image(story, vehicle_data, image_path)
        
        # Header section
        story.extend(self.create_header_section(vehicle_data))
        story.append(Spacer(1, 20))
        
        # What's New and Package Highlights
        story.extend(self.create_whats_new_section(vehicle_data))
        story.extend(self.create_package_highlights_section(vehicle_data))
        
        # Specifications tables
        story.extend(self.create_engine_specifications_table(vehicle_data))
        story.extend(self.create_vehicle_specifications_table(vehicle_data))
        
        # Build PDF
        doc.build(story, onLaterPages=self.create_footer, 
                 onFirstPage=self.create_footer)
        
        print(f"{self.brand_config.name} specification sheet generated: {output_path}")
        return output_path


def create_sample_database():
    """Create sample database with vehicle data for testing"""
    conn = sqlite3.connect("vehicles.db")
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
    DROP TABLE IF EXISTS engines;
    DROP TABLE IF EXISTS vehicles;
    DROP TABLE IF EXISTS models;
    
    CREATE TABLE models (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        platform TEXT,
        brand TEXT
    );
    
    CREATE TABLE vehicles (
        id INTEGER PRIMARY KEY,
        model_id INTEGER,
        description TEXT,
        platform TEXT,
        headlights TEXT,
        skis TEXT,
        seating TEXT,
        handlebar TEXT,
        riser_height INTEGER,
        starter TEXT,
        reverse TEXT,
        air_radiator BOOLEAN,
        brake_system TEXT,
        heated_grips TEXT,
        gauge_type TEXT,
        windshield TEXT,
        visor_plug TEXT,
        usb_port BOOLEAN,
        bumpers TEXT,
        hitch BOOLEAN,
        gearbox TEXT,
        clutch_system TEXT,
        dry_weight INTEGER,
        is_utility BOOLEAN,
        is_trail BOOLEAN,
        is_deep_snow BOOLEAN,
        is_family BOOLEAN,
        FOREIGN KEY (model_id) REFERENCES models (id)
    );
    
    CREATE TABLE engines (
        id INTEGER PRIMARY KEY,
        vehicle_id INTEGER,
        name TEXT,
        description TEXT,
        displacement_info TEXT,
        bore_stroke TEXT,
        max_rpm TEXT,
        carburation TEXT,
        fuel_type TEXT,
        fuel_tank_capacity INTEGER,
        oil_capacity REAL,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    );
    """)
    
    # Insert sample data
    cursor.executescript("""
    INSERT INTO models (id, name, platform, brand) VALUES
    (1, 'RAVE RE', 'Trail', 'Lynx'),
    (2, 'MXZ X-RS', 'Performance', 'Ski-Doo');
    
    INSERT INTO vehicles (id, model_id, description, platform, headlights, skis, seating, 
                         handlebar, starter, reverse, brake_system, heated_grips, 
                         gauge_type, windshield, usb_port, dry_weight) VALUES
    (1, 1, 'High-performance trail sled with advanced suspension', 'REV Gen4', 
     'Premium LED', 'Pilot RX', 'Solo', 'Standard', 'Electric', 'RER', 
     'Brembo', 'Premium', '7.2 in. Digital Display', 'Mid', 1, 185),
    (2, 2, 'An uncompromising race-inspired sled capable of taking on the roughest trails', 
     'REV Gen4', 'Premium LED', 'Pilot RX', 'Solo', 'Standard', 'Electric', 'RER',
     'High-performance KYB Pro', 'Heated', '10.25 in. touchscreen', 'Mid', 1, 190);
    
    INSERT INTO engines (id, vehicle_id, name, displacement_info, bore_stroke, max_rpm, 
                        carburation, fuel_type, fuel_tank_capacity, oil_capacity) VALUES
    (1, 1, '600R E-TEC', '600cc 2-stroke', '72 x 73.8 mm', '8000 RPM', 
     'Electronic Fuel Injection', 'Premium Unleaded', 40, 2.6),
    (2, 2, '850 E-TEC Turbo R', '850cc 2-stroke Turbo', '82 x 80.4 mm', '8100 RPM',
     'Electronic Fuel Injection', 'Premium Unleaded', 42, 3.1);
    """)
    
    conn.commit()
    conn.close()
    print("Sample database created successfully!")


# Usage examples
if __name__ == "__main__":
    # Create sample database
    create_sample_database()
    
    # Generate Lynx specification sheet
    lynx_generator = UnifiedVehicleSpecGenerator(
        db_path="vehicles.db",
        brand_config=BrandConfigs.LYNX
    )
    lynx_generator.generate_spec_sheet(
        vehicle_id=1, 
        output_path="lynx_rave_re_spec.pdf"
    )
    
    # Generate Ski-Doo specification sheet
    skidoo_generator = UnifiedVehicleSpecGenerator(
        db_path="vehicles.db", 
        brand_config=BrandConfigs.SKIDOO
    )
    skidoo_generator.generate_spec_sheet(
        vehicle_id=2, 
        output_path="skidoo_mxz_xrs_spec.pdf"
    )
    
    print("Both specification sheets generated successfully!")
