from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "AI Tai Nang 2026 - Excel QA"
    debug: bool = False
    
    
    # OpenRouter Configuration (for official competition grading)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "qwen/qwen3.7-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Qwen3.7-Flash mặc định có reasoning: chậm (~20s/lệnh) và tốn token. Tắt để tối ưu thời gian/token.
    openrouter_reasoning_effort: str = "none"  # none | low | medium | high
    workers: int = 5
    run_deadline_seconds: int = 35 * 60  # đề: tối đa 40 phút/20 câu; chừa biên để vẫn ghi được CSV
    llm_timeout: int = 90
    llm_max_attempts: int = 5
    llm_max_backoff: float = 30.0
    
    # Pipeline Settings
    max_retries: int = 3
    enable_direct_fallback: bool = True
    fallback_table_chars: int = 6000
    # Biến thể prompt để A/B: 'qfirst' (câu hỏi trước bảng), 'plan' (kế hoạch bằng chú thích trước khi viết code); nối bằng '+'
    prompt_variant: str = ""
    # Suy layout bằng LLM (1 lệnh gọi/sheet bị nghi parse sai) rồi dựng lại bảng; thay cho việc dán lưới ô thô vào prompt
    layout_repair: bool = False
    # Dán lưới ô thô vào prompt cho sheet bị nghi parse sai (biện pháp tạm); tắt để đo đóng góp của phần tiền xử lý
    raw_grid: bool = True
    max_output_tokens: int = 2048
    execution_timeout: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
