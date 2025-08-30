# Deployment Guide
**Snowmobile Product Data Reconciliation System**

## 🎯 Deployment Overview

This guide covers complete deployment procedures for the snowmobile product reconciliation system from development through production.

## 🏗️ Environment Configuration

### Development Environment
```bash
# Local development setup
poetry install
poetry shell
pre-commit install

# Database setup
createdb snowmobile_dev
poetry run alembic upgrade head

# Environment variables (.env)
DATABASE_URL=postgresql://localhost/snowmobile_dev
CLAUDE_API_KEY=sk-ant-api03-dev-key
ENVIRONMENT=development
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

### Staging Environment
```bash
# Staging environment variables
DATABASE_URL=postgresql://staging-db:5432/snowmobile_staging
CLAUDE_API_KEY=sk-ant-api03-staging-key
ENVIRONMENT=staging
DEBUG_MODE=false
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Production Environment
```bash
# Production environment variables (secure)
DATABASE_URL=postgresql://prod-db:5432/snowmobile_prod
CLAUDE_API_KEY=sk-ant-api03-prod-key
ENVIRONMENT=production
DEBUG_MODE=false
LOG_LEVEL=INFO
METRICS_ENABLED=true
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
```

## 🚀 Deployment Process

### Pre-Deployment Validation
```bash
# Complete validation checklist
make validate-all              # All quality checks pass
make test-integration          # End-to-end tests pass
make security-scan             # Zero vulnerabilities
make performance-benchmark     # Performance requirements met
make documentation-check       # Documentation updated

# Deployment safety checks
poetry run python scripts/pre_deployment_check.py
```

### Staging Deployment
```bash
# Build application
make build

# Deploy to staging
make deploy-staging

# Validate staging deployment
make test-staging
poetry run python scripts/validate_staging.py

# Performance testing on staging
make load-test-staging
```

### Production Deployment
```bash
# Final pre-production checks
make validate-production-readiness

# Create production backup
make backup-production

# Deploy to production (requires manual approval)
make deploy-prod

# Post-deployment validation
make validate-production-deployment
make health-check-production
```

## 🐳 Docker Configuration

### Development Docker Setup
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  app:
    build: 
      context: .
      target: development
    volumes:
      - .:/app
      - poetry-cache:/root/.cache/pypoetry
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/snowmobile_dev
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DEBUG_MODE=true
    depends_on:
      - db
      - redis
    ports:
      - "8000:8000"

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: snowmobile_dev
      POSTGRES_USER: postgres  
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres-data:
  poetry-cache:
```

### Production Docker Configuration
```dockerfile
# Multi-stage production Dockerfile
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.5.1

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction

# Production stage
FROM python:3.10-slim as production

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
WORKDIR /app
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run as non-root user
USER appuser

# Start application
CMD ["python", "-m", "src.api.main"]
```

## 🗄️ Database Deployment

### Migration Management
```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add new feature"

# Review migration before applying
cat migrations/versions/001_add_new_feature.py

# Apply migration to staging
poetry run alembic upgrade head

# Validate migration success
poetry run python scripts/validate_migration.py

