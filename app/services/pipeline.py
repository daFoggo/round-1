import os
import time
from typing import Dict, Any, Optional
import pandas as pd

from app.config import settings
from .preprocessor import parse_workbook, parse_raw_workbook, generate_table_summary
from .llm_client import LLMClient
from .executor import execute_generated_code
from .formatter import format_answer

SYSTEM_PROMPT = """You are an expert Python data analyst specializing in answering natural language queries on complex, hierarchical spreadsheets.
Your task is to write clean, concise, executable Python code to compute the exact answer to the user's question.

ENVIRONMENT & VARIABLES AVAILABLE:
- `dfs`: Dict of DataFrames for each sheet: `{sheet_name: df}`.
- `df`: The primary/first DataFrame. If the file has multiple sheets, inspect `dfs.keys()` to pick the appropriate sheet.
- `file_path`: Path to the original Excel file.
- `raw_dfs`: Dict `{sheet_name: DataFrame}` with the raw cell grid of each sheet (merged cells filled, numeric strings converted; index = Excel row number, columns = 1..N). Use it ONLY when a parsed table in `dfs` looks wrong or is missing rows/columns.
- `pd`, `openpyxl`, `re`, `datetime` are pre-imported.

TABLE STRUCTURE & CONVENTIONS:
1. Column `Row_Path`: Contains the hierarchical path of the row, combining section and item (e.g., 'Division North | Department A | Team 1', 'Category X | Sub-category Y').
   - To find items (categories, occupations, age groups, statuses), filter `df['Row_Path']` or the first column using case-insensitive substring search: `.str.contains('...', case=False, na=False)`.
   - The row's OWN label is the LAST segment of `Row_Path` (`df['Row_Path'].str.split(' | ', regex=False).str[-1]`); the earlier segments are its parents. When a question asks for a label (a size class, group, category...), take it from there.
2. Columns `Section` / `Sub_Section`: coarse grouping helpers that are often empty. Do NOT rely on them; rely on `Row_Path`.
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

   - `\\b` word boundaries do NOT work for Chinese/Japanese/Korean or other non-Latin text: for such questions use exact label match or plain substring (and exclusions) instead of `\\b`. Questions and tables may be in any language.

3. PRE-AGGREGATED TOTALS VS. SUB-CATEGORIES:
   - Data tables often include pre-calculated summary rows (e.g., 'Total', 'Overall', 'All items').
   - When asked for a summary across an entire category, prefer using the existing summary row/column rather than re-summing individual sub-categories, which avoids double-counting nested components.

4. "AVERAGE ACROSS ALL ..." CONVENTION (official rule of the contest):
   - If the question asks for an average/mean "across all ..." columns of a row and does NOT say "excluding totals" or "subcategories only", compute the plain unweighted mean over ALL numeric data columns present in that row's scope, subtotal/Total columns included.

5. COLUMNS VS ROWS:
   - Distinguish whether an attribute represents a column header or a row label.
   - Column names in `df.columns` are joined by ' | '. Match columns flexibly:
     `[c for c in df.columns if 'metric_name' in c.lower()]`.

6. DATE & TIME COMPUTATIONS:
   - Convention of this contest: when a table has a date of birth AND another event date (e.g. admission), "age", "oldest" and "youngest" mean the age AT that event date (event date minus birth date), never the age relative to today.
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

7. TEXT ANSWERS: when asked for a name/label "exactly as it appears in the table", return the label text as stored in the table (the last part of `Row_Path`, or the column header text), without inventing or rewording it.

OUTPUT FORMAT:
- `FINAL_ANSWER` must already follow the exact format the question asks for, in any language: number of decimals (build the string with an f-string, e.g. f"{x:.2f}", so "14.20" keeps its trailing zero), integers without ".0" or thousands separators, and the requested separator and order for lists.
- Assign the final computed result to variable `FINAL_ANSWER`. Printing is not enough: a script that only prints has no answer.
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
        openrouter_key: Optional[str] = None,
        openrouter_model: Optional[str] = None,
        openrouter_base_url: Optional[str] = None,
    ):
        self.llm = LLMClient(
            openrouter_key=openrouter_key,
            model=openrouter_model,
            openrouter_base_url=openrouter_base_url,
        )
        self.parsed_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.raw_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.max_retries = settings.max_retries

    def get_parsed_workbook(self, file_path: str) -> Dict[str, pd.DataFrame]:
        if file_path not in self.parsed_cache:
            self.parsed_cache[file_path] = parse_workbook(file_path)
        return self.parsed_cache[file_path]

    def get_raw_workbook(self, file_path: str) -> Dict[str, pd.DataFrame]:
        if file_path not in self.raw_cache:
            try:
                self.raw_cache[file_path] = parse_raw_workbook(file_path)
            except Exception:
                self.raw_cache[file_path] = {}
        return self.raw_cache[file_path]

    def direct_answer(self, dfs: Dict[str, pd.DataFrame], query: str, temperature: float = 0.0) -> str:
        """Đường lui cuối: hỏi thẳng LLM trên bảng dạng CSV cắt gọn khi mọi lần sinh code đều thất bại."""
        parts, budget = [], settings.fallback_table_chars
        for name, d in dfs.items():
            view = d.drop(columns=[c for c in ("Section", "Sub_Section") if c in d.columns])
            parts.append(f"### {name}\n{view.to_csv(index=False)[:budget]}")
        prompt = ("Answer the question using ONLY the tables below. Follow the exact answer format requested in the "
                  "question. Reply with the final answer only, no explanation.\n\n"
                  + "\n".join(parts) + f"\n\nQUESTION: {query}\nANSWER:")
        try:
            return self.llm.generate_response(prompt, temperature=temperature).strip().splitlines()[0].strip()
        except Exception:
            return ""

    def answer_query(self, file_path: str, query: str, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """Biểu quyết thích ứng (adaptive self-consistency): 2 mẫu; trùng nhau thì dừng, khác nhau mới thêm mẫu thứ 3.
        Qwen không hoàn toàn xác định nên một mẫu đơn lẻ dao động ±1-2 câu giữa các lần chạy."""
        retries_limit = max_retries if max_retries is not None else self.max_retries
        start_time = time.time()
        runs = [self._single_run(file_path, query, retries_limit, 0.0)]
        if settings.self_consistency:
            runs.append(self._single_run(file_path, query, retries_limit, settings.sc_temperature))
            if self._norm(runs[0]["answer"]) != self._norm(runs[1]["answer"]):
                runs.append(self._single_run(file_path, query, retries_limit, settings.sc_temperature))
        best = self._majority(runs)
        best = dict(best)
        best["samples"] = len(runs)
        best["elapsed_seconds"] = round(time.time() - start_time, 2)
        return best

    @staticmethod
    def _norm(ans: str) -> str:
        return " ".join(str(ans).lower().split())

    def _majority(self, runs):
        """Đáp án xuất hiện nhiều nhất (trong các mẫu hợp lệ); hoà thì lấy mẫu đầu tiên (temperature 0)."""
        valid = [r for r in runs if self._norm(r["answer"]) not in ("", "nan", "none")] or runs
        counts: Dict[str, int] = {}
        for r in valid:
            counts[self._norm(r["answer"])] = counts.get(self._norm(r["answer"]), 0) + 1
        top = max(counts.values())
        for r in valid:  # thứ tự mẫu: mẫu temperature 0 ưu tiên khi hoà
            if counts[self._norm(r["answer"])] == top:
                return r
        return runs[0]

    def _single_run(self, file_path: str, query: str, retries_limit: int, temperature: float) -> Dict[str, Any]:
        dfs = self.get_parsed_workbook(file_path)
        table_summary = generate_table_summary(dfs)

        user_prompt = f"""File: {os.path.basename(file_path)}

