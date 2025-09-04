#!/usr/bin/env python3
"""
LLM Specbook Data Inserter
Production tool for inserting LLM-extracted snowmobile specification data
into the llm_specbook_data_target_schema table.

Usage:
    from specbook_data_inserter import insert_specbook_data
    insert_specbook_data(json_data, 'dual_db.db')
"""
import sqlite3
import json
import os

# Example JSON data structure for reference
json_data = {
    "basicInfo": {
        "brand": "Ski-Doo",
        "model": "Summit X with Expert Package",
        "configuration": "Deep Snow",
        "category": "deep-snow",
        "modelYear": 2026,
        "description": "The ultimate precise and predictable deep-snow sled with features sharpened for most technical terrains"
    },
    "marketingContent": {
        "whatsNew": [
            "REV Gen5 Lightweight platform",
            "813 mm (32 in.) ski stance",
            "Twin link steering",
            "Super-short tunnel and radiator",
            "Improved Pilot DS 4 skis"
        ],
        "packageHighlights": [
            "Premium LED headlights",
            "RAS 3 front suspension with 813 mm (32 in.) ski stance",
            "tMotion XT rear suspension with rigid rear arm",
            "PowderMax X-Light 3 in. track with full-width rods",
            "E-TEC SHOT starter standard",
            "Ultra compact and lightweight deep snow seat",
            "10.25 in. touchscreen display with BRP Connect and built-in GPS"
        ],
        "springOptions": [
            "Monument Grey color (850 E-TEC)",
            "Terra Green (850 E-TEC Turbo R)",
            "165\" track length"
        ]
    },
    "engines": [
        {
            "name": "850 E-TEC Turbo R",
            "type": "2-stroke",
            "displacement": 849,
            "bore": 82,
            "stroke": 80.4,
            "maxRPM": None,
            "turbo": True,
            "cooling": "Liquid-cooled",
            "fuelSystem": "E-TEC direct injection with additional booster injectors",
            "carburation": None,
            "fuelType": "Premium unleaded",
            "octaneRating": 95,
            "fuelTank": 36,
            "oilCapacity": 3.4,
            "dryWeight": 207,
            "dryWeightVariant": 209,
            "starter": "E-TEC SHOT Starter",
            "gaugeType": "10.25 in. touchscreen display",
            "trackCompatibility": "154 in. and 165 in. available"
        },
        {
            "name": "850 E-TEC",
            "type": "2-stroke",
            "displacement": 849,
            "bore": 82,
            "stroke": 80.4,
            "maxRPM": None,
            "turbo": False,
            "cooling": "Liquid-cooled",
            "fuelSystem": "E-TEC direct injection with additional booster injectors",
            "carburation": None,
            "fuelType": "Premium unleaded",
            "octaneRating": 95,
            "fuelTank": 36,
            "oilCapacity": 3.4,
            "dryWeight": 199,
            "dryWeightVariant": 201,
            "starter": "E-TEC SHOT Starter",
            "gaugeType": "4.5 in. digital display",
            "trackCompatibility": "154 in. and 165 in. available"
        }
    ],
    "weight": {
        "min": 199,
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
            "dimensions": "154 x 16 x 3.0 in",
            "availability": "standard",
            "engineCompatibility": "both engines"
        },
        {
            "name": "PowderMax X-Light",
            "size": "165 x 16 x 3.0",
            "dimensions": "165 x 16 x 3.0 in",
            "availability": "spring only",
            "engineCompatibility": "both engines"
        }
    ],
    "suspension": {
        "front": {
            "type": "RAS 3",
            "travel": 207,
            "shock": "KYB PRO 36 EA-3",
            "adjustable": None
        },
        "rear": {
            "type": "tMotion XT with rigid rear arm",
            "travel": 264,
            "shock": "KYB PRO 36 EA-3",
            "adjustable": None
        },
        "center": {
            "type": "tMotion XT",
            "shock": "KYB 36 Plus"
        }
    },
    "powertrain": {
        "driveClutch": "pDrive with clickers",
        "drivenClutch": "QRS Vent Plus",
        "sprocketPitch": 89,
        "beltType": None,
        "reverse": "RER"
    },
    "brakes": {
        "type": "Brembo",
        "pistons": None,
        "adjustableLever": True,
        "description": "Brembo with adjustable lever"
    },
    "features": {
        "platform": "REV Gen5",
        "headlights": "Premium LED",
        "skis": "Pilot DS 4",
        "seating": "Deep snow ultra compact",
        "handlebar": "Tapered with J-hooks / Grab handle / Flexible handguards",
        "riserBlockHeight": 120,
        "windshield": None,
        "visorPlug": None,
        "usb": None,
        "bumpers": "Standard / Standard",
        "runner": "3/8 square – 4",
        "heatedGrips": True,
        "additionalFeatures": [
            "Premium LED headlights",
            "Ultra compact deep snow seat",
            "Heated throttle lever/grips"
        ]
    },
    "colors": [
        {
            "name": "Monument Grey",
            "code": None,
            "availability": "spring only",
            "engineRestriction": "850 E-TEC only"
        },
        {
            "name": "Timeless Black",
            "code": None,
            "availability": "standard",
            "engineRestriction": None
        },
        {
            "name": "Terra Green",
            "code": None,
            "availability": "spring only",
            "engineRestriction": "850 E-TEC Turbo R only"
        }
    ],
    "pricing": {
        "msrp": None,
        "currency": None,
        "market": None
    },
    "metadata": {
        "extractionNotes": "Extracted from Ski-Doo 2026 Product Spec Book, Summit X with Expert Package model specifications",
        "documentType": "Product Specification Manual",
        "completeness": "High - comprehensive technical specifications available"
    }
}

