# Pipeline Terminology Reference
**Snowmobile Product Data Reconciliation System**

## 🎯 Overview

This document defines the standardized terminology used throughout the snowmobile product data reconciliation pipeline. Consistent terminology is critical for developer onboarding, debugging, and system maintenance across multiple brands and years.

## 📝 Core Data Terminology

### **Model Code**
- **Definition**: 4-letter unique identifier from price lists
- **Examples**: `LTTA`, `MVTL`, `LLTE`, `UYTU`
- **Usage**: Primary key for price list entries, used in logging and debugging
- **Note**: These are cryptic codes that need to be decoded through the pipeline

### **Model** 
- **Definition**: Complete price list entry (full row with all fields)
- **Structure**: `Model Code | Malli | Paketti | Moottori | Telamatto | Käynnistin | Mittaristo | Kevätoptiot | Väri | Hinta`
- **Example**: 
  ```
  LTTA | Rave | RE | 600R E-TEC | 129in 3300mm | Manual | 7.2 in. Digital Display | (empty) | Viper Red / Black | €18,750.00
  ```
- **Usage**: The complete data object that flows through the pipeline

### **Model Family**
- **Definition**: Grouping identifier extracted from `Malli + Paketti` fields
- **Formula**: `{price_entry['malli']} {price_entry['paketti']}`
- **Examples**: 
  - `"Rave RE"` (from Rave + RE)
  - `"Backcountry X-RS"` (from Backcountry + X-RS)
  - `"Summit X"` (from Summit + X)
- **Usage**: Lookup key to find corresponding catalog sections

### **Base Model**
- **Definition**: Catalog template section containing inheritance specifications
- **Structure**: Complete specification template with available options
- **Examples**: 
  - Lynx Rave RE catalog section
  - Ski-Doo MXZ X-RS catalog section
- **Usage**: Template that Model Codes inherit from via Full Inheritance pattern

## 🔄 Pipeline Data Flow

```
Model Code → Model → Model Family → Base Model → Complete Product
    ↓           ↓          ↓            ↓             ↓
   LTTA    →  Full Row →  "Rave RE" →  Catalog  →   Final Specs
             w/ pricing              Template    w/ inheritance
```

### **Complete Flow Example**

**Input Processing:**
1. **Model Code**: `LTTA` (starting point from price list)
2. **Model**: `LTTA | Rave | RE | 600R E-TEC | 129in 3300mm | Manual | 7.2 in. Digital Display | | Viper Red / Black | €18,750.00`
3. **Model Family**: `"Rave RE"` (extracted from Malli=Rave + Paketti=RE)
4. **Base Model**: Lynx Rave RE catalog section (inheritance template with all available options)
5. **Final Product**: Complete LTTA specifications (inherited + selected + enhanced)

## 📊 Quick Reference Table

| Term | Definition | Source | Example | Pipeline Stage |
|------|------------|--------|---------|----------------|
| **Model Code** | 4-letter identifier | Price list | `LTTA`, `MVTL` | Input |
| **Model** | Complete price entry | Price list | Full row w/ specs | Processing |
| **Model Family** | Malli + Paketti | Derived | `"Rave RE"` | Matching |
| **Base Model** | Catalog template | Catalog | Rave RE section | Inheritance |

## 🏗️ Implementation Context

### **Database Schema Implications**
- `model_code VARCHAR(4)` - stores LTTA, MVTL, etc.
- `model_family VARCHAR(50)` - stores "Rave RE", "Backcountry X-RS"
- `base_model_id UUID` - references catalog base model templates

### **API Endpoint Naming**
- `GET /api/models/{model_code}` - retrieve by model code (LTTA)
- `GET /api/model-families/{family}` - retrieve by model family ("Rave RE") 
- `GET /api/base-models/{base_model_id}` - retrieve catalog template

### **Logging Standards**
```python
logger.info(f"Processing Model Code: {model_code}")
logger.info(f"Matched Model Family: {model_family}")
logger.info(f"Found Base Model: {base_model.name}")
logger.info(f"Completed Model: {final_product.sku}")
```

## 🎯 Spring Options Context

### **Spring Options Analysis**
- **Input**: `Kevätoptiot` field from Model (price list entry)
- **Examples**: `"Black edition"`, `"Studded Track"`, `"Black edition, Studded Track"`
- **Processing**: Comma-separated parsing, enhanced Claude validation
- **Impact**: Triggers deeper catalog research and specification enhancement

### **Spring Options Flow**
```
Model w/ Kevätoptiot → Parse Options → Enhanced Claude Validation → Modified Specifications
```

## 🚨 Critical Usage Notes

### **Consistency Requirements**
- **Always use these exact terms** in code, documentation, and communication
- **Never use synonyms** - stick to defined terminology
- **Database fields must match** terminology (model_code not variant_code)

### **Multi-Brand Compatibility**
- Terminology applies across **all brands**: Ski-Doo, Lynx, Sea-Doo
- Model Family patterns consistent: `{Malli} {Paketti}` formula universal
- Base Model inheritance works for any brand/year combination

### **Developer Onboarding**
- **New developers must review this document first**
- All code reviews should verify terminology consistency
- Pipeline debugging uses these terms in all logging/error messages

---

**Document Version**: 1.0  
**Last Updated**: August 30, 2025  
**Pipeline Architecture**: Full Inheritance (Option A)  
**Status**: Approved and locked for implementation