#!/usr/bin/env python3
"""
LLM JSON Parser - Converts nested LLM response to flattened database fields
Handles the Expected Structure from LLM_promt_spec_books.md
"""

import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMJsonParser:
    """Parser to convert LLM nested JSON response to flattened database fields"""
    
    def __init__(self, db_path: str = "dual_db.db"):
        self.db_path = db_path
    
    def parse_llm_response(self, llm_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse complete LLM JSON response into flattened database fields
        
        Args:
            llm_json: Complete LLM response matching Expected Structure
            
        Returns:
            Dict with flattened fields matching llm_specbook_data_target_schema
        """
        
        # Initialize result dictionary with all possible fields
        result = {
            # Basic Info fields
            'basic_info_brand': None,
            'basic_info_model': None,
            'basic_info_configuration': None,
            'basic_info_category': None,
            'basic_info_model_year': None,
            'basic_info_description': None,
            
            # Marketing Content fields
            'marketing_content_whats_new': None,
            'marketing_content_package_highlights': None,
            'marketing_content_spring_options': None,
            
            # Engines (JSON array + extracted values)
            'engines': None,
            
            # Weight fields
            'weight_min': None,
            'weight_max': None,
            
            # Dimensions fields
            'dimensions_overall_length': None,
            'dimensions_overall_width': None,
            'dimensions_overall_height': None,
            'dimensions_ski_stance': None,
            'dimensions_fuel_capacity': None,
            
            # Tracks (JSON array)
            'tracks': None,
            
            # Suspension fields
            'suspension_front_type': None,
            'suspension_front_travel': None,
            'suspension_front_shock': None,
            'suspension_front_adjustable': None,
            'suspension_rear_type': None,
            'suspension_rear_travel': None,
            'suspension_rear_shock': None,
            'suspension_rear_adjustable': None,
            'suspension_center_type': None,
            'suspension_center_shock': None,
            
            # Powertrain fields
            'powertrain_drive_clutch': None,
            'powertrain_driven_clutch': None,
            'powertrain_sprocket_pitch': None,
            'powertrain_belt_type': None,
            'powertrain_reverse': None,
            
            # Brakes fields
            'brakes_type': None,
            'brakes_pistons': None,
            'brakes_adjustable_lever': None,
            'brakes_description': None,
            
            # Features fields
            'features_platform': None,
            'features_headlights': None,
            'features_skis': None,
            'features_seating': None,
            'features_handlebar': None,
            'features_riser_block_height': None,
            'features_windshield': None,
            'features_visor_plug': None,
            'features_usb': None,
            'features_bumpers': None,
            'features_runner': None,
            'features_heated_grips': None,
            'features_additional_features': None,
            
            # Colors (JSON array)
            'colors': None,
            
            # Pricing fields
            'pricing_msrp': None,
            'pricing_currency': None,
            'pricing_market': None,
            
            # Metadata fields
            'metadata_extraction_notes': None,
            'metadata_document_type': None,
            'metadata_completeness': None,
            
            # Full JSON storage
            'full_llm_json': None
        }
        
        # Store complete JSON
        result['full_llm_json'] = json.dumps(llm_json)
        
        # Parse basicInfo object
        basic_info = llm_json.get('basicInfo', {})
        if basic_info:
            result['basic_info_brand'] = basic_info.get('brand')
            result['basic_info_model'] = basic_info.get('model')
            result['basic_info_configuration'] = basic_info.get('configuration')
            result['basic_info_category'] = basic_info.get('category')
            result['basic_info_model_year'] = basic_info.get('modelYear')
            result['basic_info_description'] = basic_info.get('description')
        
        # Parse marketingContent object
        marketing_content = llm_json.get('marketingContent', {})
        if marketing_content:
            whats_new = marketing_content.get('whatsNew')
            if whats_new:
                result['marketing_content_whats_new'] = json.dumps(whats_new)
                
            package_highlights = marketing_content.get('packageHighlights')
            if package_highlights:
                result['marketing_content_package_highlights'] = json.dumps(package_highlights)
                
            spring_options = marketing_content.get('springOptions')
            if spring_options:
                result['marketing_content_spring_options'] = json.dumps(spring_options)
        
        # Parse engines array
        engines = llm_json.get('engines', [])
        if engines:
            result['engines'] = json.dumps(engines)
        
        # Parse weight object
        weight = llm_json.get('weight', {})
        if weight:
            result['weight_min'] = weight.get('min')
            result['weight_max'] = weight.get('max')
        
        # Parse dimensions object
        dimensions = llm_json.get('dimensions', {})
        if dimensions:
            overall = dimensions.get('overall', {})
            result['dimensions_overall_length'] = overall.get('length')
            result['dimensions_overall_width'] = overall.get('width')
            result['dimensions_overall_height'] = overall.get('height')
            result['dimensions_ski_stance'] = dimensions.get('skiStance')
            result['dimensions_fuel_capacity'] = dimensions.get('fuelCapacity')
        
        # Parse tracks array
        tracks = llm_json.get('tracks', [])
        if tracks:
            result['tracks'] = json.dumps(tracks)
        
        # Parse suspension object
        suspension = llm_json.get('suspension', {})
        if suspension:
            front = suspension.get('front', {})
            result['suspension_front_type'] = front.get('type')
            result['suspension_front_travel'] = front.get('travel')
            result['suspension_front_shock'] = front.get('shock')
            result['suspension_front_adjustable'] = front.get('adjustable')
            
            rear = suspension.get('rear', {})
            result['suspension_rear_type'] = rear.get('type')
            result['suspension_rear_travel'] = rear.get('travel')
            result['suspension_rear_shock'] = rear.get('shock')
            result['suspension_rear_adjustable'] = rear.get('adjustable')
            
            center = suspension.get('center', {})
            result['suspension_center_type'] = center.get('type')
            result['suspension_center_shock'] = center.get('shock')
        
        # Parse powertrain object
        powertrain = llm_json.get('powertrain', {})
        if powertrain:
            result['powertrain_drive_clutch'] = powertrain.get('driveClutch')
            result['powertrain_driven_clutch'] = powertrain.get('drivenClutch')
            result['powertrain_sprocket_pitch'] = powertrain.get('sprocketPitch')
            result['powertrain_belt_type'] = powertrain.get('beltType')
            result['powertrain_reverse'] = powertrain.get('reverse')
        
        # Parse brakes object
        brakes = llm_json.get('brakes', {})
        if brakes:
            result['brakes_type'] = brakes.get('type')
            result['brakes_pistons'] = brakes.get('pistons')
            result['brakes_adjustable_lever'] = brakes.get('adjustableLever')
            result['brakes_description'] = brakes.get('description')
        
        # Parse features object
        features = llm_json.get('features', {})
        if features:
            result['features_platform'] = features.get('platform')
            result['features_headlights'] = features.get('headlights')
            result['features_skis'] = features.get('skis')
            result['features_seating'] = features.get('seating')
            result['features_handlebar'] = features.get('handlebar')
            result['features_riser_block_height'] = features.get('riserBlockHeight')
            result['features_windshield'] = features.get('windshield')
            result['features_visor_plug'] = features.get('visorPlug')
            result['features_usb'] = features.get('usb')
            result['features_bumpers'] = features.get('bumpers')
            result['features_runner'] = features.get('runner')
            result['features_heated_grips'] = features.get('heatedGrips')
            
            additional_features = features.get('additionalFeatures')
            if additional_features:
                result['features_additional_features'] = json.dumps(additional_features)
        
        # Parse colors array
        colors = llm_json.get('colors', [])
        if colors:
            result['colors'] = json.dumps(colors)
        
        # Parse pricing object
        pricing = llm_json.get('pricing', {})
        if pricing:
            result['pricing_msrp'] = pricing.get('msrp')
            result['pricing_currency'] = pricing.get('currency')
            result['pricing_market'] = pricing.get('market')
        
        # Parse metadata object
        metadata = llm_json.get('metadata', {})
        if metadata:
            result['metadata_extraction_notes'] = metadata.get('extractionNotes')
            result['metadata_document_type'] = metadata.get('documentType')
            result['metadata_completeness'] = metadata.get('completeness')
        
        return result
    
    def insert_llm_response(self, llm_json: Dict[str, Any]) -> bool:
        """
        Parse LLM response and insert into llm_specbook_data_target_schema table
        
        Args:
            llm_json: Complete LLM JSON response
            
        Returns:
            bool: Success status
        """
        try:
            # Parse JSON to flattened fields
            parsed_data = self.parse_llm_response(llm_json)
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build INSERT statement dynamically
            columns = list(parsed_data.keys())
            placeholders = ['?' for _ in columns]
            values = [parsed_data[col] for col in columns]
            
            insert_sql = f"""
                INSERT INTO llm_specbook_data_target_schema
                ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(insert_sql, values)
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully inserted LLM response for {parsed_data.get('basic_info_brand')} {parsed_data.get('basic_info_model')}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting LLM response: {e}")
            return False
    
    def parse_json_string(self, llm_json_string: str) -> bool:
        """
        Parse LLM JSON string and insert into database
        
        Args:
            llm_json_string: JSON string from LLM response
            
        Returns:
            bool: Success status
        """
        try:
            llm_json = json.loads(llm_json_string)
            return self.insert_llm_response(llm_json)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON string: {e}")
            return False


def main():
    """Test the LLM JSON Parser with sample data"""
    parser = LLMJsonParser()
    
    # Sample LLM response matching Expected Structure
    sample_llm_response = {
        "basicInfo": {
            "brand": "Ski-Doo",
            "model": "Summit X",
            "configuration": "Expert Package", 
            "category": "deep-snow",
            "modelYear": 2026,
            "description": "Ultimate deep snow performance"
        },
        "marketingContent": {
            "whatsNew": [
                "REV Gen5 Lightweight platform",
                "813 mm ski stance",
                "Twin link steering"
            ],
            "packageHighlights": [
                "Premium LED headlights",
                "RAS 3 front suspension",
                "E-TEC SHOT starter standard"
            ],
            "springOptions": [
                "Terra Green color",
                "165\" track length"
            ]
        },
        "engines": [
            {
                "name": "850 E-TEC Turbo R",
                "type": "2-stroke",
                "displacement": 849,
                "bore": 82.0,
                "stroke": 80.4,
                "maxRPM": 7900,
                "turbo": True,
                "cooling": "liquid-cooled",
                "fuelSystem": "E-TEC direct injection with booster injectors",
                "fuelType": "Premium unleaded - 95",
                "octaneRating": 95,
                "fuelTank": 36,
                "oilCapacity": 3.4,
                "dryWeight": 207,
                "dryWeightVariant": 209,
                "starter": "E-TEC SHOT",
                "gaugeType": "10.25 in. touchscreen",
                "trackCompatibility": "All lengths"
            }
        ],
        "weight": {
            "min": 207,
            "max": 209
        },
        "dimensions": {
            "overall": {
                "length": 3188,
                "width": 971,
                "height": 1306
            },
            "skiStance": 813,
            "fuelCapacity": 36
        },
        "tracks": [
            {
                "name": "PowderMax X-Light",
                "size": "154 x 16 x 3.0",
                "dimensions": "154 x 16 x 3.0 in.",
                "availability": "standard",
                "engineCompatibility": "All engines"
            }
        ],
        "suspension": {
            "front": {
                "type": "RAS 3",
                "travel": 207,
                "shock": "KYB PRO 36 EA-3",
                "adjustable": True
            },
            "rear": {
                "type": "tMotion XT with rigid rear arm", 
                "travel": 264,
                "shock": "KYB PRO 36 EA-3",
                "adjustable": True
            },
            "center": {
                "type": "Standard",
                "shock": "KYB 36 Plus"
            }
        },
        "powertrain": {
            "driveClutch": "pDrive with clickers",
            "drivenClutch": "QRS Vent Plus",
            "sprocketPitch": 89,
            "beltType": "Standard",
            "reverse": "RER"
        },
        "brakes": {
            "type": "Brembo",
            "pistons": 1,
            "adjustableLever": True,
            "description": "Brembo with adjustable lever"
        },
        "features": {
            "platform": "REV Gen5",
            "headlights": "Premium LED",
            "skis": "Pilot DS 4",
            "seating": "Deep snow ultra compact",
            "handlebar": "Tapered with J-hooks",
            "riserBlockHeight": 120,
            "windshield": "No",
            "visorPlug": None,
            "usb": "No",
            "bumpers": "Standard",
            "runner": "3/8 square – 4",
            "heatedGrips": True,
            "additionalFeatures": [
                "E-TEC SHOT Starter",
                "10.25 in. touchscreen display"
            ]
        },
        "colors": [
            {
                "name": "Timeless Black",
                "code": "TB2026",
                "availability": "standard",
                "engineRestriction": None
            },
            {
                "name": "Terra Green",
                "code": "TG2026", 
                "availability": "spring only",
                "engineRestriction": "850 E-TEC Turbo R only"
            }
        ],
        "pricing": {
            "msrp": 18899.00,
            "currency": "USD",
            "market": "North America"
        },
        "metadata": {
            "extractionNotes": "Complete extraction from spec book page 8",
            "documentType": "Product Specification Book",
            "completeness": "100%"
        }
    }
    
    # Test parsing
    logger.info("Testing LLM JSON Parser...")
    success = parser.insert_llm_response(sample_llm_response)
    
    if success:
        logger.info("✅ LLM JSON Parser test successful!")
    else:
        logger.error("❌ LLM JSON Parser test failed!")


if __name__ == "__main__":
    main()