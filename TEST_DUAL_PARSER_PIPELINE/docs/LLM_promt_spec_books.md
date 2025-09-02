# Advanced LLM Prompt Template for Snowmobile Specification Extraction

## System Prompt (Critical Foundation):

```
You are an expert snowmobile specification extraction AI with deep technical knowledge of powersports vehicles. Your task is to extract comprehensive vehicle specifications from PDF documents and return them in a precise JSON structure.

CRITICAL EXTRACTION RULES:
1. Extract ONLY information explicitly present in the document - never infer or guess
2. Handle multiple engine variants within the same model (like Rave RE with 850 Turbo R, 850 E-TEC, 600R E-TEC)
3. Capture engine-specific variations (different weights, RPM, features per engine)
4. Use null for missing values - precision over completeness
5. Pay meticulous attention to units and convert as specified
6. Return ONLY valid JSON - no explanations, formatting, or additional text
7. Preserve exact technical terminology and part numbers
8. Handle seasonal/conditional availability (spring only, specific engine combinations)

RESPONSE FORMAT: Return a single, valid JSON object following the exact structure specified below.
```

## Main Extraction Prompt:

````
Extract all snowmobile specifications from the attached PDF document. This document may contain:
- Single engine models (like Summit X with 2 engine options)  
- Multi-engine models (like Rave RE with 3+ engine variants)
- Engine-specific features that vary by powerplant
- Seasonal availability restrictions
- Marketing content (What's New, Package Highlights, Spring Options)

Return the data in this exact JSON structure:

```json
{
  "basicInfo": {
    "brand": null,
    "model": null,
    "configuration": null,
    "category": null,
    "modelYear": null,
    "description": null
  },
  "marketingContent": {
    "whatsNew": [],
    "packageHighlights": [],
    "springOptions": []
  },
  "engines": [
    {
      "name": null,
      "type": null,
      "displacement": null,
      "bore": null,
      "stroke": null,
      "maxRPM": null,
      "turbo": null,
      "cooling": null,
      "fuelSystem": null,
      "carburation": null,
      "fuelType": null,
      "octaneRating": null,
      "fuelTank": null,
      "oilCapacity": null,
      "dryWeight": null,
      "dryWeightVariant": null,
      "starter": null,
      "gaugeType": null,
      "trackCompatibility": null
    }
  ],
  "weight": {
    "min": null,
    "max": null
  },
  "dimensions": {
    "overall": {
      "length": null,
      "width": null,
      "height": null
    },
    "skiStance": null,
    "fuelCapacity": null
  },
  "tracks": [
    {
      "name": null,
      "size": null,
      "dimensions": null,
      "availability": null,
      "engineCompatibility": null
    }
  ],
  "suspension": {
    "front": {
      "type": null,
      "travel": null,
      "shock": null,
      "adjustable": null
    },
    "rear": {
      "type": null,
      "travel": null,
      "shock": null,
      "adjustable": null
    },
    "center": {
      "type": null,
      "shock": null
    }
  },
  "powertrain": {
    "driveClutch": null,
    "drivenClutch": null,
    "sprocketPitch": null,
    "beltType": null,
    "reverse": null
  },
  "brakes": {
    "type": null,
    "pistons": null,
    "adjustableLever": null,
    "description": null
  },
  "features": {
    "platform": null,
    "headlights": null,
    "skis": null,
    "seating": null,
    "handlebar": null,
    "riserBlockHeight": null,
    "windshield": null,
    "visorPlug": null,
    "usb": null,
    "bumpers": null,
    "runner": null,
    "heatedGrips": null,
    "additionalFeatures": []
  },
  "colors": [
    {
      "name": null,
      "code": null,
      "availability": null,
      "engineRestriction": null
    }
  ],
  "pricing": {
    "msrp": null,
    "currency": null,
    "market": null
  },
  "metadata": {
    "extractionNotes": null,
    "documentType": null,
    "completeness": null
  }
}
```

## CRITICAL EXTRACTION INSTRUCTIONS:

### **Multi-Engine Handling (ESSENTIAL):**
- If document shows multiple engine columns (like "850 E-TEC Turbo R | 850 E-TEC | 600R E-TEC"), create separate engine objects for each
- Extract engine-specific data: different dry weights, RPM limits, starter types, gauge types
- Note which tracks work with which engines in trackCompatibility
- Capture engine-specific feature variations

### **Unit Conversion Standards:**
- **Dimensions**: Convert to millimeters (mm)
- **Weight**: Convert to kilograms (kg)  
- **Engine**: Displacement in cubic centimeters (cc)
- **Capacity**: Liters (L)
- **Speed**: km/h
- **Pressure**: Leave in original units with note in extractionNotes

### **Field-Specific Rules:**

**basicInfo.category**: 
- Use: "deep-snow", "trail", "racing", "utility", "touring", "crossover"
- Look for category indicators in headers or model positioning

**engines[].type**: 
- Use: "2-stroke" or "4-stroke" (standardized format)

**engines[].turbo**: 
- true/false/null based on "Turbo", "Turbocharged", or "T" designation

**engines[].dryWeight**: 
- If multiple weights shown (like "207 kg (154 in.) / 209 kg (165 in.)"), use first as dryWeight, second as dryWeightVariant

**weight.min/max**: 
- Calculate from all engine variants' dry weights
- If single engine with variants, use those; if multiple engines, use engine range

**tracks[].availability**: 
- Extract restrictions like "spring only", "165 in. only", "standard"
- Note seasonal limitations clearly

**colors[].availability**: 
- Capture restrictions like "spring only on 850 E-TEC", "850 E-TEC Turbo R only"
- Use engineRestriction for engine-specific color limitations

**features.gaugeType**: 
- May vary by engine (e.g., "10.25 in. touchscreen (std on 850 Turbo R) / 4.5 in. digital display")

### **Marketing Content Extraction:**

**whatsNew**: Extract from "WHAT'S NEW" section as array of strings
**packageHighlights**: Extract from "PACKAGE HIGHLIGHTS" section  
**springOptions**: Extract from "SPRING OPTIONS" section

### **Quality Control Instructions:**

1. **Verify Engine Count**: Count engine columns in specification tables
2. **Cross-Reference Data**: Ensure engine-specific data aligns with correct engine
3. **Unit Consistency**: All similar measurements should use same units
4. **Null Handling**: Use null for truly missing data, not empty strings
5. **Completeness Check**: Note in metadata.completeness if document appears incomplete

### **Common Patterns to Recognize:**

- **Multiple Engine Tables**: "ROTAX ENGINE" with multiple columns
- **Weight Variations**: Different weights per engine or track length
- **Conditional Features**: Features available only on certain engines
- **Seasonal Availability**: Spring-only colors or track lengths
- **Track Compatibility**: Specific tracks for specific engines (like "600R only")

### **Error Prevention:**

- **Don't Duplicate**: If same spec applies to all engines, don't repeat unnecessarily
- **Don't Assume**: If a field is blank in one engine column, use null, don't copy from another
- **Don't Guess Units**: If units are unclear, note in extractionNotes
- **Don't Merge**: Keep engine-specific data separate even if similar

## VALIDATION CHECKLIST:
Before returning JSON, verify:
✓ All engine variants captured as separate objects
✓ Engine-specific weights/features correctly assigned  
✓ Track compatibility noted where relevant
✓ Seasonal restrictions captured
✓ All measurements in consistent units
✓ Marketing content arrays populated
✓ No hallucinated data - only document content

## OUTPUT REQUIREMENTS:
- Return ONLY the JSON object
- NO explanatory text before or after
- NO markdown formatting around JSON
- NO truncation or "..." in arrays
- COMPLETE data extraction in single response

DO NOT OUTPUT ANYTHING OTHER THAN THE COMPLETE JSON OBJECT.
````

## Advanced Validation Prompt (Use After Extraction):

```
Review the extracted snowmobile JSON data for accuracy and completeness:

VALIDATION CHECKLIST:
1. **Engine Variants**: Are all engine options captured as separate objects?
2. **Weight Consistency**: Do min/max weights align with individual engine weights?
3. **Unit Standardization**: Are all dimensions in mm, weights in kg, displacement in cc?
4. **Engine-Specific Features**: Are starter types, gauge types correctly assigned per engine?
5. **Track Compatibility**: Are track restrictions properly noted?
6. **Seasonal Options**: Are spring-only items clearly marked?
7. **Technical Accuracy**: Do specifications make engineering sense?
8. **Completeness**: Are all major specification sections represented?

CORRECTION INSTRUCTIONS:
- Fix any unit inconsistencies
- Correct engine-specific data misalignments  
- Add missing engine variants if found
- Clarify conditional availability
- Note any data quality concerns in metadata.extractionNotes

Return either "VALIDATION_PASSED" or the corrected JSON with improvements noted in metadata.extractionNotes.
```

## Few-Shot Learning Examples:

### Example 1: Multi-Engine Model (Rave RE Pattern)
**Input Cue**: "Document shows ROTAX ENGINE table with three columns: 850 E-TEC Turbo R | 850 E-TEC | 600R E-TEC"

**Expected Structure**:
```json
{
  "engines": [
    {
      "name": "850 E-TEC Turbo R",
      "displacement": 849,
      "dryWeight": 240,
      "maxRPM": 7900,
      "starter": "SHOT",
      "gaugeType": "10.25 in. touchscreen"
    },
    {
      "name": "850 E-TEC", 
      "displacement": 849,
      "dryWeight": 238,
      "maxRPM": 8100,
      "starter": "Electric and manual",
      "gaugeType": "10.25 in. touchscreen"
    },
    {
      "name": "600R E-TEC",
      "displacement": 599.4,
      "dryWeight": 229,
      "maxRPM": 8100,
      "starter": "Electric and manual", 
      "gaugeType": "7.2 in. digital"
    }
  ],
  "weight": {"min": 229, "max": 240}
}
```

### Example 2: Single Engine with Variants (Summit X Pattern)
**Input Cue**: "Document shows two engine options with track length variations affecting weight"

**Expected Structure**:
```json
{
  "engines": [
    {
      "name": "850 E-TEC Turbo R",
      "displacement": 849,
      "dryWeight": 207,
      "dryWeightVariant": 209
    },
    {
      "name": "850 E-TEC",
      "displacement": 849, 
      "dryWeight": 199,
      "dryWeightVariant": 201
    }
  ],
  "weight": {"min": 199, "max": 209}
}
```

## Implementation Tips:

### **For API Integration:**
1. **Temperature**: Use 0.1-0.3 for consistent extraction
2. **Max Tokens**: Set to 4000+ for complete responses
3. **Model**: Claude-3.5 Sonnet or GPT-4 recommended
4. **Retry Logic**: Implement for malformed JSON responses
5. **Validation**: Always parse JSON before database insertion

### **For Batch Processing:**
1. **Consistent Prompts**: Use identical prompts for all documents
2. **Quality Sampling**: Manually verify every 10th extraction
3. **Error Logging**: Track extraction failures and patterns
4. **Progressive Enhancement**: Start with basic fields, add complexity

### **Performance Optimization:**
1. **Pre-process PDFs**: Ensure clean text extraction
2. **Chunk Large Documents**: Break into logical sections if needed  
3. **Cache Results**: Store successful extractions to avoid re-processing
4. **Parallel Processing**: Process multiple documents simultaneously

This enhanced prompt template will deliver **consistent, accurate, and comprehensive** snowmobile specification extraction that perfectly matches your unified database schema!