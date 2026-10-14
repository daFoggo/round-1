from pydantic import BaseModel
from typing import Optional, List, Any

class QueryItem(BaseModel):
    id: str
    file_name: str
    query: str

class QueryResponse(BaseModel):
    id: str
    query: str
    answer: str
    raw_result: Optional[Any] = None
    code: Optional[str] = None
    retries: int = 0
    elapsed_seconds: float = 0.0

class BatchQueryRequest(BaseModel):
    input_dir: str = "xlsx_files"
    queries_file: str = "queries.json"
    output_file: Optional[str] = "submission.csv"

class EvaluationMetric(BaseModel):
    total_queries: int
    exact_matches: int
    accuracy_percentage: float
    total_time_seconds: float
    avg_time_per_query: float
