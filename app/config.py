from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "AI Tai Nang 2026 - Excel QA"
    debug: bool = False
    
    # Provider: 'openrouter' (chấm thi chính thức) hoặc 'gemini' (thử nghiệm cục bộ)
    llm_provider: str = "openrouter"
    
    # Gemini Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.1-flash-lite"
    
    # OpenRouter Configuration (for official competition grading)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "qwen/qwen3.7-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Pipeline Settings
    max_retries: int = 2
    max_output_tokens: int = 2048
    execution_timeout: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
