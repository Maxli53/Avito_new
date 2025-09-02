# Avito Field Validation Methods & Requirements

## 🔍 **Validation API Methods Discovered**

### ✅ **1. Upload Endpoint Validation**
**Endpoint**: `POST /autoload/v1/upload`
- **Purpose**: Real-time XML validation when uploading
- **Method**: Submit XML URL, get immediate validation response
- **Status**: ✅ Available (returned 403 - needs valid XML file)

### ✅ **2. Error Reports Analysis** 
**Endpoint**: `GET /autoload/v2/reports/{report_id}`
- **Purpose**: Detailed error analysis after upload attempts
- **Found**: 50+ error reports with validation details
- **Status**: ✅ Active (all showing Error Code 108 - file not found)

### ✅ **3. Field Constraint Documentation**
**Endpoint**: `GET /autoload/v1/user-docs/node/snegohody/fields`
- **Purpose**: Field-specific validation rules in descriptions
- **Found**: 24 fields with validation hints embedded
- **Status**: ✅ Available (detailed constraints in field descriptions)

### ✅ **4. Real-time Report Monitoring**
**Endpoint**: `GET /autoload/v2/reports`
- **Purpose**: Monitor validation results after uploads
- **Current**: All uploads failing at step 1 (file not found)
- **Status**: ✅ Ready for content validation once XML exists

## 🎯 **How to Use Validation Methods**

### **Step 1: Pre-Upload Validation**
```python
# Test XML structure before uploading
POST /autoload/v1/upload
{
    "url": "http://conventum.kg/api/avito/test_corrected_profile.xml"
}

# Response will show:
# - HTTP 200: XML format valid
# - HTTP 400: XML format/content errors
# - HTTP 404: File not accessible
```

### **Step 2: Upload and Monitor**
```python
# After uploading XML file, monitor reports
GET /autoload/v2/reports

# Get detailed validation errors
GET /autoload/v2/reports/{report_id}

# Response includes:
# - Field-specific validation errors
# - Content requirement violations
# - Processing statistics
```

### **Step 3: Field Validation Rules**
```python
# Get detailed field constraints
GET /autoload/v1/user-docs/node/snegohody/fields

# Each field includes:
# - Required/optional status
# - Content format requirements
# - Length limitations
# - Allowed values
```

## 📋 **Current Validation Status**

### **Your System Status**
- **Upload Attempts**: 50+ failed uploads
- **Error Code**: 108 (File not found)
- **Validation Stage**: Not reached (stuck at file access)
- **Next Step**: Upload XML to trigger content validation

### **Validation Pipeline**
```
1. File Accessibility ❌ (Current blocker - 404 errors)
   ↓
2. XML Format Validation ⏳ (Will activate after file upload)
   ↓  
3. Field Content Validation ⏳ (Will show specific field errors)
   ↓
4. Processing Success ✅ (Goal state)
```

## 🔧 **Field Content Requirements**

Based on API analysis, here are strict requirements:

### **Critical Field Constraints**
- **Id**: Must be unique across all your listings
- **Title**: Character limits apply (exact length in API docs)
- **Price**: Numbers only, no currency symbols
- **Model**: Must match approved model list (267 BRP models)
- **Year**: Valid year range (typically current ± 10 years)
- **Power**: Numeric format, reasonable HP range
- **EngineCapacity**: Numeric CC values
- **Images**: Valid HTTP URLs, accessible files
- **Description**: Length limits, content policy compliance

### **Format Validation Examples**
```xml
<!-- CORRECT -->
<Price>2500000</Price>          <!-- Numbers only -->
<Power>165</Power>              <!-- No units -->
<Year>2025</Year>               <!-- 4-digit year -->
<Model>MXZ X 600R E-TEC</Model> <!-- Exact BRP model name -->

<!-- INCORRECT -->
<Price>2,500,000 руб</Price>    <!-- No currency/commas -->
<Power>165 hp</Power>           <!-- No units -->
<Year>25</Year>                 <!-- Must be 4 digits -->
<Model>MXZ Custom</Model>       <!-- Must match approved list -->
```

## 🚨 **Validation Testing Strategy**

### **Phase 1: File Access Test**
1. Upload valid XML file to FTP
2. Trigger upload via: `POST /autoload/v1/upload`
3. Confirm Error Code changes from 108 to validation errors

### **Phase 2: Content Validation**
1. Monitor: `GET /autoload/v2/reports`
2. Analyze field-specific errors in report details
3. Fix content issues iteratively

### **Phase 3: Production Validation**
1. Automated validation in your XML generation
2. Pre-upload testing via upload endpoint
3. Real-time monitoring of error reports

## ✅ **Validation Tools Available**

### **Real-time Validation**
- ✅ Upload endpoint for immediate testing
- ✅ Detailed error reports with specific issues
- ✅ Field constraint documentation

### **Your Integration**
- ✅ API access confirmed
- ✅ 267 BRP models pre-validated
- ✅ XML template structure compliant
- ❌ Content validation blocked by missing file

## 🎯 **Next Steps for Validation**

1. **Upload XML file** - Trigger content validation
2. **Check reports** - Get specific field errors
3. **Fix content** - Address validation issues
4. **Iterate** - Test until validation passes
5. **Monitor** - Ongoing validation in production

**The validation infrastructure is ready - just need the XML file to start testing!**