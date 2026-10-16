"""Suy ra layout (header / dữ liệu / cột nhãn) của sheet bị parse sai bằng MỘT lệnh gọi LLM, rồi để parser tất định dựng lại bảng.

Ý tưởng theo ST-Raptor (arXiv:2508.18190) và TreeThinker của RealHiTBench (arXiv:2506.13405): nhận diện cấu trúc đúng
trước khi hỏi đáp là đòn bẩy lớn nhất. Khác hai bài đó, ta chỉ gọi LLM cho sheet có dấu hiệu parse sai (`suspicious_sheets`)
và LLM chỉ trả về vài con số (dòng header, dòng dữ liệu, cột nhãn) — phần còn lại do parser tất định xử lý.
"""
import json
import re
from typing import Any, Dict, Optional

import openpyxl
import pandas as pd

LAYOUT_SYSTEM = (
    "You analyse the layout of one spreadsheet sheet and answer ONLY with a JSON object, no explanation."
)

LAYOUT_PROMPT = """Below is the top of a spreadsheet sheet. Each line is `r<N>: ` followed by the cells of Excel row N,
separated by ' | ' (empty cells are blank, so column positions are kept; columns are numbered 1,2,3... = A,B,C...).
Merged cell ranges are listed first (merged cells show their value only in the first cell).

SHEET '{sheet}' ({n_rows} rows x {n_cols} columns)
MERGED RANGES: {merged}
{grid}

Identify the main data table and answer with JSON:
{{"header_rows": [first_row, last_row], "data_start": row, "data_end": row, "label_cols": [column numbers]}}
- header_rows: Excel rows holding the COLUMN headers of the data (several rows when headers are multi-level, include
  unit rows such as 'HK$ thousand'); exclude titles, notes and blank rows above them.
- data_start / data_end: first and last Excel row of the data VALUES (exclude footnotes and notes after the table).
- label_cols: column numbers, left to right, that hold the ROW labels (the hierarchy of the row stub, e.g. [1, 2] when
  column A holds the group and column B the item). Do not include numeric value columns.
"""


def _merged_summary(file_path: str, sheet: str, limit: int = 24) -> str:
    try:
        ws = openpyxl.load_workbook(file_path, data_only=True)[sheet]
        rngs = [str(r) for r in list(ws.merged_cells.ranges)[:limit]]
        extra = len(ws.merged_cells.ranges) - len(rngs)
        return ", ".join(rngs) + (f" (+{extra} more)" if extra > 0 else "") if rngs else "none"
    except Exception:
        return "unknown"


def _grid(raw: pd.DataFrame, max_rows: int = 60, max_cols: int = 18, cell_chars: int = 22) -> str:
    lines = []
    for idx, row in raw.iloc[:, :max_cols].iterrows():
        cells = ["" if pd.isna(v) else str(v).replace("\n", " ").strip()[:cell_chars] for v in row.tolist()]
        if any(cells):
            lines.append(f"r{idx}: " + " | ".join(cells))
        if len(lines) >= max_rows:
            lines.append("...")
            break
    return "\n".join(lines)


def validate_layout(lay: Any, n_rows: int, n_cols: int) -> Optional[Dict[str, Any]]:
    """Chỉ nhận layout hợp lý; trả None nếu có giá trị sai/ngoài phạm vi."""
    try:
        h0, h1 = [int(x) for x in lay["header_rows"]]
        ds = int(lay["data_start"])
        de = int(lay["data_end"]) if lay.get("data_end") else n_rows
        cols = [int(c) for c in lay.get("label_cols", [])]
    except (KeyError, TypeError, ValueError):
        return None
    if not (1 <= h0 <= h1 < ds <= de <= n_rows):
        return None
    if any(c < 1 or c > n_cols for c in cols) or len(cols) > 4 or cols != sorted(set(cols)):
        return None
    return {"header_rows": [h0, h1], "data_start": ds, "data_end": de, "label_cols": cols}


def infer_layout(llm: Any, file_path: str, sheet: str, raw: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Một lệnh gọi LLM -> layout đã kiểm tra hợp lệ (hoặc None)."""
    prompt = LAYOUT_PROMPT.format(sheet=sheet, n_rows=raw.shape[0], n_cols=raw.shape[1],
                                  merged=_merged_summary(file_path, sheet), grid=_grid(raw))
    try:
        text = llm.generate_response(prompt, system_prompt=LAYOUT_SYSTEM)
    except Exception:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return validate_layout(json.loads(m.group(0)), raw.shape[0], raw.shape[1])
    except json.JSONDecodeError:
        return None
