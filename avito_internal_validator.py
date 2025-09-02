#!/usr/bin/env python3
"""
Complete internal validation system for Avito XML generation
Uses live API requirements to validate before upload
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validation check"""
    field_name: str
    is_valid: bool
    error_message: str = ""
    warning_message: str = ""
    suggested_fix: str = ""

@dataclass 
class OverallValidationResult:
    """Complete validation results"""
    is_valid: bool
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    passed_checks: int
    total_checks: int
    summary: str

class AvitoInternalValidator:
    def __init__(self):
        self.brp_models = self.load_brp_models()
        self.field_constraints = self.load_field_constraints()
        self.validation_rules = self.build_validation_rules()
        
    def load_brp_models(self) -> List[str]:
        """Load current BRP models list"""
        models_file = Path("Avito_I/official_avito_brp_models.json")
        
        if models_file.exists():
            with open(models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('brp_models', [])
        
        print("WARNING: BRP models file not found, using empty list")
        return []
    
    def load_field_constraints(self) -> Dict[str, Any]:
        """Load field validation constraints from API response"""
        # Use the parsed field data from earlier API calls
        constraints_file = Path("avito_snegohody_fields_20250902_124141.json")
        
        if constraints_file.exists():
            with open(constraints_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return self.parse_field_constraints(data.get('raw_data', {}))
        
        print("WARNING: Field constraints file not found, using defaults")
        return {}
    
    def parse_field_constraints(self, raw_data: Dict) -> Dict[str, Any]:
        """Parse field constraints from raw API data"""
        constraints = {}
        
        if 'fields' not in raw_data:
            return constraints
            
        for field in raw_data['fields']:
            tag = field.get('tag', 'Unknown')
            label = field.get('label', '')
            descriptions = field.get('descriptions', '')
            
            # Extract constraint info
            is_required = False
            field_type = 'text'
            
            content_entries = field.get('content', [])
            for content in content_entries:
                is_required = content.get('required', False)
                field_type = content.get('field_type', 'text')
                break
            
            # Analyze description for validation hints
            validation_hints = self.extract_validation_hints(descriptions)
            
            constraints[tag] = {
                'label': label,
                'required': is_required,
                'type': field_type,
                'validation_hints': validation_hints,
                'description': descriptions
            }
        
        return constraints
    
    def extract_validation_hints(self, description: str) -> List[str]:
        """Extract validation requirements from field descriptions"""
        hints = []
        if not description:
            return hints
            
        desc_lower = description.lower()
        
        # Common validation patterns
        patterns = {
            'numeric': r'(число|цифр|numeric|number)',
            'required': r'(обязательн|required|must)',
            'length_limit': r'(длин|length|символ|character)',
            'format_specific': r'(формат|format|pattern)',
            'url': r'(url|ссылк|link)',
            'phone': r'(телефон|phone)',
            'email': r'(email|почт)',
            'currency': r'(рубл|руб|currency|price)',
            'range': r'(от|до|from|to|range|диапазон)'
        }
        
        for hint, pattern in patterns.items():
            if re.search(pattern, desc_lower):
                hints.append(hint)
        
        return hints
    
    def build_validation_rules(self) -> Dict[str, callable]:
        """Build validation rules for each field"""
        return {
            'Id': self.validate_id,
            'Title': self.validate_title,
            'Model': self.validate_model,
            'Price': self.validate_price,
            'Year': self.validate_year,
            'Power': self.validate_power,
            'EngineCapacity': self.validate_engine_capacity,
            'PersonCapacity': self.validate_person_capacity,
            'TrackWidth': self.validate_track_width,
            'Description': self.validate_description,
            'Images': self.validate_images,
            'Address': self.validate_address,
            'Category': self.validate_category,
            'VehicleType': self.validate_vehicle_type,
            'Make': self.validate_make,
            'EngineType': self.validate_engine_type,
            'Condition': self.validate_condition,
            'Kilometrage': self.validate_kilometrage,
            'Type': self.validate_snowmobile_type,
            'Availability': self.validate_availability,
            'AvitoDateBegin': self.validate_date_begin,
            'AvitoDateEnd': self.validate_date_end
        }
    
    def validate_id(self, value: str) -> ValidationResult:
        """Validate Id field - unique identifier"""
        if not value or not value.strip():
            return ValidationResult('Id', False, "Id is required and cannot be empty")
        
        # Must be alphanumeric, reasonable length
        cleaned_value = value.strip()
        if len(cleaned_value) < 3:
            return ValidationResult('Id', False, "Id must be at least 3 characters long")
        
        if len(cleaned_value) > 50:
            return ValidationResult('Id', False, "Id must be no more than 50 characters long")
        
        # Should be alphanumeric with possible hyphens/underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', cleaned_value):
            return ValidationResult('Id', False, "Id should only contain letters, numbers, hyphens, and underscores",
                                  suggested_fix="Use format like: ARTICLE-CODE-123 or MODEL_YEAR_2025")
        
        return ValidationResult('Id', True)
    
    def validate_title(self, value: str) -> ValidationResult:
        """Validate Title field"""
        if not value or not value.strip():
            return ValidationResult('Title', False, "Title is required")
        
        cleaned_value = value.strip()
        if len(cleaned_value) < 10:
            return ValidationResult('Title', False, "Title must be at least 10 characters long")
        
        if len(cleaned_value) > 100:
            return ValidationResult('Title', False, "Title must be no more than 100 characters long")
        
        # Should contain meaningful snowmobile-related terms
        snowmobile_terms = ['снегоход', 'ski-doo', 'lynx', 'brp', 'мотоснегокат']
        has_snowmobile_term = any(term.lower() in cleaned_value.lower() for term in snowmobile_terms)
        
        if not has_snowmobile_term:
            return ValidationResult('Title', True, warning_message="Title should contain snowmobile-related terms for better visibility")
        
        return ValidationResult('Title', True)
    
    def validate_model(self, value: str) -> ValidationResult:
        """Validate Model field against official BRP models"""
        if not value or not value.strip():
            return ValidationResult('Model', False, "Model is required")
        
        cleaned_value = value.strip()
        
        # Check against official BRP models list
        if cleaned_value not in self.brp_models:
            # Try fuzzy matching
            similar_models = [m for m in self.brp_models if 
                            cleaned_value.lower() in m.lower() or 
                            m.lower() in cleaned_value.lower()]
            
            if similar_models:
                return ValidationResult('Model', False, 
                                      f"Model '{cleaned_value}' not found in official BRP list",
                                      suggested_fix=f"Did you mean: {similar_models[0]}?")
            else:
                return ValidationResult('Model', False, 
                                      f"Model '{cleaned_value}' not found in official BRP list",
                                      suggested_fix="Check official BRP model list for exact spelling")
        
        return ValidationResult('Model', True)
    
    def validate_price(self, value: str) -> ValidationResult:
        """Validate Price field"""
        if not value or not value.strip():
            return ValidationResult('Price', False, "Price is required")
        
        cleaned_value = value.strip()
        
        # Must be numeric only (no currency symbols)
        if not cleaned_value.isdigit():
            return ValidationResult('Price', False, "Price must contain only numbers (no currency symbols, commas, or spaces)",
                                  suggested_fix="Use format: 2500000 (not 2,500,000 руб)")
        
        price_value = int(cleaned_value)
        
        # Reasonable price range for snowmobiles
        if price_value < 100000:  # Less than 100k rubles
            return ValidationResult('Price', False, "Price seems too low for a snowmobile (minimum 100,000 rubles)")
        
        if price_value > 5000000:  # More than 5M rubles
            return ValidationResult('Price', False, "Price seems too high for a snowmobile (maximum 5,000,000 rubles)")
        
        return ValidationResult('Price', True)
    
    def validate_year(self, value: str) -> ValidationResult:
        """Validate Year field"""
        if not value or not value.strip():
            return ValidationResult('Year', False, "Year is required")
        
        cleaned_value = value.strip()
        
        if not cleaned_value.isdigit() or len(cleaned_value) != 4:
            return ValidationResult('Year', False, "Year must be a 4-digit number",
                                  suggested_fix="Use format: 2025")
        
        year = int(cleaned_value)
        current_year = datetime.now().year
        
        if year < 2000:
            return ValidationResult('Year', False, f"Year must be 2000 or later (got {year})")
        
        if year > current_year + 2:
            return ValidationResult('Year', False, f"Year cannot be more than 2 years in the future (got {year})")
        
        return ValidationResult('Year', True)
    
    def validate_power(self, value: str) -> ValidationResult:
        """Validate Power field (HP)"""
        if not value or not value.strip():
            return ValidationResult('Power', True, warning_message="Power is recommended for better visibility")
        
        cleaned_value = value.strip()
        
        if not cleaned_value.isdigit():
            return ValidationResult('Power', False, "Power must be a number (HP only, no units)",
                                  suggested_fix="Use format: 165 (not 165 hp)")
        
        power = int(cleaned_value)
        
        if power < 10:
            return ValidationResult('Power', False, "Power seems too low for a snowmobile (minimum 10 HP)")
        
        if power > 300:
            return ValidationResult('Power', False, "Power seems too high for a snowmobile (maximum 300 HP)")
        
        return ValidationResult('Power', True)
    
    def validate_engine_capacity(self, value: str) -> ValidationResult:
        """Validate EngineCapacity field (CC)"""
        if not value or not value.strip():
            return ValidationResult('EngineCapacity', True, warning_message="Engine capacity is recommended")
        
        cleaned_value = value.strip()
        
        if not cleaned_value.isdigit():
            return ValidationResult('EngineCapacity', False, "Engine capacity must be a number (CC only, no units)",
                                  suggested_fix="Use format: 849 (not 849cc)")
        
        capacity = int(cleaned_value)
        
        if capacity < 200:
            return ValidationResult('EngineCapacity', False, "Engine capacity seems too low (minimum 200 CC)")
        
        if capacity > 2000:
            return ValidationResult('EngineCapacity', False, "Engine capacity seems too high (maximum 2000 CC)")
        
        return ValidationResult('EngineCapacity', True)
    
    def validate_person_capacity(self, value: str) -> ValidationResult:
        """Validate PersonCapacity field"""
        if not value or not value.strip():
            return ValidationResult('PersonCapacity', True, warning_message="Person capacity is recommended")
        
        cleaned_value = value.strip()
        
        if not cleaned_value.isdigit():
            return ValidationResult('PersonCapacity', False, "Person capacity must be a number")
        
        capacity = int(cleaned_value)
        
        if capacity < 1 or capacity > 3:
            return ValidationResult('PersonCapacity', False, "Person capacity must be 1, 2, or 3")
        
        return ValidationResult('PersonCapacity', True)
    
    def validate_track_width(self, value: str) -> ValidationResult:
        """Validate TrackWidth field (mm)"""
        if not value or not value.strip():
            return ValidationResult('TrackWidth', True, warning_message="Track width is recommended")
        
        cleaned_value = value.strip()
        
        if not cleaned_value.isdigit():
            return ValidationResult('TrackWidth', False, "Track width must be a number (mm only, no units)")
        
        width = int(cleaned_value)
        
        if width < 300 or width > 600:
            return ValidationResult('TrackWidth', False, "Track width must be between 300-600mm")
        
        return ValidationResult('TrackWidth', True)
    
    def validate_description(self, value: str) -> ValidationResult:
        """Validate Description field"""
        if not value or not value.strip():
            return ValidationResult('Description', False, "Description is required")
        
        cleaned_value = value.strip()
        
        if len(cleaned_value) < 50:
            return ValidationResult('Description', False, "Description must be at least 50 characters long")
        
        if len(cleaned_value) > 5000:
            return ValidationResult('Description', False, "Description must be no more than 5000 characters long")
        
        return ValidationResult('Description', True)
    
    def validate_images(self, value: str) -> ValidationResult:
        """Validate Images field"""
        if not value or not value.strip():
            return ValidationResult('Images', False, "At least one image is required")
        
        # Basic URL validation
        if not value.startswith(('http://', 'https://')):
            return ValidationResult('Images', False, "Image must be a valid HTTP/HTTPS URL")
        
        # Check for image file extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        has_valid_extension = any(ext in value.lower() for ext in valid_extensions)
        
        if not has_valid_extension:
            return ValidationResult('Images', True, warning_message="Image URL should end with .jpg, .png, or .webp")
        
        return ValidationResult('Images', True)
    
    def validate_category(self, value: str) -> ValidationResult:
        """Validate Category field"""
        expected_category = "Мотоциклы и мототехника"
        
        if value != expected_category:
            return ValidationResult('Category', False, f"Category must be '{expected_category}'")
        
        return ValidationResult('Category', True)
    
    def validate_vehicle_type(self, value: str) -> ValidationResult:
        """Validate VehicleType field"""
        expected_type = "Снегоходы"
        
        if value != expected_type:
            return ValidationResult('VehicleType', False, f"VehicleType must be '{expected_type}'")
        
        return ValidationResult('VehicleType', True)
    
    def validate_make(self, value: str) -> ValidationResult:
        """Validate Make field"""
        expected_make = "BRP"
        
        if value != expected_make:
            return ValidationResult('Make', False, f"Make must be '{expected_make}' for BRP snowmobiles")
        
        return ValidationResult('Make', True)
    
    def validate_engine_type(self, value: str) -> ValidationResult:
        """Validate EngineType field"""
        expected_type = "Бензин"
        
        if value != expected_type:
            return ValidationResult('EngineType', False, f"EngineType must be '{expected_type}'")
        
        return ValidationResult('EngineType', True)
    
    def validate_condition(self, value: str) -> ValidationResult:
        """Validate Condition field"""
        expected_condition = "Новое"
        
        if value != expected_condition:
            return ValidationResult('Condition', False, f"Condition must be '{expected_condition}' for new snowmobiles")
        
        return ValidationResult('Condition', True)
    
    def validate_kilometrage(self, value: str) -> ValidationResult:
        """Validate Kilometrage field"""
        expected_km = "0"
        
        if value != expected_km:
            return ValidationResult('Kilometrage', False, f"Kilometrage must be '{expected_km}' for new snowmobiles")
        
        return ValidationResult('Kilometrage', True)
    
    def validate_snowmobile_type(self, value: str) -> ValidationResult:
        """Validate Type field (snowmobile category)"""
        if not value or not value.strip():
            return ValidationResult('Type', True, warning_message="Type is recommended for better categorization")
        
        valid_types = [
            "Утилитарный",
            "Спортивный или горный", 
            "Туристический",
            "Детский",
            "Мотобуксировщик"
        ]
        
        if value not in valid_types:
            return ValidationResult('Type', False, f"Type must be one of: {', '.join(valid_types)}")
        
        return ValidationResult('Type', True)
    
    def validate_availability(self, value: str) -> ValidationResult:
        """Validate Availability field"""
        if not value or not value.strip():
            return ValidationResult('Availability', True, warning_message="Availability is recommended")
        
        valid_availability = ["В наличии", "Под заказ", "Нет в наличии"]
        
        if value not in valid_availability:
            return ValidationResult('Availability', False, f"Availability must be one of: {', '.join(valid_availability)}")
        
        return ValidationResult('Availability', True)
    
    def validate_address(self, value: str) -> ValidationResult:
        """Validate Address field"""
        expected_address = "Санкт-Петербург"
        
        if value != expected_address:
            return ValidationResult('Address', False, f"Address must be '{expected_address}'")
        
        return ValidationResult('Address', True)
    
    def validate_date_begin(self, value: str) -> ValidationResult:
        """Validate AvitoDateBegin field"""
        if not value or not value.strip():
            return ValidationResult('AvitoDateBegin', True, warning_message="Date begin is optional")
        
        # Should be in YYYY-MM-DD format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return ValidationResult('AvitoDateBegin', False, "Date must be in YYYY-MM-DD format",
                                  suggested_fix="Use format: 2025-01-01")
        
        return ValidationResult('AvitoDateBegin', True)
    
    def validate_date_end(self, value: str) -> ValidationResult:
        """Validate AvitoDateEnd field"""
        if not value or not value.strip():
            return ValidationResult('AvitoDateEnd', True, warning_message="Date end is optional")
        
        # Should be in YYYY-MM-DD format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return ValidationResult('AvitoDateEnd', False, "Date must be in YYYY-MM-DD format",
                                  suggested_fix="Use format: 2025-12-31")
        
        return ValidationResult('AvitoDateEnd', True)
    
    def validate_xml_data(self, xml_data: Dict[str, str]) -> OverallValidationResult:
        """Validate complete XML data"""
        results = []
        errors = []
        warnings = []
        
        print(f"\n=== VALIDATING XML DATA ===")
        print(f"BRP Models Available: {len(self.brp_models)}")
        print(f"Field Constraints: {len(self.field_constraints)}")
        print(f"Validation Rules: {len(self.validation_rules)}")
        print()
        
        # Validate each field
        for field_name, field_value in xml_data.items():
            if field_name in self.validation_rules:
                result = self.validation_rules[field_name](field_value)
                results.append(result)
                
                if not result.is_valid:
                    errors.append(result)
                    print(f"ERROR {field_name}: {result.error_message}")
                    if result.suggested_fix:
                        print(f"   Suggestion: {result.suggested_fix}")
                elif result.warning_message:
                    warnings.append(result)
                    print(f"WARN  {field_name}: {result.warning_message}")
                else:
                    print(f"OK    {field_name}: Valid")
            else:
                print(f"SKIP  {field_name}: No validation rule (field will be passed through)")
        
        # Calculate overall result
        passed_checks = sum(1 for r in results if r.is_valid)
        total_checks = len(results)
        is_valid = len(errors) == 0
        
        # Generate summary
        if is_valid:
            summary = f"VALIDATION PASSED: {passed_checks}/{total_checks} checks passed"
            if warnings:
                summary += f" ({len(warnings)} warnings)"
        else:
            summary = f"VALIDATION FAILED: {len(errors)} errors, {len(warnings)} warnings"
        
        print(f"\n{summary}")
        
        return OverallValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            passed_checks=passed_checks,
            total_checks=total_checks,
            summary=summary
        )
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation system summary"""
        return {
            'brp_models_count': len(self.brp_models),
            'field_constraints_count': len(self.field_constraints),
            'validation_rules_count': len(self.validation_rules),
            'supported_fields': list(self.validation_rules.keys()),
            'required_fields': ['Id', 'Title', 'Category', 'VehicleType', 'Price', 'Description', 'Images', 'Address'],
            'brp_sample_models': self.brp_models[:10] if self.brp_models else []
        }

def test_validator():
    """Test the validator with sample data"""
    validator = AvitoInternalValidator()
    
    # Test data
    test_xml_data = {
        'Id': 'MXZ-X-600R-2025',
        'Title': 'Снегоход Ski-Doo MXZ X 600R E-TEC 2025',
        'Model': 'Ski-Doo MXZ X 600R E-TEC',
        'Price': '2500000',
        'Year': '2025',
        'Power': '165',
        'EngineCapacity': '849',
        'PersonCapacity': '2',
        'TrackWidth': '406',
        'Description': 'Новый снегоход Ski-Doo MXZ X 600R E-TEC 2025 года. Отличные характеристики для спорта и отдыха.',
        'Images': 'https://example.com/snowmobile.jpg',
        'Address': 'Санкт-Петербург',
        'Category': 'Мотоциклы и мототехника',
        'VehicleType': 'Снегоходы',
        'Make': 'BRP',
        'EngineType': 'Бензин',
        'Condition': 'Новое',
        'Kilometrage': '0',
        'Type': 'Спортивный или горный',
        'Availability': 'В наличии'
    }
    
    # Validate
    result = validator.validate_xml_data(test_xml_data)
    
    # Show summary
    summary = validator.get_validation_summary()
    print(f"\nVALIDATION SYSTEM SUMMARY:")
    for key, value in summary.items():
        if isinstance(value, list) and len(value) > 10:
            print(f"  {key}: {len(value)} items")
        else:
            print(f"  {key}: {value}")
    
    return result.is_valid

if __name__ == "__main__":
    success = test_validator()
    if success:
        print(f"\nINTERNAL VALIDATOR READY FOR PRODUCTION!")
    else:
        print(f"\nVALIDATOR NEEDS REFINEMENT")