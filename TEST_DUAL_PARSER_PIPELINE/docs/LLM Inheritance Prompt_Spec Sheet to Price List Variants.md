# LLM Inheritance Prompt: Spec Sheet → Price List Variants

## System Prompt:

```
You are a product data inheritance specialist. Your task is to take a base specification sheet for a snowmobile model and intelligently inherit/populate multiple price list variants from that single specification, accounting for how different configurations, options, and packages modify the base specifications.

INHERITANCE CONCEPT: One detailed spec sheet (parent) creates multiple commercial variants (children) where each child inherits base specs but has specific modifications based on engine, track, options, and packages.

CORE PRINCIPLES:
1. Preserve all base technical specifications unless explicitly modified
2. Apply logical modifications based on engine variants, track options, and packages
3. Inherit marketing content (What's New, Package Highlights) to appropriate variants
4. Calculate weight, pricing, and performance variations intelligently
5. Handle availability restrictions (seasonal, engine-specific) properly
6. Create complete, sellable product variants ready for e-commerce

RESPONSE FORMAT: Return structured JSON with inherited product variants.
```

## Main Inheritance Prompt:

````
You are given a detailed specification sheet for a snowmobile model and a list of price variants. Your task is to create complete product records by intelligently inheriting specifications from the base spec sheet to each price variant, applying appropriate modifications.

## BASE SPECIFICATION SHEET:
```json
{
  "baseSpec": {
    "brand": "Ski-Doo",
    "model": "Rave RE",
    "modelYear": 2026,
    "category": "trail",
    "description": "Built with pure racing pedigree. Unbeatable in aggressive trail riding especially on rough trails.",
    "whatsNew": [
      "LFS-R front suspension",
      "Electric Starter standard on 850 and 600R E-TEC",
      "38 mm Ice Ripper XT studded track standard on 850 Turbo R and 850 E-TEC"
    ],
    "packageHighlights": [
      "Launch Control and E-TEC SHOT starter (850 E-TEC Turbo R only)",
      "10.25 in. touchscreen display with BRP Connect and built-in GPS",
      "High-Performance 4-piston brake caliper with adjustable brake lever",
      "Kashima coated high-performance KYB PRO 46 HLCR shocks"
    ],
    "engines": [
      {
        "name": "850 E-TEC Turbo R",
        "displacement": 849,
        "type": "2-stroke",
        "turbo": true,
        "maxRPM": 7900,
        "dryWeight": 240
      },
      {
        "name": "850 E-TEC", 
        "displacement": 849,
        "type": "2-stroke",
        "turbo": false,
        "maxRPM": 8100,
        "dryWeight": 238
      },
      {
        "name": "600R E-TEC",
        "displacement": 599,
        "type": "2-stroke", 
        "turbo": false,
        "maxRPM": 8100,
        "dryWeight": 229
      }
    ],
    "baseDimensions": {
      "length": 3040,
      "width": 1270,
      "height": 1140,
      "skiStance": 1097
    },
    "baseSuspension": {
      "front": {"type": "LFS-R", "shock": "KYB PRO 46 HLCR Kashima"},
      "rear": {"type": "PPS³", "shock": "KYB PRO 46 HLCR Kashima"}
    },
    "baseFeatures": {
      "platform": "Radien²",
      "headlights": "Premium LED",
      "seating": "Sport, 1-up",
      "handlebar": "U-type aluminium with hooks",
      "brakes": "Brembo 4-Piston with adjustable lever"
    }
  }
}
```

