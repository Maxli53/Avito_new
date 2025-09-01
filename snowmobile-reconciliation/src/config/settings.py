"""
Application configuration management using Pydantic settings.

Implements secure configuration handling following Universal Development Standards
with environment variable support and validation.
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration with connection pooling"""

    # Core database settings
    database_url: PostgresDsn = Field(..., description="Database connection URL")
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Maximum overflow connections")
    database_pool_timeout: int = Field(default=30, description="Pool connection timeout")
    database_pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")

    # Connection settings
    database_echo: bool = Field(False, env="DB_ECHO")
    database_echo_pool: bool = Field(False, env="DB_ECHO_POOL")

    # Migration settings
    alembic_config_path: str = Field("alembic.ini", env="ALEMBIC_CONFIG_PATH")

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL is valid PostgreSQL URL"""
        if not str(v).startswith("postgresql"):
            raise ValueError("Database URL must be PostgreSQL (postgresql://...)")
        return v

    model_config = ConfigDict(env_prefix="DB_")


class ClaudeSettings(BaseSettings):
    """Claude API configuration with security and cost controls"""

    # API credentials
    claude_api_key: str = Field(..., env="CLAUDE_API_KEY")
    claude_model: str = Field("claude-3-haiku-20240307", env="CLAUDE_MODEL")

    # Request configuration
    claude_max_tokens: int = Field(4000, env="CLAUDE_MAX_TOKENS", ge=100, le=8000)
    claude_temperature: float = Field(0.1, env="CLAUDE_TEMPERATURE", ge=0.0, le=1.0)
    claude_timeout_seconds: int = Field(30, env="CLAUDE_TIMEOUT", ge=5, le=120)
    claude_max_retries: int = Field(3, env="CLAUDE_MAX_RETRIES", ge=0, le=5)

    # Batch processing
    claude_batch_size: int = Field(5, env="CLAUDE_BATCH_SIZE", ge=1, le=10)
    claude_batch_enabled: bool = Field(True, env="CLAUDE_BATCH_ENABLED")

    # Rate limiting
    claude_requests_per_minute: int = Field(
        50, env="CLAUDE_REQUESTS_PER_MINUTE", ge=1, le=100
    )
    claude_min_request_interval: float = Field(
        0.1, env="CLAUDE_MIN_REQUEST_INTERVAL", ge=0.0
    )

    # Cost controls
    claude_daily_cost_limit: float = Field(10.0, env="CLAUDE_DAILY_COST_LIMIT", ge=0.0)
    claude_monthly_cost_limit: float = Field(
        200.0, env="CLAUDE_MONTHLY_COST_LIMIT", ge=0.0
    )
    claude_cost_alerts_enabled: bool = Field(True, env="CLAUDE_COST_ALERTS_ENABLED")

    @field_validator("claude_api_key")
    @classmethod
    def validate_api_key(cls, v):
        """Validate Claude API key format"""
        if not v.startswith("sk-ant-"):
            raise ValueError("Claude API key must start with sk-ant-")
        if len(v) < 20:
            raise ValueError("Claude API key appears to be too short")
        return v

    model_config = ConfigDict(env_prefix="CLAUDE_")


class PipelineSettings(BaseSettings):
    """Pipeline processing configuration"""

    # Confidence thresholds
    auto_accept_threshold: float = Field(
        0.9, env="AUTO_ACCEPT_THRESHOLD", ge=0.5, le=1.0
    )
    manual_review_threshold: float = Field(
        0.7, env="MANUAL_REVIEW_THRESHOLD", ge=0.0, le=1.0
    )

    # Performance settings
    max_concurrent_processing: int = Field(10, env="MAX_CONCURRENT", ge=1, le=50)
    enable_parallel_stages: bool = Field(True, env="ENABLE_PARALLEL_STAGES")

    # Feature flags
    enable_spring_options: bool = Field(True, env="ENABLE_SPRING_OPTIONS")
    enable_claude_fallback: bool = Field(True, env="ENABLE_CLAUDE_FALLBACK")
    enable_confidence_tuning: bool = Field(True, env="ENABLE_CONFIDENCE_TUNING")

    # Processing limits
    max_products_per_batch: int = Field(
        1000, env="MAX_PRODUCTS_PER_BATCH", ge=1, le=10000
    )
    processing_timeout_seconds: int = Field(
        300, env="PROCESSING_TIMEOUT", ge=30, le=3600
    )

    # Quality controls
    min_base_model_confidence: float = Field(
        0.6, env="MIN_BASE_MODEL_CONFIDENCE", ge=0.0, le=1.0
    )
    min_spring_options_confidence: float = Field(
        0.7, env="MIN_SPRING_OPTIONS_CONFIDENCE", ge=0.0, le=1.0
    )

    @field_validator("manual_review_threshold")
    @classmethod
    def validate_review_threshold(cls, v, info):
        """Ensure manual review threshold is less than auto accept threshold"""
        auto_accept = info.data.get("auto_accept_threshold", 0.9)
        if v >= auto_accept:
            raise ValueError(
                "Manual review threshold must be less than auto accept threshold"
            )
        return v

    model_config = ConfigDict(env_prefix="PIPELINE_")


class SecuritySettings(BaseSettings):
    """Security configuration"""

    # Application security
    secret_key: str = Field(..., env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS", ge=1, le=168)

    # API security
    api_key_enabled: bool = Field(False, env="API_KEY_ENABLED")
    api_keys: list[str] = Field(default_factory=list, env="API_KEYS")

    # CORS settings
    cors_origins: list[str] = Field(default_factory=list, env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(False, env="CORS_ALLOW_CREDENTIALS")

    # Rate limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(60, env="RATE_LIMIT_RPM", ge=1)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure secret key is sufficiently strong"""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v

    @field_validator("api_keys")
    @classmethod
    def validate_api_keys(cls, v):
        """Validate API key format"""
        for key in v:
            if len(key) < 20:
                raise ValueError("API keys must be at least 20 characters long")
        return v

    model_config = ConfigDict(env_prefix="SECURITY_")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration"""

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")  # json, text
    log_file_enabled: bool = Field(True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field("logs/app.log", env="LOG_FILE_PATH")
    log_rotation_size: str = Field("10MB", env="LOG_ROTATION_SIZE")
    log_rotation_count: int = Field(5, env="LOG_ROTATION_COUNT")

    # Metrics
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    prometheus_enabled: bool = Field(False, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(8001, env="PROMETHEUS_PORT", ge=1024, le=65535)

    # Health checks
    health_check_enabled: bool = Field(True, env="HEALTH_CHECK_ENABLED")
    health_check_interval_seconds: int = Field(30, env="HEALTH_CHECK_INTERVAL", ge=10)

    # Performance monitoring
    performance_tracking_enabled: bool = Field(True, env="PERFORMANCE_TRACKING_ENABLED")
    slow_query_threshold_ms: int = Field(1000, env="SLOW_QUERY_THRESHOLD", ge=100)

    # Alerting
    alerts_enabled: bool = Field(False, env="ALERTS_ENABLED")
    alert_webhook_url: Optional[str] = Field(None, env="ALERT_WEBHOOK_URL")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format"""
        if v not in ["json", "text"]:
            raise ValueError('Log format must be "json" or "text"')
        return v

    model_config = ConfigDict(env_prefix="MONITORING_")


