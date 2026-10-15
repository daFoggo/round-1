import os
import time
from typing import Dict, Any, Optional
import pandas as pd

from app.config import settings
from .preprocessor import parse_workbook, generate_table_summary
from .llm_client import LLMClient
from .executor import execute_generated_code
from .formatter import format_answer

SYSTEM_PROMPT = """You are an expert Python data analyst specializing in answering natural language queries on complex, hierarchical spreadsheets.
Your task is to write clean, concise, executable Python code to compute the exact answer to the user's question.

ENVIRONMENT & VARIABLES AVAILABLE:
- `dfs`: Dict of DataFrames for each sheet: `{sheet_name: df}`.
- `df`: The primary/first DataFrame. If the file has multiple sheets, inspect `dfs.keys()` to pick the appropriate sheet.
- `file_path`: Path to the original Excel file.
- `pd`, `openpyxl`, `re`, `datetime` are pre-imported.

TABLE STRUCTURE & CONVENTIONS:
1. Column `Row_Path`: Contains the hierarchical path of the row, combining section and item (e.g., 'Division North | Department A | Team 1', 'Category X | Sub-category Y').
   - To find items (categories, occupations, age groups, statuses), filter `df['Row_Path']` or the first column using case-insensitive substring search: `.str.contains('...', case=False, na=False)`.
2. Column `Section`: The top-level category/grouping of the row.
3. Column names: Multi-level column headers joined by ' | ' (e.g., '2024 | Quarter 1 | Revenue', 'Metric Group | Measure Name').

ROBUST DATA ANALYSIS GUIDELINES:
1. MULTI-TABLE & MULTI-SHEET WORKBOOKS:
   - Workbooks or sheets may contain multiple distinct tables. They are provided in `dfs` with descriptive keys: `{table_name: df}` (e.g. `'SheetName - TableTitle'`).
   - If multiple tables exist, select the table whose key matches the query keywords:
     ```python
     # Example: Match table key by keyword
     target_df = next((v for k, v in dfs.items() if 'keyword' in k.lower()), df)
     ```
   - If only one table exists, `df` is already set to the primary table.

2. SUBSTRING MATCHING & COLLISION PREVENTION:
   - Queries may contain typos or synonyms. Use case-insensitive substring search: `.str.contains(..., case=False, na=False)`.
   - IMPORTANT: When searching for a term that could be a substring of another word (such as 'men' inside 'women', 'car' inside 'carpet', or 'full' inside 'full-time'), ALWAYS use regex word boundaries `r'\\bterm\\b'` or explicit exclusions `& ~df['Row_Path'].str.contains('conflicting_word')`.

3. PRE-AGGREGATED TOTALS VS. SUB-CATEGORIES:
   - Data tables often include pre-calculated summary rows (e.g., 'Total', 'Overall', 'All items').
   - When asked for a summary across an entire category, prefer using the existing summary row/column rather than re-summing individual sub-categories, which avoids double-counting nested components.

4. COLUMNS VS ROWS:
   - Distinguish whether an attribute represents a column header or a row label.
   - Column names in `df.columns` are joined by ' | '. Match columns flexibly:
     `[c for c in df.columns if 'metric_name' in c.lower()]`.

5. DATE & TIME COMPUTATIONS:
   - When computing intervals, age, or elapsed time from dates, parse with `pd.to_datetime(...)` and compute differences (e.g., `.dt.days` or `.dt.total_seconds()`).

GENERAL PROGRAMMING PATTERNS:
- Pattern A (Aggregating across multiple metric columns for a specific row):
  ```python
  # Filter matching row and compute metric across relevant columns
  row = df[df['Row_Path'].str.contains('Category A', case=False, na=False) & df['Row_Path'].str.contains('Sub-group', case=False, na=False)]
  cols = [c for c in df.columns if 'target_metric' in c.lower()]
  FINAL_ANSWER = round(row[cols].iloc[0].astype(float).mean(), 2)
  ```
- Pattern B (Comparing metrics across distinct categories with collision avoidance):
  ```python
  # Use word boundary r'\\b...\\b' to prevent false substring matches
  item_a = df[df['Row_Path'].str.contains(r'\\bItemA\\b', case=False, na=False)]
  item_b = df[df['Row_Path'].str.contains(r'\\bItemB\\b', case=False, na=False)]
  col = [c for c in df.columns if 'metric_name' in c.lower()][0]
  FINAL_ANSWER = f"{item_a[col].values[0]:.2f}, {item_b[col].values[0]:.2f}"
  ```
- Pattern C (Date arithmetic and sorting):
  ```python
  elapsed = (pd.to_datetime(df['End Date']) - pd.to_datetime(df['Start Date'])).dt.days
  ranked = df.assign(duration=elapsed).sort_values(by='duration')
  FINAL_ANSWER = ranked.iloc[0]['Entity Name']
  ```

OUTPUT FORMAT:
- Assign the final computed result to variable `FINAL_ANSWER`.
- Return ONLY executable Python code inside ```python ... ``` block. No markdown or explanation outside the code block.
"""