TABLE SUMMARY:
{table_summary}

QUESTION:
"{query}"

Write Python code to compute the answer and assign it to `FINAL_ANSWER`.
"""

        raw_response = self.llm.generate_response(user_prompt, system_prompt=SYSTEM_PROMPT, temperature=temperature)
        code = self.llm.extract_python_code(raw_response)

        raw_dfs = self.get_raw_workbook(file_path)
        raw_result, error_trace, stdout = execute_generated_code(code, dfs, file_path, raw_dfs=raw_dfs)
        retries_used = 0

        while is_invalid_result(raw_result, error_trace) and retries_used < retries_limit:
            retries_used += 1
            if error_trace:
                reason = error_trace[-1500:]
            else:
                reason = (f"FINAL_ANSWER was invalid or empty ({repr(raw_result)}). Check your filters on "
                          "df['Row_Path'] and the column names against the table summary; if the parsed table looks "
                          "wrong, use `raw_dfs`.")
            if stdout:
                reason += f"\n\nYour code printed (use it to correct the code):\n{stdout[-1500:]}"
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
            raw_response = self.llm.generate_response(correction_prompt, system_prompt=SYSTEM_PROMPT, temperature=temperature)
            code = self.llm.extract_python_code(raw_response)
            raw_result, error_trace, stdout = execute_generated_code(code, dfs, file_path, raw_dfs=raw_dfs)

        used_fallback = False
        if is_invalid_result(raw_result, error_trace) and settings.enable_direct_fallback:
            used_fallback = True
            raw_result, error_trace = self.direct_answer(dfs, query, temperature), None

        formatted = format_answer(raw_result, query)

        return {
            "query": query,
            "raw_result": raw_result,
            "answer": formatted,
            "code": code,
            "retries": retries_used,
            "direct_fallback": used_fallback,
            "error": error_trace,
        }
