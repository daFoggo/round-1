"""Phân loại tự động các câu sai hệ thống của bench (không đọc từng câu).

    python scripts/triage_failures.py --sets p6,p7 --dir output/ext1 --runs 3

Nhóm: near_numeric (lệch <= 2%: làm tròn/độ chính xác), format (đáp án chứa nhau: dài dòng/thiếu đơn vị), failure
(trả về 0/unknown/not found/lỗi: không truy xuất được), wrong_type (đúng/sai kiểu: số vs chữ), other (giá trị khác hẳn).
"""
import argparse, csv, json, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

FAIL = re.compile(r"^(0|0\.0+|error|not found|no data|unknown|n/?a|none|nan|insufficient|data not|cannot|unable|)$", re.I)

def norm(s):
    s = str(s).strip().lower().replace("%", "").replace("$", "")
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)
    return re.sub(r"\s*,\s*", ",", re.sub(r"\s+", " ", s)).strip(" .\"'")

def num(s):
    try: return float(norm(s))
    except ValueError: return None

def load(p):
    return {r[0]: r[1] for r in list(csv.reader(open(p, encoding="utf-8-sig")))[1:] if len(r) >= 2}

def classify(gold, got):
    g, a = norm(gold), norm(got)
    gn, an = num(gold), num(got)
    if FAIL.match(a): return "failure"
    if gn is not None and an is not None:
        if abs(gn - an) <= 0.02 * max(abs(gn), 1e-9): return "near_numeric"
        if abs(abs(gn) - abs(an)) <= 0.02 * max(abs(gn), 1e-9): return "sign"
        return "other"
    if (gn is None) != (an is None): return "wrong_type"
    if g and (g in a or a in g): return "format"
    return "other"

ap = argparse.ArgumentParser()
ap.add_argument("--sets", default="p6,p7"); ap.add_argument("--dir", default="output/ext1"); ap.add_argument("--runs", type=int, default=3)
ap.add_argument("--show", type=int, default=0, help="in n ví dụ mỗi nhóm")
a = ap.parse_args()
for name in a.sets.split(","):
    truth = load(f"data/{name}/sample_submission.csv")
    queries = {str(q["id"]): q["query"] for q in json.load(open(f"data/{name}/queries.json", encoding="utf-8-sig"))}
    runs = [load(f"{a.dir}/bench_{name}_{i}.csv") for i in range(1, a.runs + 1)]
    cat, ex = Counter(), {}
    for k in truth:
        wrong = [r.get(k, "") for r in runs if norm(r.get(k, "")) != norm(truth[k])]
        if len(wrong) >= 2:
            c = Counter(classify(truth[k], w) for w in wrong).most_common(1)[0][0]
            cat[c] += 1; ex.setdefault(c, []).append((k, truth[k], wrong[0], queries[k][:90]))
    n = sum(cat.values())
    print(f"\n== {name}: {n} câu sai hệ thống / {len(truth)}")
    for c, v in cat.most_common(): print(f"  {c:13} {v:3} ({v/n:.0%})")
    for c, items in ex.items():
        for it in items[:a.show]: print(f"    [{c}] {it[0]} gold={it[1]!r} got={it[2]!r} | {it[3]}")
