#!/usr/bin/env python3
"""
Test script for LLM JSON Parser
"""

from llm_json_parser import LLMJsonParser
import json

def test_json_string_parsing():
    """Test parsing from JSON string (simulating LLM API response)"""
    parser = LLMJsonParser()
    
    # Simulate LLM API response as JSON string
    llm_response_string = json.dumps({
        "basicInfo": {
            "brand": "Lynx",
            "model": "Rave RE",
            "configuration": "Enduro Package",
            "category": "trail",
            "modelYear": 2026,
            "description": "High-performance trail sled"
        },
        "marketingContent": {
            "whatsNew": ["LFS-R front suspension", "Electric Starter standard"],
            "packageHighlights": ["Launch Control", "10.25 in. touchscreen"],
            "springOptions": ["Black color option"]
        },
        "engines": [
            {
                "name": "850 E-TEC Turbo R",
                "type": "2-stroke", 
                "displacement": 849,
                "turbo": True,
                "dryWeight": 240
            },
            {
                "name": "600R E-TEC",
                "type": "2-stroke",
                "displacement": 599,
                "turbo": False,
                "dryWeight": 229
            }
        ],
        "weight": {"min": 229, "max": 240},
        "pricing": {"msrp": 16999.00, "currency": "USD", "market": "North America"},
        "metadata": {
            "extractionNotes": "Multi-engine model extracted successfully",
            "documentType": "Product Specification Book",
            "completeness": "95%"
        }
    })
    
    print("Testing JSON string parsing...")
    success = parser.parse_json_string(llm_response_string)
    
    if success:
        print("✅ JSON string parsing successful!")
        return True
    else:
        print("❌ JSON string parsing failed!")
        return False

if __name__ == "__main__":
    test_json_string_parsing()