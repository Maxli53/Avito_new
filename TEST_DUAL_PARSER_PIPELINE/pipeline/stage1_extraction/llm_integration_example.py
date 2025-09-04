#!/usr/bin/env python3
"""
LLM Integration Example - How to use the LLM JSON Parser

This shows how to integrate with actual LLM API calls.
"""

from llm_json_parser import LLMJsonParser
import json

def process_llm_api_response(llm_api_response_text: str) -> bool:
    """
    Example of how to process LLM API response
    
    Args:
        llm_api_response_text: Raw text response from LLM API
        
    Returns:
        bool: Success status
    """
    parser = LLMJsonParser()
    
    try:
        # Parse the LLM response text as JSON
        # In real usage, this would come from your LLM API call
        success = parser.parse_json_string(llm_api_response_text)
        
        if success:
            print(f"Successfully processed LLM response")
            return True
        else:
            print(f"Failed to process LLM response")
            return False
            
    except Exception as e:
        print(f"Error processing LLM response: {e}")
        return False

def simulate_llm_extraction_workflow():
    """
    Simulate the complete workflow:
    1. Send PDF to LLM with prompt
    2. Receive JSON response
    3. Parse and store in database
    """
    
    print("=== LLM Extraction Workflow Simulation ===")
    
    # Step 1: This would be your actual LLM API call
    # llm_response = openai_client.chat.completions.create(
    #     model="claude-3.5-sonnet",
    #     messages=[
    #         {"role": "system", "content": LLM_PROMPT_FROM_SPEC_BOOKS_MD},
    #         {"role": "user", "content": f"Extract specifications from: {pdf_content}"}
    #     ]
    # )
    
    # Step 2: Simulated LLM response (this would be llm_response.choices[0].message.content)
    simulated_llm_response = """{
        "basicInfo": {
            "brand": "Polaris",
            "model": "RMK Pro",
            "configuration": "155",
            "category": "deep-snow",
            "modelYear": 2026,
            "description": "Ultimate mountain performance"
        },
        "marketingContent": {
            "whatsNew": ["New chassis design", "Improved suspension"],
            "packageHighlights": ["Premium shocks", "Lightweight design"],
            "springOptions": []
        },
        "engines": [
            {
                "name": "850 Patriot",
                "type": "2-stroke",
                "displacement": 850,
                "turbo": false,
                "dryWeight": 245
            }
        ],
        "weight": {"min": 245, "max": 245},
        "pricing": {"msrp": 17999.00, "currency": "USD", "market": "North America"},
        "metadata": {
            "extractionNotes": "Extracted from Polaris spec sheet",
            "documentType": "Product Specification",
            "completeness": "90%"
        }
    }"""
    
    # Step 3: Process the response
    success = process_llm_api_response(simulated_llm_response)
    
    if success:
        print("✓ Complete workflow successful!")
        
        # Verify data was stored
        parser = LLMJsonParser()
        conn = parser.sqlite3.connect(parser.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM llm_specbook_data_target_schema WHERE basic_info_brand = 'Polaris'")
        count = cursor.fetchone()[0]
        conn.close()
        
        print(f"✓ Verified: {count} Polaris record(s) in database")
        
    else:
        print("✗ Workflow failed!")

# Usage examples:
def main():
    """Main examples"""
    
    print("LLM JSON Parser - Integration Examples")
    print("=====================================")
    
    # Example 1: Direct JSON object parsing
    print("\n1. Direct JSON object parsing:")
    parser = LLMJsonParser()
    
    sample_json = {
        "basicInfo": {"brand": "Arctic Cat", "model": "M Series"},
        "engines": [{"name": "800", "displacement": 800}],
        "metadata": {"completeness": "test"}
    }
    
    parser.insert_llm_response(sample_json)
    print("✓ Direct JSON parsing complete")
    
    # Example 2: JSON string parsing (API response simulation)
    print("\n2. JSON string parsing:")
    simulate_llm_extraction_workflow()
    
    # Example 3: Show current database state
    print("\n3. Current database records:")
    conn = parser.sqlite3.connect(parser.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT basic_info_brand, basic_info_model, basic_info_configuration 
        FROM llm_specbook_data_target_schema 
        ORDER BY id
    """)
    
    records = cursor.fetchall()
    for i, (brand, model, config) in enumerate(records, 1):
        config_str = f" {config}" if config else ""
        print(f"   {i}. {brand} {model}{config_str}")
    
    conn.close()
    
    print(f"\nTotal records in LLM target schema: {len(records)}")

if __name__ == "__main__":
    main()