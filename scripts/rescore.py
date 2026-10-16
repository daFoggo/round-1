"""Chấm lại các file bench đã có bằng bộ chuẩn hoá hiện tại của bench.py (không gọi LLM).

    python scripts/rescore.py --sets p6,p7 --dir output/ext1 --runs 3
"""
import argparse, csv, re, sys
sys.stdout.reconfigure(encoding="utf-8")
src = open("scripts/bench.py", encoding="utf-8").read()
ns = {"re": re}
exec(src[src.index("def _norm_part"):src.index("def same")], ns)
N = ns["_norm_answer"]
def load(p): return {r[0]: r[1] for r in list(csv.reader(open(p, encoding="utf-8-sig")))[1:] if len(r) >= 2}
ap = argparse.ArgumentParser(); ap.add_argument("--sets", default="p6,p7"); ap.add_argument("--dir", default="output/ext1"); ap.add_argument("--runs", type=int, default=3)
a = ap.parse_args()
for name in a.sets.split(","):
    truth = load(f"data/{name}/sample_submission.csv")
    sc = []
    for i in range(1, a.runs + 1):
        pred = load(f"{a.dir}/bench_{name}_{i}.csv")
        sc.append(sum(N(pred.get(k, "")) == N(v) for k, v in truth.items()))
    print(f"{name}: {sc} mean {sum(sc)/len(sc):.1f}/{len(truth)} ({sum(sc)/len(sc)/len(truth):.1%})")
