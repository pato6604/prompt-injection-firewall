from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # Detection settings
    detection_enabled: bool = True
    detection_block_threshold: float = 0.7
    detection_flag_threshold: float = 0.3
    detection_rules_dir: str = "app/detection/policies"

    model_config = {"env_prefix": "", "env_file": ".env"}

settings = Settings()