class ApplicationSettings(BaseSettings):
    """Main application configuration"""

    # Basic application settings
    app_name: str = Field("Snowmobile Product Reconciliation", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug_mode: bool = Field(False, env="DEBUG_MODE")

    # Server settings
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT", ge=1024, le=65535)
    workers: int = Field(4, env="WORKERS", ge=1, le=16)

    # File processing
    upload_max_size_mb: int = Field(100, env="UPLOAD_MAX_SIZE_MB", ge=1, le=1000)
    temp_dir: str = Field("/tmp/snowmobile", env="TEMP_DIR")

    # External services
    external_api_timeout: int = Field(30, env="EXTERNAL_API_TIMEOUT", ge=5, le=300)

    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    claude: ClaudeSettings = ClaudeSettings()
    pipeline: PipelineSettings = PipelineSettings()
    security: SecuritySettings = SecuritySettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment name"""
        valid_environments = ["development", "staging", "production"]
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v

    @field_validator("debug_mode")
    @classmethod
    def validate_debug_mode(cls, v, info):
        """Ensure debug mode is disabled in production"""
        environment = info.data.get("environment", "development")
        if environment == "production" and v:
            raise ValueError("Debug mode must be disabled in production")
        return v

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == "development"

    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.environment == "staging"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        use_enum_values=True
    )


@lru_cache
def get_settings() -> ApplicationSettings:
    """
    Get application settings with caching.
    Uses LRU cache to avoid re-reading environment on every call.
    """
    return ApplicationSettings()


def validate_settings() -> None:
    """
    Validate all settings and raise helpful errors.
    Call this at application startup to fail fast on configuration errors.
    """
    try:
        settings = get_settings()

        # Validate critical paths exist
        temp_dir = Path(settings.temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        log_file = Path(settings.monitoring.log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Validate Claude API connectivity in production
        if settings.is_production():
            if not settings.claude.claude_api_key:
                raise ValueError("Claude API key is required in production")

        # Validate database connectivity
        if not settings.database.database_url:
            raise ValueError("Database URL is required")

        print("✓ All settings validated successfully")

    except Exception as e:
        print(f"❌ Settings validation failed: {e}")
        raise


def get_environment_info() -> dict:
    """Get current environment information for debugging"""
    settings = get_settings()

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.environment,
        "debug_mode": settings.debug_mode,
        "host": settings.host,
        "port": settings.port,
        "database_configured": bool(settings.database.database_url),
        "claude_configured": bool(settings.claude.claude_api_key),
        "monitoring_enabled": settings.monitoring.metrics_enabled,
        "pipeline_features": {
            "spring_options": settings.pipeline.enable_spring_options,
            "claude_fallback": settings.pipeline.enable_claude_fallback,
            "confidence_tuning": settings.pipeline.enable_confidence_tuning,
        },
    }


# Export main settings getter for easy importing
__all__ = [
    "ApplicationSettings",
    "get_settings",
    "validate_settings",
    "get_environment_info",
]
