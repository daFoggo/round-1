"""Debug 1 câu: in bảng đã parse, code LLM sinh ra, kết quả và lỗi.

    python scripts/debug_query.py --data data/p2 --id 20 [--show-summary]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.services.pipeline import QAPipeline
from app.services.preprocessor import generate_table_summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/p2")
    ap.add_argument("--id", required=True)
    ap.add_argument("--show-summary", action="store_true")
    ap.add_argument("--no-run", action="store_true", help="chỉ in bảng, không gọi LLM")
    a = ap.parse_args()

    with open(os.path.join(a.data, "queries.json"), encoding="utf-8-sig") as f:
        item = next(q for q in json.load(f) if str(q["id"]) == str(a.id))
    path = os.path.join(a.data, "xlsx_files", item["file_name"])
    print(f"## {item['id']} {item['file_name']}\n{item['query']}\n")

    pipe = QAPipeline()
    dfs = pipe.get_parsed_workbook(path)
    if a.show_summary or a.no_run:
        print(generate_table_summary(dfs)[:6000])
    if a.no_run:
        return
    res = pipe.answer_query(path, item["query"])
    print("--- CODE ---\n" + (res["code"] or ""))
    print(f"--- RESULT --- raw={res['raw_result']!r} answer={res['answer']!r} retries={res['retries']}")
    if res.get("error"):
        print("--- ERROR ---\n" + res["error"][-800:])


if __name__ == "__main__":
    main()
