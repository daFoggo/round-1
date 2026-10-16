import io
import signal
import sys
import threading
import traceback
import datetime
import re
import pandas as pd
import openpyxl
from typing import Dict, Any, Tuple, Optional
from app.config import settings


class ExecutionTimeout(Exception):
    pass


def _raise_timeout(signum, frame):
    raise ExecutionTimeout("Generated code exceeded the execution time limit.")

def execute_generated_code(
    code: str,
    dfs: Dict[str, pd.DataFrame],
    file_path: str,
    timeout_seconds: Optional[int] = None,
    raw_dfs: Optional[Dict[str, pd.DataFrame]] = None,
) -> Tuple[Optional[Any], Optional[str], str]:
    """Chạy code do LLM sinh. Trả về (FINAL_ANSWER, traceback, stdout).
    Dùng bản sao dữ liệu để các câu hỏi trên cùng một file không ảnh hưởng nhau."""
    timeout = timeout_seconds or settings.execution_timeout
    dfs = {k: v.copy() for k, v in dfs.items()}
    raw_dfs = {k: v.copy() for k, v in (raw_dfs or {}).items()}
    first_sheet_name = next(iter(dfs)) if dfs else ""
    local_env = {
        "dfs": dfs,
        "df": dfs.get(first_sheet_name) if first_sheet_name else None,
        "file_path": file_path,
        "raw_dfs": raw_dfs,
        "pd": pd,
        "openpyxl": openpyxl,
        "re": re,
        "datetime": datetime,
        "FINAL_ANSWER": None,
    }

    # Timeout bằng SIGALRM (Linux/Docker, main thread); nơi khác chạy không giới hạn
    use_alarm = hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread()
    old_handler = None

    stdout_buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_buf

    try:
        if use_alarm:
            old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
            signal.alarm(timeout)
        exec(code, local_env, local_env)
        final_ans = local_env.get("FINAL_ANSWER")
        return final_ans, None, stdout_buf.getvalue().strip()
    except BaseException:  # gồm cả ExecutionTimeout và SystemExit từ code sinh ra
        return None, traceback.format_exc(), stdout_buf.getvalue().strip()
    finally:
        if use_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        sys.stdout = old_stdout
