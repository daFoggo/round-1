"""Dựng bộ đánh giá ngoài (đúng cấu trúc cuộc thi) từ RealHiTBench (https://huggingface.co/datasets/spzy/RealHiTBench).

    python scripts/build_external_set.py --n 50 --out data/p5

Dữ liệu nguồn: CC BY-NC 4.0, chỉ dùng để đánh giá cục bộ (data/external và data/p5 nằm trong .gitignore, không đưa vào gói nộp).
Chọn mỗi file bảng tối đa 1 câu loại Fact Checking / Numerical Reasoning có đáp án ngắn, lấy mẫu cố định (seed) và phân tầng
theo nguồn để không dồn vào một loại bảng.
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import urllib.request
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://huggingface.co/datasets/spzy/RealHiTBench/resolve/main"
KEEP_SUBTYPES = {"Value-Matching", "Calculation", "Counting", "Comparison", "Ranking",
                 "Multi-hop Fact Checking", "Multi-hop Numerical Reasoning", "Inference-based Fact Checking"}


def short_answer(a: str) -> bool:
    a = (a or "").strip()
    return 0 < len(a) <= 40 and "\n" not in a


def cell_fingerprint(path: str) -> frozenset:
    """Tập giá trị ô của một workbook; dùng để loại bảng đã có trong bộ công khai (p2/p4 lấy lại từ cùng nguồn)."""
    import openpyxl
    cells = set()
    for ws in openpyxl.load_workbook(path, data_only=True):
        for row in ws.iter_rows(values_only=True):
            cells.update(str(v).strip().lower() for v in row if v is not None)
    return frozenset(cells)


def known_fingerprints(dirs) -> list:
    import glob
    return [cell_fingerprint(p) for d in dirs for p in glob.glob(os.path.join(d, "xlsx_files", "*.xlsx"))]


def is_known(fp: frozenset, known: list) -> bool:
    return any(len(fp & k) >= 0.9 * max(len(fp), len(k)) for k in known)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa", default="data/external/realhitbench/QA_final.json")
    ap.add_argument("--cache", default="data/external/realhitbench/tables")
    ap.add_argument("--out", default="data/p5")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--suffix", default=" Answer with only the final value, without explanation.",
                    help="câu yêu cầu định dạng nối vào câu hỏi (đề thi luôn có yêu cầu kiểu này)")
    a = ap.parse_args()

    items = json.load(open(a.qa, encoding="utf-8"))["queries"]
    pool = [x for x in items
            if x["QuestionType"] in ("Fact Checking", "Numerical Reasoning")
            and x["SubQType"] in KEEP_SUBTYPES
            and short_answer(x["ProcessedAnswer"]) and not re.search(r"chart|plot|graph", x["Question"], re.I)]
    rnd = random.Random(a.seed)
    by_file = defaultdict(list)
    for x in pool:
        by_file[x["FileName"]].append(x)
    per_source = defaultdict(list)
    for fn, xs in by_file.items():
        x = rnd.choice(xs)
        per_source[x["Source"]].append(x)
    for xs in per_source.values():
        rnd.shuffle(xs)
    os.makedirs(os.path.join(a.out, "xlsx_files"), exist_ok=True)
    os.makedirs(a.cache, exist_ok=True)
    known = known_fingerprints(["data/p2", "data/p4"])
    picked, skipped = [], 0
    while len(picked) < a.n and any(per_source.values()):  # vòng tròn giữa các nguồn
        for src in sorted(per_source):
            if per_source[src] and len(picked) < a.n:
                x = per_source[src].pop()
                cached = os.path.join(a.cache, f"{x['FileName']}.xlsx")
                if not os.path.exists(cached):
                    urllib.request.urlretrieve(f"{BASE}/tables/{x['FileName']}.xlsx", cached)
                if is_known(cell_fingerprint(cached), known):
                    skipped += 1
                    continue
                picked.append(x)
    print(f"bỏ {skipped} bảng trùng với p2/p4")

    queries, truth = [], []
    for i, x in enumerate(picked, 1):
        fn = f"{x['FileName']}.xlsx"
        cached = os.path.join(a.cache, fn)
        if not os.path.exists(cached):
            urllib.request.urlretrieve(f"{BASE}/tables/{fn}", cached)
        with open(cached, "rb") as src, open(os.path.join(a.out, "xlsx_files", fn), "wb") as dst:
            dst.write(src.read())
        queries.append({"id": i, "file_name": fn, "query": x["Question"].strip() + a.suffix})
        truth.append((i, x["ProcessedAnswer"].strip(), x["Source"], x["SubQType"]))

    with open(os.path.join(a.out, "queries.json"), "w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)
    with open(os.path.join(a.out, "sample_submission.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "answer"])
        for i, ans, _, _ in truth:
            w.writerow([i, ans])
    with open(os.path.join(a.out, "meta.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "source", "subtype"])
        for i, _, src, sub in truth:
            w.writerow([i, src, sub])
    print(f"{len(queries)} câu / {len(set(q['file_name'] for q in queries))} file -> {a.out}")
    for src in sorted({t[2] for t in truth}):
        print(f"  {src}: {sum(1 for t in truth if t[2] == src)}")


if __name__ == "__main__":
    main()