## PRICE LIST VARIANTS TO POPULATE:
```json
{
  "priceVariants": [
    {
      "sku": "LLTD",
      "engine": "850 E-TEC Turbo R with WIS", 
      "track": "137in 3500mm 1.5in 38mm Ice Ripper XT",
      "starter": "SHOT",
      "display": "10.25 in. Color Touchscreen Display",
      "color": "Viper Red / Black",
      "priceEuros": 25960.00
    },
    {
      "sku": "LLTE",
      "engine": "850 E-TEC Turbo R with WIS",
      "track": "137in 3500mm 1.5in 38mm Ice Ripper XT", 
      "starter": "SHOT",
      "display": "10.25 in. Color Touchscreen Display",
      "color": "Platinum Silver Satin / Black",
      "springOptions": "Black edition",
      "priceEuros": 25960.00
    },
    {
      "sku": "LUTC",
      "engine": "850 E-TEC",
      "track": "137in 3500mm 1.5in 38mm Ice Ripper XT",
      "starter": "Electric with manual rewind", 
      "display": "10.25 in. Color Touchscreen Display",
      "color": "Viper Red / Black",
      "priceEuros": 22220.00
    },
    {
      "sku": "LTTA",
      "engine": "600R E-TEC",
      "track": "129in 3300mm 1.6in 41mm Cobra",
      "starter": "Manual",
      "display": "7.2 in. Digital Display", 
      "color": "Viper Red / Black",
      "priceEuros": 18750.00
    }
  ]
}
```

## INHERITANCE RULES:

### 1. ENGINE-SPECIFIC INHERITANCE:
- **Match engine from price variant to base spec engine array**
- **Inherit engine specifications**: displacement, type, turbo, maxRPM
- **Apply engine-specific modifications**:
  - Weight: Use engine-specific dryWeight from base spec
  - Starter: Override with price variant starter type
  - Features: Apply engine-specific feature availability

### 2. TRACK-SPECIFIC INHERITANCE:
- **Parse track specifications**: "137in 3500mm 1.5in 38mm Ice Ripper XT" 
  - Length: 137 inches / 3500mm
  - Width: 1.5 inches / 38mm  
  - Type: Ice Ripper XT
- **Apply track modifications**:
  - Overall length may change with track length
  - Weight may vary with track type/size
  - Performance characteristics affected

### 3. PACKAGE/OPTION INHERITANCE:
- **Starter Systems**: SHOT vs Electric vs Manual affects features
- **Display Systems**: Touchscreen vs Digital affects connectivity features
- **Special Editions**: "Black edition" affects color options and availability

### 4. FEATURE INHERITANCE LOGIC:
```
IF engine = "850 E-TEC Turbo R" THEN
  - Include "Launch Control and E-TEC SHOT starter" in highlights
  - Set starter capability to SHOT
  - Include premium connectivity features
  
IF track contains "Ice Ripper XT" THEN  
  - Add studded track capability
  - Modify performance characteristics
  - Include track-specific features

IF display = "10.25 in. Color Touchscreen" THEN
  - Include "BRP Connect and built-in GPS"
  - Add touchscreen-specific features
  - Enhanced connectivity options
```

### 5. WEIGHT CALCULATION:
- **Base weight**: From matched engine specification
- **Track adjustment**: +/- based on track length/type
- **Option weight**: Accessories and packages modify weight

### 6. AVAILABILITY INHERITANCE:
- **Seasonal restrictions**: "Black edition" = spring only
- **Engine compatibility**: Some tracks only with specific engines  
- **Color availability**: Engine-specific color restrictions

## OUTPUT FORMAT:

Create complete product records by inheriting from base spec:

