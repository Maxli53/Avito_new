import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Database settings
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/snowmobile_dual_parser",
        env="DATABASE_URL",
        description="PostgreSQL database connection URL"
    )
    
    db_pool_min_size: int = Field(default=1, env="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=10, env="DB_POOL_MAX_SIZE") 
    db_command_timeout: int = Field(default=60, env="DB_COMMAND_TIMEOUT")
    
    # Claude AI settings
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    claude_max_tokens: int = Field(default=4000, env="CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(default=0.1, env="CLAUDE_TEMPERATURE")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # File storage settings
    pdf_storage_path: str = Field(default="./data/pdfs", env="PDF_STORAGE_PATH")
    html_output_path: str = Field(default="./data/html", env="HTML_OUTPUT_PATH")
    
    # Processing settings
    max_concurrent_extractions: int = Field(default=3, env="MAX_CONCURRENT_EXTRACTIONS")
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
    
    def get_pdf_storage_path(self) -> Path:
        """Get PDF storage path as Path object"""
        return Path(self.pdf_storage_path)
    
    def get_html_output_path(self) -> Path:
        """Get HTML output path as Path object"""
        return Path(self.html_output_path)
    
    def ensure_directories_exist(self):
        """Create necessary directories if they don't exist"""
        self.get_pdf_storage_path().mkdir(parents=True, exist_ok=True)
        self.get_html_output_path().mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        Path("logs").mkdir(parents=True, exist_ok=True)
    
    def validate_settings(self) -> List[str]:
        """Validate settings and return list of issues"""
        issues = []
        
        if not self.claude_api_key:
            issues.append("CLAUDE_API_KEY is not set")
        
        if not self.database_url or self.database_url == "postgresql://user:password@localhost:5432/snowmobile_dual_parser":
            issues.append("DATABASE_URL is not properly configured")
        
        if self.api_port < 1 or self.api_port > 65535:
            issues.append(f"Invalid API_PORT: {self.api_port}")
        
        if self.claude_temperature < 0 or self.claude_temperature > 1:
            issues.append(f"Invalid CLAUDE_TEMPERATURE: {self.claude_temperature}")
        
        return issues


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def validate_environment():
    """Validate environment configuration and raise error if invalid"""
    issues = settings.validate_settings()
    
    if issues:
        raise RuntimeError(
            f"Environment configuration issues:\n" + 
            "\n".join(f"  - {issue}" for issue in issues)
        )
    
    # Ensure directories exist
    settings.ensure_directories_exist()
    
    return True