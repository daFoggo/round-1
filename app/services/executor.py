import io
import sys
import traceback
import datetime
import re
import pandas as pd
import openpyxl
from typing import Dict, Any, Tuple, Optional
from app.config import settings

def execute_generated_code(
    code: str,
    dfs: Dict[str, pd.DataFrame],
    file_path: str,
    timeout_seconds: Optional[int] = None
) -> Tuple[Optional[Any], Optional[str]]:
    timeout = timeout_seconds or settings.execution_timeout
    first_sheet_name = next(iter(dfs)) if dfs else ""
    local_env = {
        "dfs": dfs,
        "df": dfs.get(first_sheet_name) if first_sheet_name else None,
        "file_path": file_path,
        "pd": pd,
        "openpyxl": openpyxl,
        "re": re,
        "datetime": datetime,
        "FINAL_ANSWER": None,
    }

    stdout_buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_buf

    try:
        exec(code, local_env, local_env)
        final_ans = local_env.get("FINAL_ANSWER")
        stdout_output = stdout_buf.getvalue().strip()

        if final_ans is None and stdout_output:
            final_ans = stdout_output.split("\n")[-1].strip()

        return final_ans, None
    except Exception as e:
        tb = traceback.format_exc()
        return None, tb
    finally:
        sys.stdout = old_stdout
