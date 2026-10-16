import json
import os
import csv
import time
from app.services.pipeline import QAPipeline

def run_evaluation(data_dir: str = "data/p4", limit: int = None, output_csv: str = "submission.csv"):
    pipeline = QAPipeline()

    with open(os.path.join(data_dir, "queries.json"), "r", encoding="utf-8-sig") as f:
        queries = json.load(f)

    ground_truth = {}
    truth_path = os.path.join(data_dir, "sample_submission.csv")
    if os.path.exists(truth_path):
        with open(truth_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 2:
                    ground_truth[row[0]] = row[1]

    if limit:
        queries = queries[:limit]

    print(f"=== Starting Evaluation on {len(queries)} Queries ===", flush=True)
    results = []
    correct_count = 0
    total_time = 0.0

    submission_rows = [["id", "answer"]]

    for idx, item in enumerate(queries, 1):
        qid = item["id"]
        fname = item["file_name"]
        qtext = item["query"]
        fpath = os.path.join(data_dir, "xlsx_files", fname)
        expected = ground_truth.get(qid, "N/A")

        print(f"\n[{idx}/{len(queries)}] {qid} ({fname})...", flush=True)
        res = pipeline.answer_query(fpath, qtext)
        pred = res["answer"]
        is_match = (pred == expected)
        if is_match:
            correct_count += 1
        total_time += res["elapsed_seconds"]

        print(f"  Query: {qtext}", flush=True)
        print(f"  Pred:     '{pred}'", flush=True)
        print(f"  Expected: '{expected}'", flush=True)
        print(f"  Match: {is_match} | Time: {res['elapsed_seconds']}s | Retries: {res['retries']}", flush=True)

        submission_rows.append([qid, pred])
        results.append({
            "id": qid,
            "file_name": fname,
            "query": qtext,
            "predicted": pred,
            "expected": expected,
            "match": is_match,
            "elapsed": res["elapsed_seconds"],
            "retries": res["retries"]
        })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(submission_rows)

    print("\n" + "="*50, flush=True)
    print(f"EVALUATION SUMMARY:", flush=True)
    print(f"Total Queries: {len(queries)}", flush=True)
    print(f"Exact Matches: {correct_count}/{len(queries)} ({correct_count/len(queries)*100:.1f}%)", flush=True)
    print(f"Total Time:    {total_time:.2f}s (Avg: {total_time/len(queries):.2f}s per query)", flush=True)
    print(f"Saved submission to: {output_csv}", flush=True)
    print("="*50, flush=True)

    return results

if __name__ == "__main__":
    import sys
    run_evaluation(sys.argv[1] if len(sys.argv) > 1 else "data/p4")
