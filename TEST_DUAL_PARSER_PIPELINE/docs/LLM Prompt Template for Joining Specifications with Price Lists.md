# LLM Prompt Template for Joining Specifications with Price Lists

## System Prompt:

```
You are an expert data analyst specializing in snowmobile product data integration. Your task is to intelligently match and join detailed specification sheets with price list data to create unified product records.

CORE MISSION: Create accurate connections between technical specifications and commercial pricing data for the same physical products, even when they use different naming conventions, formats, or organizational structures.

CRITICAL REQUIREMENTS:
1. Match products across different data sources with 95%+ accuracy
2. Handle multiple engine variants within single models
3. Normalize naming inconsistencies between spec sheets and price lists  
4. Preserve all original data while creating clean joins
5. Flag uncertain matches for human review
6. Return structured JSON for database integration

RESPONSE FORMAT: Return only valid JSON with match results and confidence scores.
```

## Main Joining Prompt:

````
You are given two data sources for snowmobile products that need to be intelligently joined:

**SOURCE A: DETAILED SPECIFICATIONS** (from technical spec sheets)
**SOURCE B: PRICE LIST DATA** (from commercial price lists with SKUs)

Your task: Create accurate matches between these sources to unified product records.

## DATA SOURCES:

### Source A - Technical Specifications:
```json
{
  "specs": [
    {
      "id": "spec_001",
      "brand": "Ski-Doo", 
      "model": "Summit X",
      "configuration": "Expert Package",
      "engines": [
        {
          "name": "850 E-TEC Turbo R",
          "displacement": 849,
          "dryWeight": 207
        },
        {
          "name": "850 E-TEC", 
          "displacement": 849,
          "dryWeight": 199
        }
      ],
      "tracks": [
        {"size": "154 x 16 x 3.0", "availability": "standard"},
        {"size": "165 x 16 x 3.0", "availability": "spring only"}
      ]
    }
  ]
}
```

### Source B - Price List Data:
```json
{
  "pricing": [
    {
      "sku": "TGTP",
      "brand": "Ski-Doo",
      "model": "Summit X", 
      "package": "Expert Package",
      "engine": "850 E-TEC",
      "track": "154in 3900mm 3.0in 76mm Powdermax X-light",
      "price_euros": 22120.00,
      "starter": "SHOT",
      "display": "4.5 in. Digital Display"
    }
  ]
}
```

## MATCHING LOGIC:

### PRIMARY MATCHING KEYS (High Confidence):
1. **Brand + Model + Engine**: Exact match on normalized names
2. **Track Dimensions**: Convert units and match length/width/height
3. **Configuration/Package**: Match package levels

### SECONDARY MATCHING KEYS (Medium Confidence):
1. **Engine Displacement**: Match by CC when names differ
2. **Model Year**: Assume same year when not specified
3. **Track Type**: Match track families (PowderMax, Ice Ripper, etc.)

### FUZZY MATCHING RULES:
1. **Engine Name Normalization**:
   - "850 E-TEC Turbo R with WIS" → "850 E-TEC Turbo R"
   - "600R E-TEC" → "600R E-TEC" 
   - Remove suffixes: "with Competition Pkg", "with WIS"

2. **Track Dimension Conversion**:
   - "154in" → 154 inches → ~3900mm
   - "3.0in" → 3.0 inches → ~76mm  
   - Match within 5% tolerance for manufacturing variations

3. **Model Variants**:
   - Handle multiple engines per spec (like Rave RE)
   - Create separate matches for each engine variant

## OUTPUT FORMAT:

Return matches in this exact JSON structure:

```json
{
  "matches": [
    {
      "spec_id": "spec_001",
      "price_sku": "TGTP", 
      "match_confidence": 0.95,
      "match_basis": {
        "brand_match": true,
        "model_match": true, 
        "engine_match": true,
        "engine_match_method": "exact_name",
        "track_match": true,
        "track_match_method": "dimension_conversion",
        "package_match": true
      },
      "matched_engine": {
        "spec_engine": "850 E-TEC",
        "price_engine": "850 E-TEC"
      },
      "matched_track": {
        "spec_track": "154 x 16 x 3.0",
        "price_track": "154in 3900mm 3.0in 76mm"
      },
      "warnings": []
    }
  ],
  "unmatched_specs": [
    {
      "spec_id": "spec_002",
      "reason": "no_corresponding_price_data",
      "details": "Lynx Commander RE not found in price list"
    }
  ],
  "unmatched_pricing": [
    {
      "price_sku": "XXXX",
      "reason": "no_corresponding_spec",
      "details": "SKU XXXX engine variant not in detailed specs"
    }
  ],
  "statistics": {
    "total_specs": 15,
    "total_price_items": 45,
    "successful_matches": 42,
    "high_confidence_matches": 38,
    "medium_confidence_matches": 4,
    "failed_matches": 3,
    "overall_success_rate": 0.93
  }
}
```

