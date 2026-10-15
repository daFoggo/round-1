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
        stdout_output = stdout_buf.getvalue().strip()

        if final_ans is None and stdout_output:
            final_ans = stdout_output.split("\n")[-1].strip()

        return final_ans, None
    except Exception as e:
        tb = traceback.format_exc()
        return None, tb
    finally:
        if use_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        sys.stdout = old_stdout