# Rollback if needed
poetry run alembic downgrade -1
```

### Database Backup Strategy
```python
class DatabaseBackupManager:
    """Automated database backup and recovery"""
    
    def create_backup(self, environment: str) -> BackupResult:
        """Create timestamped database backup"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"backup_{environment}_{timestamp}.sql"
        
        # Create backup
        subprocess.run([
            'pg_dump',
            '--no-password',
            '--format=custom',
            '--file', backup_file,
            self.database_url
        ], check=True)
        
        # Validate backup
        self._validate_backup(backup_file)
        
        return BackupResult(backup_file, timestamp)
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore database from backup"""
        
    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove backups older than retention period"""
```

## 📊 Monitoring and Alerting

### Production Monitoring Setup
```python
# Prometheus metrics configuration
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
PROCESSING_COUNTER = Counter('products_processed_total', 'Total products processed')
PROCESSING_TIME = Histogram('processing_duration_seconds', 'Time spent processing')
CONFIDENCE_GAUGE = Gauge('average_confidence_score', 'Average confidence score')
API_CALLS_COUNTER = Counter('claude_api_calls_total', 'Total Claude API calls')

class MetricsCollector:
    """Collect and expose metrics for monitoring"""
    
    def track_processing(self, processing_time: float, confidence: float):
        """Track processing metrics"""
        PROCESSING_COUNTER.inc()
        PROCESSING_TIME.observe(processing_time)
        CONFIDENCE_GAUGE.set(confidence)
    
    def track_api_usage(self):
        """Track Claude API usage"""
        API_CALLS_COUNTER.inc()
```

### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Snowmobile Pipeline Monitoring",
    "panels": [
      {
        "title": "Processing Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(products_processed_total[5m])",
            "legendFormat": "Products/minute"
          }
        ]
      },
      {
        "title": "Confidence Score Distribution", 
        "type": "histogram",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, processing_confidence_bucket)",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "API Cost Tracking",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(claude_api_calls_total[1d]) * 0.015",
            "legendFormat": "Daily API Cost ($)"
          }
        ]
      }
    ]
  }
}
```

## 🔐 Security Configuration

### API Key Management
```bash
# Secure API key storage (production)
# Use AWS Secrets Manager, Azure Key Vault, or similar

# Environment-specific key rotation
CLAUDE_API_KEY_DEV=sk-ant-api03-dev-...
CLAUDE_API_KEY_STAGING=sk-ant-api03-staging-...  
CLAUDE_API_KEY_PROD=sk-ant-api03-prod-...

# Key rotation script
poetry run python scripts/rotate_api_keys.py --environment production
```

### Database Security
```sql
-- Create dedicated database users
CREATE USER snowmobile_app WITH PASSWORD 'secure_password';
CREATE USER snowmobile_readonly WITH PASSWORD 'readonly_password';

-- Grant minimal necessary permissions
GRANT CONNECT ON DATABASE snowmobile_prod TO snowmobile_app;
GRANT USAGE ON SCHEMA public TO snowmobile_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO snowmobile_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO snowmobile_app;

-- Read-only access for reporting
GRANT CONNECT ON DATABASE snowmobile_prod TO snowmobile_readonly;
GRANT USAGE ON SCHEMA public TO snowmobile_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO snowmobile_readonly;
```

## 🚨 Rollback Procedures

### Application Rollback
```bash
# Quick rollback to previous version
docker tag snowmobile:current snowmobile:rollback-backup
docker tag snowmobile:previous snowmobile:current
docker-compose up -d

# Database rollback (if needed)
poetry run alembic downgrade -1

# Validate rollback success
make health-check
make test-critical-functionality
```

### Emergency Recovery
```python
class EmergencyRecovery:
    """Emergency recovery procedures"""
    
    def emergency_stop(self):
        """Stop all processing immediately"""
        # Stop all running processes
        # Clear processing queues
        # Send alerts to operations team
    
    def restore_from_backup(self, backup_timestamp: str):
        """Restore system from specific backup"""
        # Restore database
        # Restore application state
        # Validate system integrity
    
    def rollback_deployment(self, previous_version: str):
        """Rollback to previous working version"""
        # Deploy previous version
        # Restore compatible database state
        # Validate system functionality
```

## 📋 Deployment Checklist

### Pre-Deployment (Required)
- [ ] **Code Quality**: All quality checks pass (make validate-all)
- [ ] **Testing**: Full test suite passes with 80%+ coverage
- [ ] **Security**: Security scan shows zero vulnerabilities
- [ ] **Performance**: Benchmarks meet requirements
- [ ] **Documentation**: All documentation updated
- [ ] **Database**: Migrations tested and validated
- [ ] **Backup**: Current state backed up
- [ ] **Rollback Plan**: Rollback procedure tested

### During Deployment
- [ ] **Monitoring**: Real-time monitoring active
- [ ] **Health Checks**: Continuous health validation
- [ ] **Performance**: Monitor resource usage
- [ ] **Error Tracking**: Watch for error spikes
- [ ] **User Impact**: Monitor customer-facing services

### Post-Deployment
- [ ] **Validation**: Run post-deployment test suite
- [ ] **Performance**: Verify performance targets met
- [ ] **Monitoring**: Confirm all monitoring systems active
- [ ] **Documentation**: Update deployment records
- [ ] **Team Notification**: Notify stakeholders of completion

## 📞 Support Contacts

### Technical Issues
- **Database**: DBA team for query optimization and schema issues
- **API**: Claude support for API-related problems
- **Infrastructure**: DevOps team for deployment and infrastructure

### Business Issues
- **Data Quality**: Product management for specification validation
- **Cost Optimization**: Finance team for API cost monitoring
- **Performance**: Business stakeholders for SLA requirements

---

**Deployment Standards**: All deployments must follow this exact procedure. Any shortcuts or deviations risk system stability and data integrity.