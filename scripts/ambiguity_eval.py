"""Bộ test cho câu hỏi mơ hồ "across all <nhóm cột>" – đáp án tính trực tiếp từ ô Excel.

Mục đích: kiểm tra thay đổi prompt/summary không overfit 1 câu (p4_q007) và không làm hỏng
trường hợp loại trừ rõ ràng. Quy ước đáp án (theo p4_q007): "all X" = mọi cột cùng cấp header
được liệt kê, kể cả cột Total; có "excluding the Total columns" thì chỉ lấy cột lá.

    python scripts/ambiguity_eval.py
"""
import json
import time

from app.services.preprocessor import parse_workbook
from app.services.pipeline import QAPipeline

F = "xlsx_files/p4_t04.xlsx"
TWO = "Answer with only the number rounded to two decimal places."


def _row(df, row_path):
    return df[df["Row_Path"] == row_path].iloc[0]


def expected_mean(df, row_path, exclude_total=False):
    cols = [c for c in df.columns if c.startswith("2023 | ")]
    if exclude_total:
        cols = [c for c in cols if not c.split(" | ")[-1].startswith("Total")]
    return f"{_row(df, row_path)[cols].astype(float).mean():.2f}"


CASES = [
    # (id, row_path, câu hỏi, exclude_total)
    ("amb01", "Men | Unemployment rate",
     f"What was the average unemployment rate across all education levels for men? {TWO}", False),
    ("amb02", "TOTAL | Participation rate",
     f"What is the mean participation rate across all education levels for the whole population? {TWO}", False),
    ("amb03", "Women | Employment-population ratio",
     f"What was the average employment-population ratio across all education levels for women? {TWO}", False),
    ("amb04", "Men | Participation rate",
     f"Across every education level, what is the average participation rate of men? {TWO}", False),
    ("amb05", "TOTAL | Unemployment rate",
     f"What is the average unemployment rate over all education levels for the total population? {TWO}", False),
    # Loại trừ rõ ràng – không được kéo cột Total vào
    ("amb06", "Women | Unemployment rate",
     f"What was the average unemployment rate across the education levels for women, excluding the 'Total' columns? {TWO}", True),
    ("amb07", "Men | Employment-population ratio",
     f"Averaging only the individual education levels (not the Total columns), what was the employment-population ratio for men? {TWO}", True),
]


def main() -> None:
    df = next(iter(parse_workbook(F).values()))
    pipe = QAPipeline()
    ok, details = 0, []
    for cid, rp, q, excl in CASES:
        exp = expected_mean(df, rp, excl)
        t = time.time()
        res = pipe.answer_query(F, q)
        match = res["answer"] == exp
        ok += match
        print(f"{cid} {'OK ' if match else 'FAIL'} pred={res['answer']!r} exp={exp!r} ({time.time()-t:.1f}s, retries={res['retries']})", flush=True)
        details.append({"id": cid, "pred": res["answer"], "expected": exp, "match": bool(match)})
    print(f"AMBIGUITY SET: {ok}/{len(CASES)} | tokens={pipe.llm.usage['total_tokens']}")
    return details


if __name__ == "__main__":
    main()
