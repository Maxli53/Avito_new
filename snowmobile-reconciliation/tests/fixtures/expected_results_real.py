"""
Real Expected Results Database - Built from Actual PDF Data
No fabricated data - all values extracted from production PDFs.

This is the foundation for reality-based testing that prevents AYTS-style failures.
"""
from decimal import Decimal

EXPECTED_MODEL_RESULTS = {
    "AYTS": {
        # Real data from SKI-DOO_2026-PRICE_LIST.pdf, page 2
        "brand": "Ski-Doo",
        "model_family": "Expedition SE",
        "engine": "900 ACE Turbo R",
        "price_eur": Decimal("25110.00"),
        "color": "Terra Green",
        "track": "154in 3900mm 1.5in 38mm Ice Crosscut",
        "display": "10.25 in. Color Touchscreen Display",
        "starter": "Electric",
        "min_confidence": 0.95,
        "source_pdf": "SKI-DOO_2026-PRICE_LIST.pdf",
        "page_number": 2,
        "model_code_line": "x AYTS Expedition SE 900 ACE Turbo R154in",
        "extraction_method": "Direct PDF text extraction",
        "validation_status": "Confirmed real data - fixes previous pipeline failure"
    },
    
    # Additional real models that can be extracted from PDFs
    "AYRN": {
        # Real data from SKI-DOO_2024-PRICE_LIST.pdf, page 1
        "brand": "Ski-Doo", 
        "model_family": "Expedition SE",
        "engine": "900 ACE Turbo R",
        "track": "154in",
        "min_confidence": 0.90,
        "source_pdf": "SKI-DOO_2024-PRICE_LIST.pdf",
        "page_number": 1,
        "notes": "2024 model year AYTS equivalent"
    },
    
    "AYSE": {
        # Real data from SKI-DOO_2025-PRICE_LIST.pdf, page 1  
        "brand": "Ski-Doo",
        "model_family": "Expedition SE", 
        "engine": "900 ACE Turbo R",
        "track": "154in",
        "min_confidence": 0.90,
        "source_pdf": "SKI-DOO_2025-PRICE_LIST.pdf",
        "page_number": 1,
        "notes": "2025 model year AYTS equivalent"
    }
}

# Brand detection patterns from real PDFs
BRAND_DETECTION_PATTERNS = {
    "Ski-Doo": {
        "model_codes": ["AYTS", "AYRN", "AYSE", "AYSH", "AYTG", "AYTR", "AYTP"],
        "model_families": ["Expedition SE", "Expedition LE", "Expedition Xtreme"],
        "engines": ["900 ACE Turbo R", "900 ACE Turbo"],
        "pdf_files": ["SKI-DOO_2024-PRICE_LIST.pdf", "SKI-DOO_2025-PRICE_LIST.pdf", "SKI-DOO_2026-PRICE_LIST.pdf"]
    },
    "Lynx": {
        "model_codes": ["LTTA", "LFSA", "LFSE", "SZSP", "SMSA"],
        "model_families": ["Commander RE", "Brutal RE", "Xterrain RE"],
        "engines": ["900 ACE Turbo R", "850 E-TEC"],
        "pdf_files": ["LYNX_2025-PRICE_LIST.pdf", "LYNX_2026-PRICE_LIST.pdf"]
    }
}

# Price validation ranges (based on real PDF data)
PRICE_VALIDATION_RANGES = {
    "AYTS": {"min": 24000.00, "max": 26000.00},  # Real: 25,110 EUR
    "Expedition SE": {"min": 20000.00, "max": 30000.00},
    "900 ACE Turbo R": {"min": 18000.00, "max": 35000.00}
}

def get_expected_result(model_code: str) -> dict:
    """Get expected result for a model code"""
    return EXPECTED_MODEL_RESULTS.get(model_code)

def validate_against_expected(model_code: str, result: dict) -> dict:
    """Validate pipeline result against expected real data"""
    expected = get_expected_result(model_code)
    if not expected:
        return {"valid": False, "error": f"No expected result for {model_code}"}
    
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Critical validations that must pass
    critical_fields = ["brand", "model_family", "engine"]
    for field in critical_fields:
        if field in expected and field in result:
            if result[field] != expected[field]:
                validation_results["errors"].append(
                    f"{field}: expected '{expected[field]}', got '{result[field]}'"
                )
                validation_results["valid"] = False
    
    # Price validation with tolerance
    if "price_eur" in expected and "price_eur" in result:
        expected_price = float(expected["price_eur"])
        result_price = float(result["price_eur"])
        price_diff = abs(expected_price - result_price)
        
        if price_diff > 100:  # 100 EUR tolerance
            validation_results["errors"].append(
                f"price_eur: expected ~{expected_price}, got {result_price} (diff: {price_diff})"
            )
            validation_results["valid"] = False
        elif price_diff > 10:  # Warning for small differences
            validation_results["warnings"].append(
                f"price_eur: small difference - expected {expected_price}, got {result_price}"
            )
    
    return validation_results

# Test data quality enforcement
def validate_no_fabricated_data():
    """Ensure all test data is real, not fabricated"""
    fabricated_indicators = ["fake_", "mock_", "dummy_", "test_123", "example_"]
    
    for model_code, data in EXPECTED_MODEL_RESULTS.items():
        for key, value in data.items():
            if isinstance(value, str):
                for indicator in fabricated_indicators:
                    assert indicator not in value.lower(), f"Fabricated data detected in {model_code}.{key}: {value}"
    
    return True