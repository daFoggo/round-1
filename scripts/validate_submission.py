"""Kiểm tra submission.csv theo HUONG_DAN_NOP_BAI.md (mục 4).

    python scripts/validate_submission.py --queries queries.json --submission submission.csv [--truth sample_submission.csv]
"""
import argparse
import csv
import json
import sys


def validate(queries_path: str, submission_path: str) -> list:
    errors = []
    with open(queries_path, "r", encoding="utf-8-sig") as f:
        expected_ids = [str(q["id"]) for q in json.load(f)]

    try:
        with open(submission_path, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return ["File không phải UTF-8"]
    if text.startswith("﻿"):
        errors.append("File có BOM (UTF-8-SIG) – nên ghi UTF-8 không BOM")
        text = text[1:]

    rows = list(csv.reader(text.splitlines()))
    if not rows or rows[0] != ["id", "answer"]:
        errors.append(f"Header phải là 'id,answer', nhận được: {rows[0] if rows else None}")
    body = rows[1:]

    for i, r in enumerate(body, 2):
        if len(r) != 2:
            errors.append(f"Dòng {i} có {len(r)} cột (cần 2): {r}")

    got_ids = [r[0] for r in body if r]
    dups = sorted({x for x in got_ids if got_ids.count(x) > 1})
    missing = sorted(set(expected_ids) - set(got_ids))
    extra = sorted(set(got_ids) - set(expected_ids))
    if dups:
        errors.append(f"id bị trùng: {dups}")
    if missing:
        errors.append(f"Thiếu id: {missing}")
    if extra:
        errors.append(f"Thừa id: {extra}")
    empty = [r[0] for r in body if len(r) == 2 and not r[1].strip()]
    if empty:
        print(f"[warn] {len(empty)} câu trả lời rỗng: {empty}")
    return errors


def exact_match(submission_path: str, truth_path: str) -> None:
    def load(p):
        with open(p, "r", encoding="utf-8-sig") as f:
            return {r[0]: r[1] for r in list(csv.reader(f))[1:] if len(r) >= 2}
    pred, truth = load(submission_path), load(truth_path)
    correct = [k for k in truth if pred.get(k) == truth[k]]
    print(f"Exact Match: {len(correct)}/{len(truth)}")
    for k in truth:
        if pred.get(k) != truth[k]:
            print(f"  ✗ {k}: pred={pred.get(k)!r} expected={truth[k]!r}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="queries.json")
    ap.add_argument("--submission", default="submission.csv")
    ap.add_argument("--truth", default=None, help="CSV đáp án để tính Exact Match (tuỳ chọn)")
    args = ap.parse_args()

    errors = validate(args.queries, args.submission)
    if errors:
        print("INVALID submission:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("VALID submission: header, UTF-8, mỗi id xuất hiện đúng một lần.")
    if args.truth:
        exact_match(args.submission, args.truth)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
