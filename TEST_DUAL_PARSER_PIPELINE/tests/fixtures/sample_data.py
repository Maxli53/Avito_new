"""
Sample test data fixtures for comprehensive testing
Contains realistic snowmobile data for various test scenarios
"""

from pathlib import Path
from typing import Dict, List, Any
import json

from core import ProductData, CatalogData


class SampleDataFactory:
    """Factory for creating consistent test data"""
    
    @staticmethod
    def create_valid_products() -> List[ProductData]:
        """Create a list of valid ProductData instances"""
        return [
            ProductData(
                model_code="S1BX",
                brand="Ski-Doo",
                year=2024,
                malli="Summit X",
                paketti="Expert 165",
                moottori="850 E-TEC Turbo R",
                telamatto="3.0",
                kaynnistin="Electric",
                mittaristo="10.25\" Digital",
                vari="Octane Blue/Black"
            ),
            ProductData(
                model_code="L2RV",
                brand="Lynx",
                year=2023,
                malli="Ranger",
                paketti="RE 600R E-TEC",
                moottori="600R E-TEC",
                telamatto="2.25",
                kaynnistin="Electric",
                mittaristo="Digital",
                vari="White/Blue"
            ),
            ProductData(
                model_code="A3CT",
                brand="Arctic Cat",
                year=2024,
                malli="Catalyst",
                paketti="9000 Turbo R",
                moottori="998cc Turbo",
                telamatto="3.0",
                kaynnistin="Electric",
                mittaristo="7\" Touch",
                vari="Team Arctic Green"
            ),
            ProductData(
                model_code="P4RM",
                brand="Polaris",
                year=2023,
                malli="RMK",
                paketti="Khaos 850",
                moottori="850 Patriot",
                telamatto="2.75",
                kaynnistin="Electric",
                mittaristo="Digital Gauge",
                vari="Lime Squeeze"
            ),
            ProductData(
                model_code="Y5SW",
                brand="Yamaha",
                year=2024,
                malli="Sidewinder",
                paketti="L-TX GT",
                moottori="998 Turbo",
                telamatto="3.0",
                kaynnistin="Electric",
                mittaristo="Digital",
                vari="Team Yamaha Blue"
            )
        ]
    
    @staticmethod
    def create_invalid_products() -> List[ProductData]:
        """Create ProductData instances with various validation issues"""
        return [
            # Missing required fields
            ProductData(
                model_code="",  # Empty model code
                brand="Test Brand",
                year=2024
            ),
            # Invalid year
            ProductData(
                model_code="INVD",
                brand="Invalid",
                year=1999  # Too old
            ),
            # Wrong model code format
            ProductData(
                model_code="TOOLONG",  # More than 4 characters
                brand="Test",
                year=2024
            )
        ]
    
    @staticmethod  
    def create_catalog_data() -> List[CatalogData]:
        """Create comprehensive catalog data for matching tests"""
        return [
            CatalogData(
                model_family="Summit X",
                brand="Ski-Doo",
                specifications={
                    "engine_type": "2-stroke turbocharged",
                    "displacement": "850cc",
                    "track_width": "3.0",
                    "suspension_front": "tMotion",
                    "suspension_rear": "tMotion",
                    "fuel_capacity": "40L",
                    "dry_weight": "250kg"
                },
                features=[
                    "Rotax 850 E-TEC Turbo R Engine",
                    "10.25-inch Digital Display",
                    "Shot Start System", 
                    "Electronic Reverse",
                    "Heated Seat and Grips",
                    "Mountain Strap",
                    "Premium Sound System"
                ]
            ),
            CatalogData(
                model_family="Ranger",
                brand="Lynx",
                specifications={
                    "engine_type": "2-stroke",
                    "displacement": "600cc",
                    "track_width": "2.25", 
                    "suspension_front": "PPS+",
                    "suspension_rear": "SC-5U",
                    "fuel_capacity": "38L",
                    "dry_weight": "230kg"
                },
                features=[
                    "Rotax 600R E-TEC Engine",
                    "Digital Gauge Cluster",
                    "Electric Start",
                    "Adjustable Suspension",
                    "LED Headlights",
                    "Storage Compartment"
                ]
            ),
            CatalogData(
                model_family="Catalyst",
                brand="Arctic Cat", 
                specifications={
                    "engine_type": "2-stroke turbocharged",
                    "displacement": "998cc",
                    "track_width": "3.0",
                    "suspension_front": "AMS",
                    "suspension_rear": "ARS II",
                    "fuel_capacity": "41L", 
                    "dry_weight": "255kg"
                },
                features=[
                    "C-TEC4 998cc Turbo Engine",
                    "7-inch Touchscreen Display",
                    "Electronic Power Steering", 
                    "Lightweight Chassis",
                    "Mountain Performance Package",
                    "Heated Seat and Grips"
                ]
            ),
            CatalogData(
                model_family="RMK",
                brand="Polaris",
                specifications={
                    "engine_type": "4-stroke",
                    "displacement": "850cc", 
                    "track_width": "2.75",
                    "suspension_front": "Walker Evans",
                    "suspension_rear": "Walker Evans", 
                    "fuel_capacity": "42L",
                    "dry_weight": "245kg"
                },
                features=[
                    "Patriot 850 Engine",
                    "AXYS Mountain Chassis",
                    "BOOST Technology",
                    "Digital Display",
                    "Electric Start",
                    "Mountain-specific Track"
                ]
            ),
            CatalogData(
                model_family="Sidewinder",
                brand="Yamaha",
                specifications={
                    "engine_type": "4-stroke turbocharged",
                    "displacement": "998cc",
                    "track_width": "3.0",
                    "suspension_front": "KYB",
                    "suspension_rear": "FOX QS3",
                    "fuel_capacity": "40L",
                    "dry_weight": "265kg"
                },
                features=[
                    "Genesis 998 Turbo Engine", 
                    "Digital Multi-Information Display",
                    "Electric Start",
                    "Yamaha Connect X App",
                    "Heated Seat and Grips",
                    "Premium Suspension"
                ]
            )
        ]
    
    @staticmethod
    def create_edge_case_products() -> List[ProductData]:
        """Create products that test edge cases and boundary conditions"""
        return [
            # Minimum valid data
            ProductData(
                model_code="MIN1",
                brand="Min",
                year=2020  # Minimum valid year
            ),
            # Maximum field lengths
            ProductData(
                model_code="MAX1",
                brand="Very Long Brand Name That Tests Maximum Length Handling",
                year=2025,  # Future year
                malli="Extra Long Model Name With Many Details",
                paketti="Complete Package Description With All Options"
            ),
            # Special characters
            ProductData(
                model_code="SP3C",
                brand="Brand-Name",
                year=2024,
                malli="Model/Name",
                vari="Color & Accents"
            ),
            # Non-standard formatting
            ProductData(
                model_code="NS4T",
                brand="lowercase brand",
                year=2024,
                malli="UPPERCASE MODEL",
                moottori="mixed Case Engine"
            )
        ]
    
    @staticmethod
    def create_matching_test_scenarios() -> Dict[str, Any]:
        """Create test scenarios for semantic matching validation"""
        return {
            "exact_matches": [
                ("Summit X Expert 165", "Summit X"),
                ("Ranger RE 600R E-TEC", "Ranger"),
                ("Catalyst 9000 Turbo R", "Catalyst")
            ],
            "partial_matches": [
                ("Summit SP 850", "Summit X"),  # Should match with lower confidence
                ("Catalyst Alpha One", "Catalyst"),  # Different variant
                ("RMK Pro", "RMK")  # Missing specification
            ],
            "no_matches": [
                ("Completely Different Model", None),
                ("Random Text", None),
                ("123456789", None)
            ],
            "ambiguous_matches": [
                ("Summit", ["Summit X", "Summit SP"]),  # Multiple possible matches
                ("RMK", ["RMK Khaos", "RMK Pro"])  # Could match multiple variants
            ]
        }
    
    @staticmethod
    def create_validation_test_cases() -> Dict[str, List[Dict[str, Any]]]:
        """Create comprehensive validation test cases"""
        return {
            "valid_cases": [
                {
                    "product": ProductData(model_code="VAL1", brand="Valid", year=2024),
                    "expected_confidence": 1.0,
                    "expected_errors": []
                },
                {
                    "product": ProductData(
                        model_code="VAL2", 
                        brand="Complete", 
                        year=2023,
                        malli="Full Model",
                        moottori="Full Engine"
                    ),
                    "expected_confidence": 1.0,
                    "expected_errors": []
                }
            ],
            "invalid_cases": [
                {
                    "product": ProductData(model_code="", brand="Empty Code", year=2024),
                    "expected_confidence": 0.0,
                    "expected_errors": ["Empty model code"]
                },
                {
                    "product": ProductData(model_code="OLD1", brand="Old", year=1999),
                    "expected_confidence": 0.3,
                    "expected_errors": ["Year too old"]
                }
            ],
            "warning_cases": [
                {
                    "product": ProductData(model_code="WARN", brand="Warning", year=2024),
                    "expected_confidence": 0.8,
                    "expected_warnings": ["Missing engine specification"]
                }
            ]
        }
    
    @staticmethod
    def create_xml_test_data() -> Dict[str, str]:
        """Create expected XML outputs for generation testing"""
        return {
            "basic_product": '''<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Ski-Doo Summit X 2024</title>
    <model_code>S1BX</model_code>
    <brand>Ski-Doo</brand>
    <year>2024</year>
    <description>Model: Summit X Expert 165
Engine: 850 E-TEC Turbo R
Track: 3.0
Starter: Electric
Gauge: 10.25" Digital
Color: Octane Blue/Black</description>
</item>''',
            "minimal_product": '''<?xml version="1.0" encoding="UTF-8"?>
<item>
    <title>Min MIN1 2020</title>
    <model_code>MIN1</model_code>
    <brand>Min</brand>
    <year>2020</year>
    <description>Model Code: MIN1</description>
</item>'''
        }
    
    @staticmethod
    def save_sample_data_to_files(output_dir: Path):
        """Save sample data to JSON files for external testing"""
        output_dir.mkdir(exist_ok=True, parents=True)
        
        data = {
            "valid_products": [p.__dict__ for p in SampleDataFactory.create_valid_products()],
            "invalid_products": [p.__dict__ for p in SampleDataFactory.create_invalid_products()],
            "catalog_data": [c.__dict__ for c in SampleDataFactory.create_catalog_data()],
            "edge_cases": [p.__dict__ for p in SampleDataFactory.create_edge_case_products()],
            "matching_scenarios": SampleDataFactory.create_matching_test_scenarios(),
            "validation_cases": SampleDataFactory.create_validation_test_cases(),
            "xml_examples": SampleDataFactory.create_xml_test_data()
        }
        
        # Save each dataset to separate files
        for filename, dataset in data.items():
            file_path = output_dir / f"{filename}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, default=str)
    
    @staticmethod
    def load_real_pdf_samples() -> List[Path]:
        """Get paths to real PDF samples for integration testing"""
        # This would be configured to point to actual test PDF files
        sample_dir = Path("tests/data/pdf_samples")
        if sample_dir.exists():
            return list(sample_dir.glob("*.pdf"))
        return []


# Global instance for easy access
sample_data_factory = SampleDataFactory()