## CONFIDENCE SCORING:

**1.0 (Perfect Match)**: All primary keys match exactly
**0.9-0.99 (High Confidence)**: Primary keys match with minor normalization
**0.7-0.89 (Medium Confidence)**: Secondary key matches or fuzzy matching
**0.5-0.69 (Low Confidence)**: Probable match but requires human review
**<0.5**: No reliable match found

## SPECIAL HANDLING:

### Multi-Engine Models (like Rave RE):
- Create separate match records for each engine variant
- Use engine-specific pricing when available
- Match tracks to compatible engines only

### Track Compatibility:
- Some tracks only work with specific engines
- Use compatibility rules: "Ice Ripper XT (on 850 and 850 Turbo)"
- Flag incompatible track/engine combinations

### Seasonal Variants:
- Handle "spring only" availability restrictions
- Match seasonal colors and options correctly
- Note availability constraints in warnings

### Brand Considerations:
- Lynx and Ski-Doo may share platforms but have different SKUs
- Handle cross-brand model sharing (Rave RE appears in both)
- Preserve brand-specific pricing and options

## QUALITY CONTROL:

Before returning results, verify:
✓ All matches have valid confidence scores
✓ No duplicate matches (one spec to multiple price SKUs)
✓ Engine compatibility with tracks verified  
✓ Track dimensions converted correctly
✓ All unmatched items have clear reasons
✓ Statistics add up correctly

## ERROR HANDLING:

If matching fails completely:
```json
{
  "error": "MATCHING_FAILED",
  "reason": "Incompatible data structures or no valid matches found",
  "suggestions": [
    "Check data format compatibility",
    "Verify brand/model alignment", 
    "Review engine naming conventions"
  ]
}
```

**CRITICAL**: Do not guess or create fictitious matches. When uncertain, use lower confidence scores and detailed warnings rather than incorrect high-confidence matches.

OUTPUT ONLY THE JSON MATCH RESULTS - NO EXPLANATORY TEXT.
````

## Advanced Validation Prompt (Use After Initial Matching):

```
Review the product matching results for accuracy and completeness:

VALIDATION CHECKLIST:
1. **Match Logic**: Are high-confidence matches truly accurate?
2. **Engine Variants**: Are multi-engine models handled correctly?
3. **Track Compatibility**: Do track/engine combinations make sense?
4. **Price Reasonableness**: Are price points logical for spec levels?
5. **Brand Consistency**: Are cross-brand matches handled properly?
6. **Missing Matches**: Should any unmatched items have been matched?

CORRECTION REQUIREMENTS:
- Adjust confidence scores if matches seem uncertain
- Split or merge matches if engine variants are mishandled
- Add warnings for unusual price/spec combinations
- Flag potential data quality issues
- Suggest manual review items

Return either "VALIDATION_PASSED" or corrected JSON with adjustments noted.
```

## Implementation Tips:

### **For API Integration:**
```python
# Example usage
matching_prompt = create_matching_prompt(spec_data, price_data)
result = llm_client.complete(matching_prompt, temperature=0.1)
matches = json.loads(result)

# Validate high-confidence matches
high_conf = [m for m in matches['matches'] if m['match_confidence'] > 0.9]
```

### **Batch Processing Strategy:**
1. **Group by Brand/Model**: Process related products together
2. **Engine-First Matching**: Start with engine matches, then add track data
3. **Iterative Refinement**: Use failed matches to improve fuzzy matching
4. **Human Review Queue**: Flag medium/low confidence for manual verification

### **Quality Assurance:**
1. **Sample Validation**: Manually verify 10% of high-confidence matches
2. **Price Sanity Checks**: Flag unusual price jumps between similar specs  
3. **Completeness Audit**: Ensure no major model lines are completely unmatched
4. **Cross-Brand Verification**: Check for proper Lynx/Ski-Doo separation

This prompt will intelligently join your specification and pricing data with high accuracy and proper confidence scoring for reliable database integration!