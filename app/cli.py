"""CLI entrypoint dùng cho hệ thống chấm (ENTRYPOINT ["python", "main.py"]).

Hệ thống chấm truyền 6 tham số:
  --xlsx-dir /input/xlsx_files --queries /input/queries.json --output /output/submission.csv
  --openrouter-key <key> --openrouter-model qwen/qwen3.7-flash
  --openrouter-base-url https://openrouter.ai/api/v1

Log ghi ra stderr; tệp kết quả chỉ chứa CSV `id,answer`.
"""
import argparse
import csv
import json
import multiprocessing
import os
import sys
import time

from app.config import settings
from app.services.pipeline import QAPipeline


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Tai Nang 2026 - Excel Table QA")
    parser.add_argument("--xlsx-dir", "--input_dir", dest="xlsx_dir", default="data/p2/xlsx_files",
                        help="Thư mục chứa các tệp .xlsx")
    parser.add_argument("--queries", default="data/p2/queries.json", help="Đường dẫn queries.json")
    parser.add_argument("--output", default="submission.csv", help="Đường dẫn submission.csv")
    parser.add_argument("--openrouter-key", default=None,
                        help="OpenRouter API key (fallback: env OPENROUTER_API_KEY)")
    parser.add_argument("--openrouter-model", default=None,
                        help="Model ID (mặc định: qwen/qwen3.7-flash)")
    parser.add_argument("--openrouter-base-url", default=None,
                        help="Base URL (mặc định: https://openrouter.ai/api/v1)")
    parser.add_argument("--workers", type=int, default=settings.workers,
                        help="Số tiến trình chạy song song (mặc định theo cấu hình)")
    return parser.parse_args(argv)


def _id_sort_key(row):
    """BTC: submission.csv sắp xếp theo id tăng dần (id là số tự nhiên)."""
    try:
        return (0, int(row[0]), "")
    except (TypeError, ValueError):
        return (1, 0, str(row[0]))


def write_submission(path: str, rows) -> None:
    rows = sorted(rows, key=_id_sort_key)
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "answer"])
        writer.writerows(rows)


# ---- Worker (mỗi tiến trình có luồng chính riêng nên SIGALRM timeout của executor hoạt động) ----
_WORKER_PIPELINE = None


def _init_worker(cfg: dict) -> None:
    global _WORKER_PIPELINE
    _WORKER_PIPELINE = QAPipeline(**cfg)


def _solve(task: tuple) -> dict:
    idx, qid, fpath, query = task
    pipe = _WORKER_PIPELINE
    before = dict(pipe.llm.usage)
    pred, err = "", None
    try:
        pred = pipe.answer_query(fpath, query)["answer"]
    except Exception as e:  # một câu lỗi không được làm hỏng cả lượt chạy
        err = repr(e)
    after = pipe.llm.usage
    return {"idx": idx, "id": qid, "answer": pred, "error": err,
            "usage": {k: after[k] - before[k] for k in after}}


def run_cli(argv=None) -> int:
    args = parse_args(argv)

    if not os.path.isfile(args.queries):
        log(f"Error: Queries file not found at {args.queries}")
        return 1
    if not os.path.isdir(args.xlsx_dir):
        log(f"Error: Excel directory not found at {args.xlsx_dir}")
        return 1

    with open(args.queries, "r", encoding="utf-8-sig") as f:
        queries = json.load(f)

    cfg = dict(openrouter_key=args.openrouter_key,
               openrouter_model=args.openrouter_model, openrouter_base_url=args.openrouter_base_url)

    tasks, rows, seen_ids = [], {}, set()
    for idx, item in enumerate(queries):
        qid = item.get("id")
        if qid in seen_ids:
            log(f"Duplicate id {qid} in queries, skipped")
            continue
        seen_ids.add(qid)
        fpath = os.path.join(args.xlsx_dir, str(item.get("file_name", "")))
        if not os.path.isfile(fpath):
            log(f"[{qid}] Warning: File not found: {fpath}")
            rows[qid] = ""
            continue
        tasks.append((idx, qid, fpath, str(item.get("query", ""))))

    workers = max(1, min(args.workers, len(tasks) or 1))
    total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
             "reasoning_tokens": 0, "cost": 0.0, "calls": 0}
    start = time.time()
    deadline = start + settings.run_deadline_seconds
    log(f"Model: {args.openrouter_model or settings.openrouter_model} | queries: {len(queries)} | workers: {workers}")

    def collect(r: dict) -> None:
        rows[r["id"]] = " ".join(str(r["answer"]).split())  # đáp án một dòng, không giải thích
        for k in total:
            total[k] += r["usage"].get(k, 0)
        msg = f" | ERROR {r['error']}" if r["error"] else ""
        log(f"[{len(rows)}/{len(queries)}] ID: {r['id']} | Answer: '{rows[r['id']]}'{msg}")

    if tasks:
        if workers == 1:
            _init_worker(cfg)
            for t in tasks:
                collect(_solve(t))
        else:
            ctx = multiprocessing.get_context("fork")
            pool = ctx.Pool(workers, initializer=_init_worker, initargs=(cfg,))
            try:
                it = pool.imap_unordered(_solve, tasks)
                for _ in tasks:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        raise multiprocessing.TimeoutError
                    collect(it.next(timeout=remaining))
            except multiprocessing.TimeoutError:
                log("Deadline reached: writing the answers collected so far")
            finally:
                pool.terminate()
                pool.join()

    for item in queries:  # câu chưa có kết quả (quá hạn/lỗi) -> chuỗi rỗng
        rows.setdefault(item.get("id"), "")
    write_submission(args.output, [[qid, ans] for qid, ans in rows.items()])
    log(f"Finished in {time.time() - start:.1f}s | calls: {total['calls']} | "
        f"tokens: {total['total_tokens']} (reasoning {total['reasoning_tokens']}) | "
        f"cost: ${total['cost']:.4f} | Submission saved to {args.output}")
    return 0


def main() -> None:
    sys.exit(run_cli())
