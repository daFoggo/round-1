"""Đối chiếu kích thước bảng / độ dài TABLE SUMMARY với tỷ lệ sai trên các bộ ngoài (không gọi LLM).

    python scripts/size_vs_error.py --sets p6,p7 --runs-dir output/cnt_{set}

Dùng để quyết định có cần thu hẹp ngữ cảnh (bảng con theo câu hỏi) hay không: nếu tỷ lệ sai tăng theo số dòng/cột
hoặc theo việc danh sách Row_Path bị cắt, thì phần thiếu ngữ cảnh là nguyên nhân đáng xử lý.
"""
import argparse
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from app.services.preprocessor import generate_table_summary, parse_workbook
from scripts.bench import load_truth, same


def bucket(v, edges):
    for e in edges:
        if v <= e:
            return f"<={e}"
    return f">{edges[-1]}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", default="p6,p7")
    ap.add_argument("--runs-dir", default="output/cnt_{set}")
    args = ap.parse_args()

    rows = []
    for name in args.sets.split(","):
        data = f"data/{name}"
        truth = load_truth(f"{data}/sample_submission.csv")
        qs = json.load(open(f"{data}/queries.json", encoding="utf-8-sig"))
        preds = [load_truth(p) for p in sorted(glob.glob(f"{args.runs_dir.format(set=name)}/bench_{name}_*.csv"))]
        cache = {}
        for q in qs:
            fn = q["file_name"]
            if fn not in cache:
                dfs = parse_workbook(f"{data}/xlsx_files/{fn}")
                summ = generate_table_summary(dfs)
                n_rp = sum(df["Row_Path"].nunique() for df in dfs.values())
                cache[fn] = dict(rows=sum(len(d) for d in dfs.values()), cols=max([d.shape[1] for d in dfs.values()] or [0]),
                                 rowpaths=n_rp, truncated=any(df["Row_Path"].nunique() > 150 for df in dfs.values()),
                                 chars=len(summ))
            k = str(q["id"])
            wrong = sum(not same(p.get(k, ""), truth[k], True) for p in preds)
            rows.append(dict(set=name, id=k, wrong=wrong / max(1, len(preds)), **cache[fn]))

    def report(key, edges=None):
        groups = {}
        for r in rows:
            g = str(r[key]) if edges is None else bucket(r[key], edges)
            groups.setdefault(g, []).append(r["wrong"])
        print(f"\n-- error rate by {key}")
        for g, v in sorted(groups.items(), key=lambda kv: kv[0]):
            print(f"  {g:>8}: n={len(v):4d} err={sum(v) / len(v):.2f}")

    print(f"questions: {len(rows)}, overall err={sum(r['wrong'] for r in rows) / len(rows):.2f}")
    report("rows", [20, 50, 100, 150, 300])
    report("cols", [5, 10, 15, 25, 40])
    report("truncated")
    report("chars", [2000, 4000, 8000, 16000])


if __name__ == "__main__":
    main()