def insert_specbook_data(json_data, database_path='../../dual_db.db'):
    """
    Insert LLM-extracted snowmobile specification data into database.
    
    Args:
        json_data (dict): Complete JSON data following LLM prompt structure
        database_path (str): Path to SQLite database file
        
    Returns:
        int: Record ID of inserted data
    """
    if not os.path.exists(database_path):
        raise FileNotFoundError(f"Database not found: {database_path}")
        
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Prepare the insert statement with ALL columns (excluding id, created_at, updated_at)
    insert_sql = """
    INSERT INTO llm_specbook_data_target_schema (
        basic_info_brand,
        basic_info_model,
        basic_info_configuration,
        basic_info_category,
        basic_info_model_year,
        basic_info_description,
        marketing_content_whats_new,
        marketing_content_package_highlights,
        marketing_content_spring_options,
        engines,
        weight_min,
        weight_max,
        dimensions_overall_length,
        dimensions_overall_width,
        dimensions_overall_height,
        dimensions_ski_stance,
        dimensions_fuel_capacity,
        tracks,
        suspension_front_type,
        suspension_front_travel,
        suspension_front_shock,
        suspension_front_adjustable,
        suspension_rear_type,
        suspension_rear_travel,
        suspension_rear_shock,
        suspension_rear_adjustable,
        suspension_center_type,
        suspension_center_shock,
        powertrain_drive_clutch,
        powertrain_driven_clutch,
        powertrain_sprocket_pitch,
        powertrain_belt_type,
        powertrain_reverse,
        brakes_type,
        brakes_pistons,
        brakes_adjustable_lever,
        brakes_description,
        features_platform,
        features_headlights,
        features_skis,
        features_seating,
        features_handlebar,
        features_riser_block_height,
        features_windshield,
        features_visor_plug,
        features_usb,
        features_bumpers,
        features_runner,
        features_heated_grips,
        features_additional_features,
        colors,
        pricing_msrp,
        pricing_currency,
        pricing_market,
        metadata_extraction_notes,
        metadata_document_type,
        metadata_completeness,
        full_llm_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Prepare the values
    values = (
        json_data["basicInfo"]["brand"],
        json_data["basicInfo"]["model"],
        json_data["basicInfo"]["configuration"],
        json_data["basicInfo"]["category"],
        json_data["basicInfo"]["modelYear"],
        json_data["basicInfo"]["description"],
        json.dumps(json_data["marketingContent"]["whatsNew"]),
        json.dumps(json_data["marketingContent"]["packageHighlights"]),
        json.dumps(json_data["marketingContent"]["springOptions"]),
        json.dumps(json_data["engines"]),
        json_data["weight"]["min"],
        json_data["weight"]["max"],
        json_data["dimensions"]["overall"]["length"],
        json_data["dimensions"]["overall"]["width"],
        json_data["dimensions"]["overall"]["height"],
        json_data["dimensions"]["skiStance"],
        json_data["dimensions"]["fuelCapacity"],
        json.dumps(json_data["tracks"]),
        json_data["suspension"]["front"]["type"],
        json_data["suspension"]["front"]["travel"],
        json_data["suspension"]["front"]["shock"],
        json_data["suspension"]["front"]["adjustable"],  # Added missing field
        json_data["suspension"]["rear"]["type"],
        json_data["suspension"]["rear"]["travel"],
        json_data["suspension"]["rear"]["shock"],
        json_data["suspension"]["rear"]["adjustable"],   # Added missing field
        json_data["suspension"]["center"]["type"],
        json_data["suspension"]["center"]["shock"],
        json_data["powertrain"]["driveClutch"],
        json_data["powertrain"]["drivenClutch"],
        json_data["powertrain"]["sprocketPitch"],
        json_data["powertrain"]["beltType"],             # Added missing field
        json_data["powertrain"]["reverse"],
        json_data["brakes"]["type"],
        json_data["brakes"]["pistons"],                  # Added missing field
        json_data["brakes"]["adjustableLever"],
        json_data["brakes"]["description"],
        json_data["features"]["platform"],
        json_data["features"]["headlights"],
        json_data["features"]["skis"],
        json_data["features"]["seating"],
        json_data["features"]["handlebar"],
        json_data["features"]["riserBlockHeight"],
        json_data["features"]["windshield"],
        json_data["features"]["visorPlug"],              # Added missing field
        json_data["features"]["usb"],                    # Added missing field
        json_data["features"]["bumpers"],
        json_data["features"]["runner"],
        json_data["features"]["heatedGrips"],
        json.dumps(json_data["features"]["additionalFeatures"]),
        json.dumps(json_data["colors"]),
        json_data["pricing"]["msrp"],                    # Added missing field
        json_data["pricing"]["currency"],               # Added missing field
        json_data["pricing"]["market"],                 # Added missing field
        json_data["metadata"]["extractionNotes"],
        json_data["metadata"]["documentType"],
        json_data["metadata"]["completeness"],
        json.dumps(json_data, indent=2)
    )
    
    cursor.execute(insert_sql, values)
    conn.commit()
    
    record_id = cursor.lastrowid
    
    # Verify the insert
    cursor.execute("SELECT basic_info_model, basic_info_brand, basic_info_model_year FROM llm_specbook_data_target_schema WHERE id = ?", (record_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    print(f"Successfully inserted: {result[0]} ({result[1]} {result[2]})")
    print(f"Record ID: {record_id}")
    
    return record_id

# Example usage for testing
if __name__ == "__main__":
    # Insert the example data
    record_id = insert_specbook_data(json_data)
    print(f"Inserted record with ID: {record_id}")