# Avito Snowmobile Pipeline Architecture

## 🎯 **Mission-Critical Components**

### **1. Internal Validation System (CRITICAL)**
- **Purpose**: Prevent invalid XML from ever reaching Avito
- **Uptime Requirement**: 99.99% (must always be available)
- **Performance**: <0.1 second validation time
- **Failure Mode**: If validation fails, STOP pipeline

## 📐 **Core Pipeline Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                             │
├───────────────┬──────────────┬───────────────────────────────┤
│ BRP Product   │ Live Avito   │ Model Catalog XML             │
│ Database      │ Field API    │ (Cached Daily)                │
└───────┬───────┴──────┬───────┴───────────┬──────────────────┘
        │              │                   │
        ▼              ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│              VALIDATION LAYER (MISSION CRITICAL)            │
├─────────────────────────────────────────────────────────────┤
│ • Field Format Validation (Live API Rules)                  │
│ • Model Validation (Cached Catalog)                         │
│ • Business Rules (Price, Year, etc.)                        │
│ • Required Field Checks                                     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼ (Only if 100% valid)
┌─────────────────────────────────────────────────────────────┐
│                    XML GENERATION                            │
├─────────────────────────────────────────────────────────────┤
│ • Use main_template.xml structure                           │
│ • Apply validated data                                      │
│ • Generate complete XML file                                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FTP UPLOAD                                │
├─────────────────────────────────────────────────────────────┤
│ • Upload to: /test_corrected_profile.xml                    │
│ • Server: 176.126.165.67                                    │
│ • Verify upload success                                     │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                 AVITO PROCESSING                             │
├─────────────────────────────────────────────────────────────┤
│ • Avito fetches XML (3x daily: 03:00, 11:00, 19:00 MSK)    │
│ • Processing validation                                      │
│ • Listing publication                                       │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 **Pipeline Components**

### **1. Data Sources**

#### **BRP Product Database**
```python
# Snowmobile product data
{
    'article_code': 'MXZ-X-600R-2025',
    'model': 'Ski-Doo MXZ X 600R E-TEC',
    'year': 2025,
    'price_rub': 2500000,
    'specifications': {...}
}
```

#### **Live Avito Field API**
```python
# Endpoint for field validation rules
GET /autoload/v1/user-docs/node/snegohody/fields

# Returns field constraints, formats, requirements
{
    'fields': [
        {
            'tag': 'Price',
            'required': true,
            'type': 'numeric',
            'validation': 'numbers only, no currency'
        }
    ]
}
```

#### **Model Catalog XML (Cached)**
```python
# Source: https://www.avito.ru/web/1/catalogs/content/feed/snegohod.xml
# Update frequency: Daily at 02:00 MSK
# Contains: 267+ BRP snowmobile models
# Cache location: ./cache/models/snegohod_models.xml
```

### **2. Validation Layer (MISSION CRITICAL)**

#### **Validation Pipeline**
```python
class AvitoValidationPipeline:
    def __init__(self):
        self.model_validator = ModelCatalogValidator()
        self.field_validator = FieldAPIValidator()
        self.business_validator = BusinessRulesValidator()
        
    def validate(self, product_data):
        # STEP 1: Model Validation
        if not self.model_validator.validate(product_data['model']):
            return ValidationResult(
                success=False,
                error="Model not in Avito catalog",
                suggestion=self.model_validator.get_similar_models()
            )
        
        # STEP 2: Field Format Validation (Live API)
        field_result = self.field_validator.validate_all_fields(product_data)
        if not field_result.success:
            return field_result
        
        # STEP 3: Business Rules
        business_result = self.business_validator.validate(product_data)
        if not business_result.success:
            return business_result
        
        return ValidationResult(success=True)
```

#### **Model Catalog Management**
```python
class ModelCatalogManager:
    """
    Manages the snowmobile model catalog with smart caching
    """
    
    def __init__(self):
        self.catalog_url = "https://www.avito.ru/web/1/catalogs/content/feed/snegohod.xml"
        self.cache_path = "./cache/models/snegohod_models.xml"
        self.cache_duration = 86400  # 24 hours
        self.models = []
        self.last_fetch = None
        
    def get_models(self):
        """Get models with intelligent caching"""
        if self.should_refresh_cache():
            try:
                self.fetch_from_avito()
            except RateLimitError:
                # Use cached version if rate limited
                self.load_from_cache()
        else:
            self.load_from_cache()
        
        return self.models
    
    def should_refresh_cache(self):
        """Check if cache needs refresh"""
        # Refresh daily at 02:00 MSK (before Avito's first processing)
        current_hour = datetime.now(moscow_tz).hour
        if current_hour == 2 and self.last_fetch_date != today:
            return True
        
        # Refresh if cache is older than 24 hours
        if not self.cache_exists() or self.cache_age() > self.cache_duration:
            return True
            
        return False
    
    def fetch_from_avito(self):
        """Fetch catalog from Avito with rate limit handling"""
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/xml'
        }
        
        # Implement exponential backoff for rate limits
        for attempt in range(3):
            try:
                response = requests.get(
                    self.catalog_url, 
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    self.save_to_cache(response.content)
                    self.parse_models(response.content)
                    self.last_fetch = datetime.now()
                    break
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt * 10  # 10, 20, 40 seconds
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed to fetch: {response.status_code}")
                    
            except Exception as e:
                if attempt == 2:  # Last attempt
                    # Fall back to cache
                    self.load_from_cache()
```

