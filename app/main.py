import argparse
import csv
import json
import os
import sys
from fastapi import FastAPI
from app.config import settings
from app.routers import health_router, qa_router
from app.services.pipeline import QAPipeline

# Khởi tạo FastAPI Application
app = FastAPI(
    title=settings.app_name,
    description="Hệ thống hỏi đáp bảng tính Excel cho cuộc thi AI Tài Năng 2026",
    version="1.0.0"
)

# Đăng ký các router
app.include_router(health_router)
app.include_router(qa_router)

def run_cli():
    parser = argparse.ArgumentParser(description="AI Tai Nang 2026 - Round 1: Excel Question Answering")
    parser.add_argument("--input_dir", type=str, default="xlsx_files", help="Path to directory containing .xlsx files")
    parser.add_argument("--queries", type=str, default="queries.json", help="Path to queries.json file")
    parser.add_argument("--output", type=str, default="submission.csv", help="Path to output submission.csv")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider: gemini or openrouter")
    args = parser.parse_args()

    if not os.path.exists(args.queries):
        print(f"Error: Queries file not found at {args.queries}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.input_dir):
        print(f"Error: Excel directory not found at {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    with open(args.queries, "r", encoding="utf-8") as f:
        queries = json.load(f)

    pipeline = QAPipeline(provider=args.provider)
    submission_rows = [["id", "answer"]]

    print(f"Processing {len(queries)} queries...")
    for idx, item in enumerate(queries, 1):
        qid = item["id"]
        fname = item["file_name"]
        qtext = item["query"]
        fpath = os.path.join(args.input_dir, fname)

        if not os.path.exists(fpath):
            print(f"[{idx}/{len(queries)}] Warning: File not found: {fpath}")
            pred = ""
        else:
            try:
                res = pipeline.answer_query(fpath, qtext)
                pred = res["answer"]
            except Exception as e:
                print(f"[{idx}/{len(queries)}] Error processing query {qid}: {e}")
                pred = ""

        print(f"[{idx}/{len(queries)}] ID: {qid} | Answer: '{pred}'")
        submission_rows.append([qid, pred])

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(submission_rows)

    print(f"Finished! Submission saved to {args.output}")

if __name__ == "__main__":
    run_cli()
