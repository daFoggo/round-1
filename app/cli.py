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
import os
import sys
import time

from app.config import settings
from app.services.pipeline import QAPipeline


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Tai Nang 2026 - Excel Table QA")
    parser.add_argument("--xlsx-dir", "--input_dir", dest="xlsx_dir", default="xlsx_files",
                        help="Thư mục chứa các tệp .xlsx")
    parser.add_argument("--queries", default="queries.json", help="Đường dẫn queries.json")
    parser.add_argument("--output", default="submission.csv", help="Đường dẫn submission.csv")
    parser.add_argument("--openrouter-key", default=None,
                        help="OpenRouter API key (fallback: env OPENROUTER_API_KEY)")
    parser.add_argument("--openrouter-model", default=None,
                        help="Model ID (mặc định: qwen/qwen3.7-flash)")
    parser.add_argument("--openrouter-base-url", default=None,
                        help="Base URL (mặc định: https://openrouter.ai/api/v1)")
    parser.add_argument("--provider", default=None,
                        help="openrouter (mặc định) hoặc gemini (chỉ để thử nghiệm cục bộ)")
    return parser.parse_args(argv)


def write_submission(path: str, rows) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "answer"])
        writer.writerows(rows)


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

    provider = args.provider
    if provider is None and (args.openrouter_key or args.openrouter_model or args.openrouter_base_url):
        provider = "openrouter"

    pipeline = QAPipeline(
        provider=provider,
        openrouter_key=args.openrouter_key,
        openrouter_model=args.openrouter_model,
        openrouter_base_url=args.openrouter_base_url,
    )
    log(f"Provider: {pipeline.llm.provider} | Model: {pipeline.llm.active_model}")
    log(f"Processing {len(queries)} queries...")

    rows = []
    seen_ids = set()
    start = time.time()
    for idx, item in enumerate(queries, 1):
        qid = item.get("id")
        if qid in seen_ids:
            log(f"[{idx}/{len(queries)}] Duplicate id {qid} in queries, skipped")
            continue
        seen_ids.add(qid)

        fpath = os.path.join(args.xlsx_dir, str(item.get("file_name", "")))
        pred = ""
        if not os.path.isfile(fpath):
            log(f"[{idx}/{len(queries)}] Warning: File not found: {fpath}")
        else:
            try:
                res = pipeline.answer_query(fpath, str(item.get("query", "")))
                pred = res["answer"]
            except Exception as e:
                log(f"[{idx}/{len(queries)}] Error processing query {qid}: {e!r}")

        # Đáp án phải nằm trên một dòng, không kèm giải thích
        pred = " ".join(str(pred).split())
        log(f"[{idx}/{len(queries)}] ID: {qid} | Answer: '{pred}'")
        rows.append([qid, pred])

    write_submission(args.output, rows)
    log(f"Finished in {time.time() - start:.1f}s | "
        f"tokens: {pipeline.llm.usage['total_tokens']} | Submission saved to {args.output}")
    return 0


def main() -> None:
    sys.exit(run_cli())