### **3. XML Generation**

#### **Main Template Structure**
```xml
<?xml version="1.0" encoding="utf-8"?>
<Ads formatVersion="3" target="Avito.ru">
    <Ad>
        <!-- REQUIRED FIELDS -->
        <Id>{article_code}</Id>
        <Title>{title}</Title>
        <Category>Мотоциклы и мототехника</Category>
        <VehicleType>Снегоходы</VehicleType>
        <Price>{price}</Price>
        <Description>{description}</Description>
        <Images>
            <Image url="{image_url}"/>
        </Images>
        <Address>Санкт-Петербург</Address>
        
        <!-- VALIDATED MODEL FIELD -->
        <Model>{validated_model_name}</Model>
        
        <!-- FIXED VALUES -->
        <Make>BRP</Make>
        <EngineType>Бензин</EngineType>
        <Condition>Новое</Condition>
        <Kilometrage>0</Kilometrage>
        
        <!-- OPTIONAL VALIDATED FIELDS -->
        <Year>{year}</Year>
        <Power>{power_hp}</Power>
        <EngineCapacity>{engine_cc}</EngineCapacity>
        <PersonCapacity>{passengers}</PersonCapacity>
        <TrackWidth>{track_mm}</TrackWidth>
        <Type>{snowmobile_type}</Type>
        <Availability>{availability}</Availability>
    </Ad>
</Ads>
```

### **4. Live API Field Validation**

#### **Field Validation Service**
```python
class FieldValidationService:
    """
    Uses live Avito API for field validation rules
    """
    
    def __init__(self):
        self.api_endpoint = "https://api.avito.ru/autoload/v1/user-docs/node/snegohody/fields"
        self.field_rules = {}
        self.last_update = None
        
    def update_field_rules(self):
        """Fetch latest field rules from API"""
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(self.api_endpoint, headers=headers)
        
        if response.status_code == 200:
            self.parse_field_rules(response.json())
            self.last_update = datetime.now()
    
    def validate_field(self, field_name, value):
        """Validate single field against live API rules"""
        
        if field_name not in self.field_rules:
            return ValidationResult(success=True, warning="No validation rule")
        
        rule = self.field_rules[field_name]
        
        # Check required
        if rule['required'] and not value:
            return ValidationResult(
                success=False,
                error=f"{field_name} is required"
            )
        
        # Check type
        if rule['type'] == 'numeric' and value:
            if not str(value).isdigit():
                return ValidationResult(
                    success=False,
                    error=f"{field_name} must be numeric",
                    suggestion="Remove currency symbols and commas"
                )
        
        # Check format
        if rule.get('format_pattern'):
            if not re.match(rule['format_pattern'], str(value)):
                return ValidationResult(
                    success=False,
                    error=f"{field_name} format invalid",
                    suggestion=f"Use format: {rule['format_example']}"
                )
        
        return ValidationResult(success=True)
```

## 🚀 **Production Pipeline Flow**

### **Step 1: Initialize Pipeline**
```python
# Initialize with latest validation rules
pipeline = AvitoPipeline()
pipeline.update_model_catalog()  # Fetch/cache model list
pipeline.update_field_rules()    # Get latest API rules
```

### **Step 2: Process Product**
```python
# Get product data
product = get_brp_product(article_code)

# CRITICAL: Validate BEFORE generation
validation_result = pipeline.validate(product)

if not validation_result.success:
    # STOP - Do not proceed with invalid data
    log_error(validation_result)
    send_alert(validation_result)
    return FAILURE

# Generate XML only if valid
xml_content = pipeline.generate_xml(product)
```

### **Step 3: Upload to FTP**
```python
# Upload validated XML
ftp_client = FTPClient(
    host='176.126.165.67',
    user='user133859',
    password=credentials['ftp_password']
)

success = ftp_client.upload(
    local_file=xml_content,
    remote_path='/test_corrected_profile.xml'
)

if success:
    log_success(f"Uploaded {product['article_code']}")
else:
    retry_with_backoff()
```

### **Step 4: Monitor Processing**
```python
# Check Avito processing results
monitor = AvitoMonitor()

# Wait for next processing window
next_window = monitor.get_next_processing_time()  # 03:00, 11:00, or 19:00
wait_until(next_window)

# Check processing results
report = monitor.get_latest_report()

if report.has_errors():
    # Analyze errors
    errors = report.get_errors()
    
    # Update validation rules if new constraints found
    if errors.has_new_validation_rules():
        pipeline.add_validation_rule(errors.get_new_rules())
```

