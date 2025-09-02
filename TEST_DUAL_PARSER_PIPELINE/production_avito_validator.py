#!/usr/bin/env python3
"""
Production Avito Validator - Mission Critical Validation System

This is the GATEKEEPER - nothing passes without validation.
No XML generation without 100% validation success.
"""

import json
import re
import requests
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from model_catalog_fetcher import ModelCatalogFetcher
import logging

# Moscow timezone
MOSCOW_TZ = timezone(timedelta(hours=3))

@dataclass
class ValidationError:
    """Critical validation error"""
    field_name: str
    error_code: str
    error_message: str
    current_value: Any
    expected_format: str = ""
    suggested_fix: str = ""

@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    validated_fields: int
    total_fields: int
    execution_time_ms: float

class CriticalValidationFailure(Exception):
    """Exception for critical validation failures"""
    pass

class ProductionAvitoValidator:
    """
    MISSION CRITICAL: Production Avito XML Validator
    
    This validator is the ONLY path to XML generation.
    If validation fails, the entire pipeline STOPS.
    """
    
    def __init__(self, credentials_path: str = "Avito_I/INTEGRATION_PACKAGE/credentials/.env"):
        """Initialize mission-critical validator"""
        
        # Setup logging
        self.setup_logging()
        
        # Load components
        self.model_fetcher = ModelCatalogFetcher()
        self.field_rules = {}
        self.credentials = self.load_credentials(credentials_path)
        self.access_token = None
        
        # Performance tracking
        self.validation_count = 0
        self.success_count = 0
        
        # Initialize with cached models
        try:
            models = self.model_fetcher.get_models()
            self.logger.info(f"Initialized with {len(models)} BRP models")
        except Exception as e:
            self.logger.critical(f"CRITICAL: Failed to load BRP models: {e}")
            raise CriticalValidationFailure("Cannot initialize validator without BRP models")
        
        self.logger.info("Production Avito Validator initialized - READY FOR VALIDATION")
    
    def setup_logging(self):
        """Setup logging for validation operations"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - AvitoValidator - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_credentials(self, path: str) -> Dict[str, str]:
        """Load API credentials"""
        credentials = {}
        env_path = Path(path)
        
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        credentials[key] = value
        
        return {
            'client_id': credentials.get('AVITO_CLIENT_ID'),
            'client_secret': credentials.get('AVITO_CLIENT_SECRET')
        }
    
    def authenticate(self) -> bool:
        """Get API access token"""
        if not self.credentials['client_id'] or not self.credentials['client_secret']:
            self.logger.error("Missing API credentials")
            return False
        
        try:
            credentials_encoded = base64.b64encode(
                f"{self.credentials['client_id']}:{self.credentials['client_secret']}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials_encoded}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {'grant_type': 'client_credentials'}
            
            response = requests.post(
                "https://api.avito.ru/token", 
                headers=headers, 
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.logger.info("API authentication successful")
                return True
            else:
                self.logger.error(f"Authentication failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def update_field_rules(self) -> bool:
        """Update field validation rules from live API"""
        
        if not self.access_token and not self.authenticate():
            self.logger.warning("Cannot update field rules - using cached rules")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                "https://api.avito.ru/autoload/v1/user-docs/node/snegohody/fields",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                fields_data = response.json()
                self.field_rules = self.parse_field_rules(fields_data)
                self.logger.info(f"Updated field rules: {len(self.field_rules)} fields")
                return True
            else:
                self.logger.warning(f"Failed to update field rules: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating field rules: {e}")
            return False
    
    def parse_field_rules(self, api_data: Dict) -> Dict[str, Any]:
        """Parse field rules from API response"""
        rules = {}
        
        if 'fields' not in api_data:
            return rules
        
        for field in api_data['fields']:
            tag = field.get('tag', 'Unknown')
            
            # Extract rule information
            is_required = False
            field_type = 'text'
            
            content_entries = field.get('content', [])
            for content in content_entries:
                is_required = content.get('required', False)
                field_type = content.get('field_type', 'text')
                break
            
            rules[tag] = {
                'required': is_required,
                'type': field_type,
                'label': field.get('label', ''),
                'description': field.get('descriptions', '')
            }
        
        return rules
    
    def validate_product_data(self, product_data: Dict[str, Any]) -> ValidationResult:
        """
        MISSION CRITICAL: Validate complete product data
        
        This is the MAIN VALIDATION ENTRY POINT.
        If this returns is_valid=False, XML generation MUST NOT proceed.
        """
        
        start_time = datetime.now()
        self.validation_count += 1
        
        self.logger.info(f"Starting validation #{self.validation_count}")
        
        errors = []
        warnings = []
        validated_fields = 0
        
        # CRITICAL VALIDATIONS - These MUST pass
        
        # 1. Required fields validation
        required_fields = ['Id', 'Title', 'Category', 'VehicleType', 'Price', 'Description', 'Images', 'Address']
        
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                errors.append(ValidationError(
                    field_name=field,
                    error_code='REQUIRED_FIELD_MISSING',
                    error_message=f'Required field {field} is missing or empty',
                    current_value=product_data.get(field),
                    expected_format='Non-empty value',
                    suggested_fix=f'Provide a value for {field}'
                ))
            else:
                validated_fields += 1
        
        # 2. Model validation (CRITICAL)
        if 'Model' in product_data:
            model_error = self.validate_model(product_data['Model'])
            if model_error:
                errors.append(model_error)
            else:
                validated_fields += 1
        
        # 3. Price validation (CRITICAL)
        if 'Price' in product_data:
            price_error = self.validate_price(product_data['Price'])
            if price_error:
                errors.append(price_error)
            else:
                validated_fields += 1
        
        # 4. Fixed values validation (CRITICAL)
        fixed_values = {
            'Category': 'Мотоциклы и мототехника',
            'VehicleType': 'Снегоходы',
            'Make': 'BRP',
            'EngineType': 'Бензин',
            'Condition': 'Новое',
            'Kilometrage': '0',
            'Address': 'Санкт-Петербург'
        }
        
        for field, expected_value in fixed_values.items():
            if field in product_data:
                if product_data[field] != expected_value:
                    errors.append(ValidationError(
                        field_name=field,
                        error_code='FIXED_VALUE_INCORRECT',
                        error_message=f'{field} must be exactly "{expected_value}"',
                        current_value=product_data[field],
                        expected_format=f'Exactly: "{expected_value}"',
                        suggested_fix=f'Set {field} to "{expected_value}"'
                    ))
                else:
                    validated_fields += 1
        
        # 5. Format validations (CRITICAL)
        format_errors = self.validate_field_formats(product_data)
        errors.extend(format_errors)
        validated_fields += len([e for e in format_errors if not e])  # Count successful validations
        
        # 6. Business rules validation
        business_errors = self.validate_business_rules(product_data)
        errors.extend(business_errors)
        
        # Calculate results
        total_fields = len(product_data)
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        is_valid = len(errors) == 0
        
        # Log results
        if is_valid:
            self.success_count += 1
            self.logger.info(f"✓ VALIDATION PASSED - {validated_fields}/{total_fields} fields validated in {execution_time:.1f}ms")
        else:
            self.logger.error(f"✗ VALIDATION FAILED - {len(errors)} errors found")
            for error in errors:
                self.logger.error(f"  {error.error_code}: {error.field_name} - {error.error_message}")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_fields=validated_fields,
            total_fields=total_fields,
            execution_time_ms=execution_time
        )
    
    def validate_model(self, model_name: str) -> Optional[ValidationError]:
        """Validate model against BRP catalog"""
        
        if not model_name or not model_name.strip():
            return ValidationError(
                field_name='Model',
                error_code='MODEL_EMPTY',
                error_message='Model field is empty',
                current_value=model_name,
                expected_format='Valid BRP model name',
                suggested_fix='Provide a valid BRP snowmobile model'
            )
        
        # Check against catalog
        if not self.model_fetcher.is_valid_model(model_name):
            similar_models = self.model_fetcher.find_similar_models(model_name, 3)
            
            return ValidationError(
                field_name='Model',
                error_code='MODEL_NOT_IN_CATALOG',
                error_message=f'Model "{model_name}" not found in Avito BRP catalog',
                current_value=model_name,
                expected_format='Exact model name from BRP catalog',
                suggested_fix=f'Try: {", ".join(similar_models)}' if similar_models else 'Check BRP model catalog'
            )
        
        return None
    
    def validate_price(self, price_value: Any) -> Optional[ValidationError]:
        """Validate price format and range"""
        
        if not price_value:
            return ValidationError(
                field_name='Price',
                error_code='PRICE_EMPTY',
                error_message='Price field is empty',
                current_value=price_value,
                expected_format='Numeric value in rubles',
                suggested_fix='Provide price in rubles (e.g., 2500000)'
            )
        
        price_str = str(price_value).strip()
        
        # Must be numeric only
        if not price_str.isdigit():
            return ValidationError(
                field_name='Price',
                error_code='PRICE_INVALID_FORMAT',
                error_message='Price must contain only numbers (no currency symbols, commas, or spaces)',
                current_value=price_value,
                expected_format='Numbers only (e.g., 2500000)',
                suggested_fix='Remove currency symbols and formatting'
            )
        
        price_int = int(price_str)
        
        # Range validation
        if price_int < 100000:
            return ValidationError(
                field_name='Price',
                error_code='PRICE_TOO_LOW',
                error_message='Price too low for a snowmobile',
                current_value=price_value,
                expected_format='Minimum 100,000 rubles',
                suggested_fix='Check price - minimum 100,000 rubles for snowmobiles'
            )
        
        if price_int > 5000000:
            return ValidationError(
                field_name='Price',
                error_code='PRICE_TOO_HIGH',
                error_message='Price too high for a snowmobile',
                current_value=price_value,
                expected_format='Maximum 5,000,000 rubles',
                suggested_fix='Check price - maximum 5,000,000 rubles for snowmobiles'
            )
        
        return None
    
    def validate_field_formats(self, product_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate field formats"""
        
        errors = []
        
        # Year validation
        if 'Year' in product_data and product_data['Year']:
            year_str = str(product_data['Year'])
            
            if not year_str.isdigit() or len(year_str) != 4:
                errors.append(ValidationError(
                    field_name='Year',
                    error_code='YEAR_INVALID_FORMAT',
                    error_message='Year must be a 4-digit number',
                    current_value=product_data['Year'],
                    expected_format='YYYY (e.g., 2025)',
                    suggested_fix='Use 4-digit year format'
                ))
            else:
                year = int(year_str)
                current_year = datetime.now().year
                
                if year < 2000 or year > current_year + 2:
                    errors.append(ValidationError(
                        field_name='Year',
                        error_code='YEAR_OUT_OF_RANGE',
                        error_message=f'Year must be between 2000 and {current_year + 2}',
                        current_value=product_data['Year'],
                        expected_format=f'2000-{current_year + 2}',
                        suggested_fix='Use valid model year'
                    ))
        
        # Power validation (if provided)
        if 'Power' in product_data and product_data['Power']:
            power_str = str(product_data['Power'])
            
            if not power_str.isdigit():
                errors.append(ValidationError(
                    field_name='Power',
                    error_code='POWER_INVALID_FORMAT',
                    error_message='Power must be numeric (HP only, no units)',
                    current_value=product_data['Power'],
                    expected_format='Number only (e.g., 165)',
                    suggested_fix='Remove "HP" or other units'
                ))
            else:
                power = int(power_str)
                if power < 10 or power > 300:
                    errors.append(ValidationError(
                        field_name='Power',
                        error_code='POWER_OUT_OF_RANGE',
                        error_message='Power must be between 10-300 HP',
                        current_value=product_data['Power'],
                        expected_format='10-300',
                        suggested_fix='Check power specification'
                    ))
        
        # Images validation
        if 'Images' in product_data and product_data['Images']:
            image_url = str(product_data['Images'])
            
            if not image_url.startswith(('http://', 'https://')):
                errors.append(ValidationError(
                    field_name='Images',
                    error_code='IMAGE_INVALID_URL',
                    error_message='Image must be a valid HTTP/HTTPS URL',
                    current_value=product_data['Images'],
                    expected_format='http://... or https://...',
                    suggested_fix='Use full URL starting with http:// or https://'
                ))
        
        return errors
    
    def validate_business_rules(self, product_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate business logic rules"""
        
        errors = []
        
        # Title should contain meaningful content
        if 'Title' in product_data and product_data['Title']:
            title = str(product_data['Title']).strip()
            
            if len(title) < 10:
                errors.append(ValidationError(
                    field_name='Title',
                    error_code='TITLE_TOO_SHORT',
                    error_message='Title must be at least 10 characters long',
                    current_value=title,
                    expected_format='At least 10 characters',
                    suggested_fix='Add more descriptive content to title'
                ))
            
            if len(title) > 100:
                errors.append(ValidationError(
                    field_name='Title',
                    error_code='TITLE_TOO_LONG',
                    error_message='Title must be no more than 100 characters long',
                    current_value=title,
                    expected_format='Maximum 100 characters',
                    suggested_fix='Shorten title to 100 characters or less'
                ))
        
        # Description validation
        if 'Description' in product_data and product_data['Description']:
            desc = str(product_data['Description']).strip()
            
            if len(desc) < 50:
                errors.append(ValidationError(
                    field_name='Description',
                    error_code='DESCRIPTION_TOO_SHORT',
                    error_message='Description must be at least 50 characters long',
                    current_value=len(desc),
                    expected_format='At least 50 characters',
                    suggested_fix='Add more product details to description'
                ))
        
        return errors
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        
        success_rate = (self.success_count / self.validation_count * 100) if self.validation_count > 0 else 0
        
        return {
            'total_validations': self.validation_count,
            'successful_validations': self.success_count,
            'failed_validations': self.validation_count - self.success_count,
            'success_rate_percent': round(success_rate, 2),
            'models_available': len(self.model_fetcher.get_models()),
            'field_rules_loaded': len(self.field_rules),
            'status': 'READY' if self.validation_count == 0 else ('HEALTHY' if success_rate > 95 else 'DEGRADED')
        }

def validate_sample_product():
    """Test the production validator with sample data"""
    
    print("=== PRODUCTION AVITO VALIDATOR TEST ===")
    
    # Initialize validator
    validator = ProductionAvitoValidator()
    
    # Test product data
    good_product = {
        'Id': 'MXZ-X-600R-2025',
        'Title': 'Снегоход Ski-Doo MXZ X 600R E-TEC 2025',
        'Category': 'Мотоциклы и мототехника',
        'VehicleType': 'Снегоходы',
        'Model': 'Ski-Doo MXZ X 600R E-TEC',
        'Make': 'BRP',
        'Price': '2500000',
        'Year': '2025',
        'Power': '165',
        'EngineCapacity': '849',
        'EngineType': 'Бензин',
        'Condition': 'Новое',
        'Kilometrage': '0',
        'Description': 'Новый снегоход Ski-Doo MXZ X 600R E-TEC 2025 года выпуска. Отличные характеристики для спорта и отдыха.',
        'Images': 'https://example.com/snowmobile.jpg',
        'Address': 'Санкт-Петербург'
    }
    
    bad_product = {
        'Id': '',  # Missing
        'Title': 'Short',  # Too short
        'Price': '2,500,000 руб',  # Wrong format
        'Model': 'Custom Snowmobile',  # Not in catalog
        'Year': '25',  # Wrong format
        'Category': 'Wrong Category'  # Wrong value
    }
    
    print("\n--- Testing VALID Product ---")
    result1 = validator.validate_product_data(good_product)
    
    print(f"Result: {'PASS' if result1.is_valid else 'FAIL'}")
    print(f"Errors: {len(result1.errors)}")
    print(f"Validated: {result1.validated_fields}/{result1.total_fields} fields")
    print(f"Time: {result1.execution_time_ms:.1f}ms")
    
    if result1.errors:
        print("Errors:")
        for error in result1.errors:
            print(f"  {error.error_code}: {error.field_name} - {error.error_message}")
    
    print("\n--- Testing INVALID Product ---")
    result2 = validator.validate_product_data(bad_product)
    
    print(f"Result: {'PASS' if result2.is_valid else 'FAIL'}")
    print(f"Errors: {len(result2.errors)}")
    print(f"Validated: {result2.validated_fields}/{result2.total_fields} fields")
    print(f"Time: {result2.execution_time_ms:.1f}ms")
    
    if result2.errors:
        print("Errors:")
        for error in result2.errors[:5]:  # Show first 5 errors
            print(f"  {error.error_code}: {error.field_name} - {error.error_message}")
            if error.suggested_fix:
                print(f"    Fix: {error.suggested_fix}")
    
    # Show stats
    stats = validator.get_validation_stats()
    print(f"\n--- Validation Statistics ---")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n=== VALIDATOR TEST COMPLETE ===")
    
    return result1.is_valid and not result2.is_valid  # Good should pass, bad should fail

if __name__ == "__main__":
    success = validate_sample_product()
    
    if success:
        print("\n🛡️ PRODUCTION VALIDATOR READY - MISSION CRITICAL VALIDATION ACTIVE")
    else:
        print("\n❌ VALIDATOR TEST FAILED")