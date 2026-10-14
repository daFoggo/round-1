from functools import lru_cache
from app.config import settings, Settings
from app.services.pipeline import QAPipeline

@lru_cache()
def get_settings() -> Settings:
    return settings

_pipeline_instance = None

def get_qa_pipeline() -> QAPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = QAPipeline()
    return _pipeline_instance