## 📊 **Validation Strategy**

### **Three-Layer Validation**

#### **Layer 1: Model Validation (Cached Catalog)**
- **Source**: Cached XML catalog (daily refresh)
- **Fallback**: Last known good cache if rate limited
- **Update**: Daily at 02:00 MSK
- **Critical**: YES - invalid model = rejection

#### **Layer 2: Field Validation (Live API)**  
- **Source**: Live API endpoint
- **Cache**: 1 hour (field rules change rarely)
- **Update**: On-demand with caching
- **Critical**: YES - invalid format = rejection

#### **Layer 3: Business Rules (Internal)**
- **Source**: Internal business logic
- **Examples**: Price ranges, year limits, capacity constraints
- **Update**: As needed based on market
- **Critical**: YES - prevents nonsensical data

## 🔄 **Cache Management**

### **Model Catalog Cache**
```python
cache_config = {
    'location': './cache/models/snegohod_models.xml',
    'max_age': 86400,  # 24 hours
    'refresh_time': '02:00 MSK',  # Before Avito processing
    'fallback': True,  # Use stale cache if fetch fails
    'retry_strategy': 'exponential_backoff'
}
```

### **Field Rules Cache**
```python
field_cache_config = {
    'location': './cache/field_rules.json',
    'max_age': 3600,  # 1 hour
    'refresh_on_error': True,  # Refresh if validation fails
    'api_timeout': 30
}
```

## 🚨 **Error Handling**

### **Validation Failures**
```python
def handle_validation_failure(error):
    # Log detailed error
    logger.error(f"Validation failed: {error}")
    
    # Alert team
    send_slack_alert(f"Avito validation failed: {error}")
    
    # Do NOT proceed with XML generation
    raise ValidationCriticalError("Cannot proceed with invalid data")
```

### **Rate Limit Handling**
```python
def handle_rate_limit():
    # Use cached data
    models = load_cached_models()
    
    if cache_is_stale(models):
        # Alert but continue with stale data
        logger.warning("Using stale model cache due to rate limit")
        
    return models
```

### **Upload Failures**
```python
def handle_upload_failure(error, retry_count=0):
    if retry_count < 3:
        # Exponential backoff
        wait_time = 2 ** retry_count * 10
        time.sleep(wait_time)
        return retry_upload(retry_count + 1)
    else:
        # Alert and queue for manual review
        alert_critical("FTP upload failed after 3 attempts")
        queue_for_manual_upload()
```

## 📈 **Monitoring & Metrics**

### **Key Metrics**
```python
metrics = {
    'validation_success_rate': '99.5%',  # Target
    'model_cache_hit_rate': '95%',       # Minimize API calls
    'field_validation_time': '<100ms',   # Performance
    'xml_generation_time': '<500ms',     # Performance
    'upload_success_rate': '99%',        # Reliability
    'processing_success_rate': '98%'     # Avito acceptance
}
```

### **Health Checks**
```python
health_checks = [
    {
        'name': 'Model Cache Fresh',
        'check': lambda: cache_age() < 86400,
        'critical': True
    },
    {
        'name': 'API Access',
        'check': lambda: test_api_connection(),
        'critical': True
    },
    {
        'name': 'FTP Access',
        'check': lambda: test_ftp_connection(),
        'critical': True
    },
    {
        'name': 'Validation Service',
        'check': lambda: test_validation_service(),
        'critical': True
    }
]
```

## 🎯 **Critical Success Factors**

1. **Internal Validation is MANDATORY**
   - Never skip validation
   - Never upload unvalidated XML
   - Stop pipeline on validation failure

2. **Model Catalog Management**
   - Cache daily at 02:00 MSK
   - Use cache when rate limited
   - Alert on stale cache >48 hours

3. **Live API Integration**
   - Fetch field rules regularly
   - Cache with 1-hour expiry
   - Handle API failures gracefully

4. **Error Prevention**
   - Validate before generation
   - Use exact model names
   - Format all numeric fields correctly

5. **Monitoring**
   - Track validation success rate
   - Alert on failures immediately
   - Log all validation errors for analysis

## 🔐 **Security & Credentials**

### **Credential Management**
```python
credentials = {
    'avito_client_id': env['AVITO_CLIENT_ID'],
    'avito_client_secret': env['AVITO_CLIENT_SECRET'],
    'ftp_host': '176.126.165.67',
    'ftp_user': 'user133859',
    'ftp_password': env['FTP_PASSWORD']
}
```

### **Access Control**
- API credentials: OAuth2 client credentials flow
- FTP access: Secure credentials in environment
- Cache access: Local filesystem with permissions

## 📝 **Summary**

This pipeline ensures **100% valid XML generation** through:

1. **Mission-critical internal validation** before any XML generation
2. **Smart caching** of model catalog to avoid rate limits
3. **Live API integration** for current field validation rules
4. **Comprehensive error handling** at every step
5. **Continuous monitoring** and improvement

**The internal validation system is the gatekeeper** - nothing passes without validation.