def is_invalid_result(res: Any, err: Optional[str]) -> bool:
    """Kiểm tra xem kết quả có bị lỗi, None, NaN hoặc rỗng hay không."""
    if err is not None:
        return True
    if res is None:
        return True
    if isinstance(res, float) and pd.isna(res):
        return True
    if isinstance(res, str) and res.strip().lower() in ['', 'nan', 'none']:
        return True
    return False

class QAPipeline:
    def __init__(
        self,
        provider: Optional[str] = None,
        openrouter_key: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        openrouter_base_url: Optional[str] = None,
    ):
        self.llm = LLMClient(
            provider=provider,
            openrouter_key=openrouter_key,
            model=openrouter_model,
            openrouter_base_url=openrouter_base_url,
        )
        self.parsed_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.max_retries = settings.max_retries

    def get_parsed_workbook(self, file_path: str) -> Dict[str, pd.DataFrame]:
        if file_path not in self.parsed_cache:
            self.parsed_cache[file_path] = parse_workbook(file_path)
        return self.parsed_cache[file_path]

    def answer_query(self, file_path: str, query: str, max_retries: Optional[int] = None) -> Dict[str, Any]:
        retries_limit = max_retries if max_retries is not None else self.max_retries
        start_time = time.time()
        dfs = self.get_parsed_workbook(file_path)
        table_summary = generate_table_summary(dfs)

        user_prompt = f"""File: {os.path.basename(file_path)}

TABLE SUMMARY:
{table_summary}

QUESTION:
"{query}"

Write Python code to compute the answer and assign it to `FINAL_ANSWER`.
"""

        raw_response = self.llm.generate_response(user_prompt, system_prompt=SYSTEM_PROMPT)
        code = self.llm.extract_python_code(raw_response)

        raw_result, error_trace = execute_generated_code(code, dfs, file_path)
        retries_used = 0

        while is_invalid_result(raw_result, error_trace) and retries_used < retries_limit:
            retries_used += 1
            reason = error_trace if error_trace else f"FINAL_ANSWER was invalid or empty ({repr(raw_result)}). Please verify your filtering conditions on df['Row_Path'] and column names against the table summary."
            correction_prompt = f"""Your previous code returned an invalid result or failed.
Previous Code:
```python
{code}
```

Issue:
{reason}

Please fix the code to correctly compute the answer for the question:
"{query}"

Output ONLY the corrected Python code inside ```python ... ``` block.
"""
            raw_response = self.llm.generate_response(correction_prompt, system_prompt=SYSTEM_PROMPT)
            code = self.llm.extract_python_code(raw_response)
            raw_result, error_trace = execute_generated_code(code, dfs, file_path)

        formatted = format_answer(raw_result, query)
        elapsed = time.time() - start_time

        return {
            "query": query,
            "raw_result": raw_result,
            "answer": formatted,
            "code": code,
            "retries": retries_used,
            "error": error_trace,
            "elapsed_seconds": round(elapsed, 2)
        }
