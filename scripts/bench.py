"""Benchmark nhiều lần chạy và phân loại câu sai: lỗi hệ thống (sai >= 2 lần) hay nhiễu (sai 1 lần).

    python scripts/bench.py --runs 3 --sets p2,p4

Chạy trong container với repo mount vào /app (xem README mục 5.4). Mỗi lần chạy dùng đúng pipeline của CLI
(song song --workers). Kết quả: EM trung bình, token/câu, thời gian, và bảng tần suất sai theo từng câu.
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

import app.cli as cli


def load_truth(path):
    with open(path, encoding="utf-8-sig") as f:
        return {r[0]: r[1] for r in list(csv.reader(f))[1:] if len(r) >= 2}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--sets", default="p2,p4")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    summary = []
    for name in args.sets.split(","):
        data = f"data/{name}"
        truth = load_truth(f"{data}/sample_submission.csv")
        queries = {str(q["id"]): q["query"] for q in json.load(open(f"{data}/queries.json", encoding="utf-8-sig"))}
        wrong = defaultdict(list)
        scores, times = [], []
        for i in range(1, args.runs + 1):
            out = f"{args.out}/bench_{name}_{i}.csv"
            t = time.time()
            cli.run_cli(["--xlsx-dir", f"{data}/xlsx_files", "--queries", f"{data}/queries.json", "--output", out])
            times.append(time.time() - t)
            pred = load_truth(out)
            bad = [k for k in truth if pred.get(k, "") != truth[k]]
            scores.append(len(truth) - len(bad))
            for k in bad:
                wrong[k].append(pred.get(k, ""))
        summary.append((name, len(truth), scores, times))
        print(f"\n=== {name}: scores {scores} mean {sum(scores)/len(scores):.1f}/{len(truth)} | avg {sum(times)/len(times):.0f}s/run",
              flush=True)
        systematic = {k: v for k, v in wrong.items() if len(v) >= 2}
        noise = {k: v for k, v in wrong.items() if len(v) == 1}
        print(f"SYSTEMATIC (wrong in >=2/{args.runs} runs): {len(systematic)}")
        for k, v in sorted(systematic.items(), key=lambda kv: -len(kv[1])):
            print(f"  {k} {len(v)}/{args.runs} exp={truth[k]!r} got={v[:3]!r} | {queries[k][:90]}")
        print(f"NOISE (wrong once): {sorted(noise)}")


if __name__ == "__main__":
    main()
