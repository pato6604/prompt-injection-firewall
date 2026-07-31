from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    database_url: str = "sqlite+aiosqlite:///./firewall.db"
    redis_url: str = ""
    auth_enabled: bool = True
    auth_master_key: str = ""
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=60, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    decision_cache_ttl_seconds: int = 60

    # Detection settings
    detection_enabled: bool = True
    detection_block_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    detection_flag_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    detection_rules_dir: str = "app/detection/policies"

    model_config = {"env_prefix": "", "env_file": ".env"}

settings = Settings()
