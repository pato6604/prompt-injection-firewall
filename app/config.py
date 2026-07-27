from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o-mini"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    model_config = {"env_prefix": "", "env_file": ".env"}

settings = Settings()