```json
{
  "inheritedProducts": [
    {
      "sku": "LLTD",
      "brand": "Ski-Doo",
      "model": "Rave RE", 
      "modelYear": 2026,
      "category": "trail",
      "description": "Built with pure racing pedigree. Unbeatable in aggressive trail riding especially on rough trails.",
      
      "inheritedSpecs": {
        "engine": {
          "name": "850 E-TEC Turbo R",
          "displacement": 849,
          "type": "2-stroke",
          "turbo": true,
          "maxRPM": 7900,
          "cooling": "liquid-cooled",
          "fuelSystem": "Electronic Direct Injection with additional booster injectors"
        },
        
        "dimensions": {
          "length": 3040,
          "width": 1270, 
          "height": 1140,
          "skiStance": 1097,
          "dryWeight": 240
        },
        
        "track": {
          "lengthInches": 137,
          "lengthMm": 3500,
          "widthInches": 1.5,
          "widthMm": 38,
          "type": "Ice Ripper XT",
          "studded": true
        },
        
        "suspension": {
          "front": {"type": "LFS-R", "shock": "KYB PRO 46 HLCR Kashima"},
          "rear": {"type": "PPS³", "shock": "KYB PRO 46 HLCR Kashima"}
        },
        
        "features": {
          "platform": "Radien²",
          "headlights": "Premium LED",
          "starter": "SHOT",
          "display": "10.25 in. Color Touchscreen Display",
          "connectivity": ["BRP Connect", "built-in GPS"],
          "brakes": "Brembo 4-Piston with adjustable lever",
          "seating": "Sport, 1-up",
          "handlebar": "U-type aluminium with hooks"
        }
      },
      
      "commercialInfo": {
        "color": "Viper Red / Black",
        "priceEuros": 25960.00,
        "availability": "standard",
        "springOptions": null
      },
      
      "inheritedMarketing": {
        "whatsNew": [
          "LFS-R front suspension",
          "Electric Starter standard on 850 and 600R E-TEC", 
          "38 mm Ice Ripper XT studded track standard on 850 Turbo R and 850 E-TEC"
        ],
        "applicableHighlights": [
          "Launch Control and E-TEC SHOT starter (850 E-TEC Turbo R only)",
          "10.25 in. touchscreen display with BRP Connect and built-in GPS",
          "High-Performance 4-piston brake caliper with adjustable brake lever",
          "Kashima coated high-performance KYB PRO 46 HLCR shocks"
        ]
      },
      
      "inheritanceNotes": {
        "engineMatch": "exact",
        "weightSource": "engine_specific", 
        "trackCompatibility": "confirmed",
        "featureModifications": ["SHOT_starter_added", "premium_display_added"]
      }
    }
  ],
  
  "inheritanceLog": {
    "successfulInheritances": 4,
    "engineMatches": 4,
    "trackCompatibilities": 4, 
    "featureConflicts": 0,
    "warnings": [
      "Manual starter on 600R E-TEC - verify electric starter availability"
    ]
  }
}
```

## CRITICAL INHERITANCE LOGIC:

### Weight Calculations:
- **Base**: Engine-specific dry weight from spec sheet
- **Track adjustment**: Longer/heavier tracks add 2-5kg
- **Option weight**: Premium features typically add 1-3kg

### Feature Availability:
- **SHOT starter**: Only available on Turbo R models
- **Touchscreen**: Available on 850+ models, digital display on 600R
- **Premium features**: Higher-end engines get more standard features

### Track Compatibility:
- **Ice Ripper XT**: Compatible with 850 engines
- **Cobra**: Typically used with 600R engines  
- **Studded tracks**: Add traction but increase weight

### Price Logic Validation:
- **Engine hierarchy**: Turbo R > 850 > 600R should reflect in pricing
- **Feature content**: Premium features justify price differences
- **Track impact**: Specialized tracks command premium pricing

## QUALITY ASSURANCE:

Before returning results, verify:
✓ All price variants successfully inherited from base spec
✓ Engine matches are accurate and complete  
✓ Track specifications properly parsed and applied
✓ Weight calculations are logical (heavier engines = more weight)
✓ Feature compatibility verified (SHOT only on Turbo R)
✓ Marketing content appropriately filtered per variant
✓ Price progression makes logical sense
✓ No missing or contradictory specifications

OUTPUT ONLY THE COMPLETE INHERITANCE JSON - NO EXPLANATORY TEXT.
````

## Key Features of This Inheritance Approach:

### **1. Smart Engine Matching**
- Matches price list engines to base spec engine array
- Inherits all technical specifications from matched engine
- Applies engine-specific features and capabilities

### **2. Intelligent Track Processing** 
- Parses track specifications from price list format
- Applies track-specific modifications to dimensions/weight
- Handles track compatibility with engines

### **3. Feature Logic Engine**
- SHOT starter only available on Turbo R engines
- Touchscreen displays on premium models
- Engine-specific feature availability

### **4. Complete Product Creation**
- Inherits all base specifications
- Applies variant-specific modifications  
- Creates sellable product records with complete specs
- Maintains traceability with inheritance notes

### **5. Marketing Content Inheritance**
- Filters "What's New" content to applicable variants
- Selects relevant package highlights per configuration
- Handles seasonal/option-specific marketing

This approach creates complete, accurate product variants by intelligently inheriting from your detailed specification sheets while respecting the commercial reality of your price list variations.