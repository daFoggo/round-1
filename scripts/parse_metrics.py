"""Đo chất lượng parse trên hàng loạt file .xlsx KHÔNG cần câu hỏi/đáp án và KHÔNG gọi LLM.

    python scripts/parse_metrics.py --dir data/external/realhitbench/tables --out data/external/parse_metrics.csv

Chỉ số cho mỗi file (so bảng đã parse với ô thật của sheet):
  coverage : tỷ lệ ô số của sheet (đa tập) xuất hiện trong bảng parse (ô dữ liệu, hoặc số nằm trong tên cột / Row_Path / ô chữ)
  excess   : tỷ lệ ô số dữ liệu của bảng parse KHÔNG có trong sheet gốc (nhân đôi / bịa ra)
  bad_cols : số cột có tên chứa dữ liệu (>= 6 dấu ' | ' hoặc dài > 150 ký tự)
  generic  : tỷ lệ cột không có tên (Col_N / Column_N)
  empty_rp : tỷ lệ dòng có Row_Path rỗng
File 'ok' khi coverage >= 0.95, excess <= 0.05, bad_cols == 0, generic <= 0.4, empty_rp <= 0.5, có ít nhất 1 dòng.

Chia dev/test cố định theo hash tên file (70/30): chỉ xem chi tiết lỗi của DEV; TEST chỉ lấy số tổng hợp để ước lượng
không thiên lệch (tránh sửa theo từng file của tập kiểm tra).
"""
import argparse
import csv
import hashlib
import multiprocessing as mp
import os
import re
import signal
import sys
import time
import warnings
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import openpyxl
import pandas as pd

from app.services.preprocessor import parse_numeric, parse_workbook

NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def split_of(name: str) -> str:
    return "dev" if int(hashlib.md5(name.encode()).hexdigest(), 16) % 10 < 7 else "test"


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return None if v != v else round(float(v), 6)  # NaN (ô trống) không phải số
    if isinstance(v, str):
        n = parse_numeric(v)
        return None if n is None else round(float(n), 6)
    return None


def _numbers_in(text: str):
    out = []
    for tok in NUM_RE.findall(str(text)):
        try:
            out.append(round(float(tok.replace(",", "")), 6))
        except ValueError:
            pass
    return out


def raw_numbers(path: str) -> Counter:
    c = Counter()
    for ws in openpyxl.load_workbook(path, data_only=True):
        for row in ws.iter_rows(values_only=True):
            for v in row:
                n = _num(v)
                if n is not None:
                    c[n] += 1
    return c


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def measure(path: str) -> dict:
    name = os.path.basename(path)
    res = {"file": name, "split": split_of(name), "error": "", "tables": 0, "rows": 0, "coverage": 0.0, "excess": 0.0,
           "bad_cols": 0, "generic": 0.0, "empty_rp": 0.0, "secs": 0.0}
    t0 = time.time()
    try:
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(90)
        raw = raw_numbers(path)
        dfs = parse_workbook(path)
        signal.alarm(0)
        parsed_data, parsed_any = Counter(), Counter()
        bad = generic = ncols = rows = empty = 0
        for df in dfs.values():
            rows += len(df)
            empty += int((df["Row_Path"].fillna("").astype(str).str.strip() == "").sum())
            for col in df.columns:
                parsed_any.update(_numbers_in(col))
            for rp in df["Row_Path"].dropna():
                parsed_any.update(_numbers_in(rp))
            for col in df.columns[3:]:
                name_c = str(col)
                ncols += 1
                if name_c.count(" | ") >= 6 or len(name_c) > 150:
                    bad += 1
                if re.fullmatch(r"(Col|Column)_\d+", name_c):
                    generic += 1
                for v in df[col].tolist():
                    n = _num(v)
                    if n is not None:
                        parsed_data[n] += 1
                    elif isinstance(v, str):
                        parsed_any.update(_numbers_in(v))
        parsed_all = parsed_data + parsed_any
        total_raw = sum(raw.values())
        matched = sum(min(c, parsed_all.get(v, 0)) for v, c in raw.items())
        total_parsed = sum(parsed_data.values())
        excess = sum(max(0, c - raw.get(v, 0)) for v, c in parsed_data.items())
        res.update(tables=len(dfs), rows=rows, coverage=round(matched / total_raw, 4) if total_raw else 1.0,
                   excess=round(excess / total_parsed, 4) if total_parsed else 0.0, bad_cols=bad,
                   generic=round(generic / ncols, 4) if ncols else 0.0,
                   empty_rp=round(empty / rows, 4) if rows else 1.0)
    except _Timeout:
        res["error"] = "timeout"
    except Exception as e:  # noqa: BLE001
        res["error"] = f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        signal.alarm(0)
    res["secs"] = round(time.time() - t0, 1)
    reasons = []
    if res["error"]:
        reasons.append("error")
    else:
        if res["rows"] < 1:
            reasons.append("no_rows")
        if res["coverage"] < 0.95:
            reasons.append("coverage")
        if res["excess"] > 0.05:
            reasons.append("excess")
        if res["bad_cols"]:
            reasons.append("bad_cols")
        if res["generic"] > 0.4:
            reasons.append("generic")
        if res["empty_rp"] > 0.5:
            reasons.append("empty_rp")
    res["reasons"] = "+".join(reasons)
    res["ok"] = int(not reasons)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/external/realhitbench/tables")
    ap.add_argument("--out", default="data/external/parse_metrics.csv")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    files = sorted(os.path.join(a.dir, f) for f in os.listdir(a.dir) if f.endswith(".xlsx") and not f.startswith("~$"))
    if a.limit:
        files = files[:a.limit]
    with mp.get_context("fork").Pool(a.workers) as pool:
        rows = pool.map(measure, files, chunksize=4)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    df = pd.DataFrame(rows)
    print(f"{len(df)} file | ok {df['ok'].mean():.1%}")
    for sp in ("dev", "test"):
        d = df[df["split"] == sp]
        print(f"  {sp}: {len(d)} file, ok {d['ok'].mean():.1%}, coverage TB {d['coverage'].mean():.3f}, "
              f"excess TB {d['excess'].mean():.3f}")
    print("Lý do lỗi (DEV):")
    reasons = Counter(r for rs in df[df["split"] == "dev"]["reasons"] for r in rs.split("+") if r)
    for r, c in reasons.most_common():
        print(f"  {r}: {c}")


if __name__ == "__main__":
    main()
