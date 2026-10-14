import time
import json
from typing import List, Dict, Any
from app.services.pipeline import QAPipeline

UNSEEN_QUERIES = [
    # Group 1: p4_t02.xlsx Table 2 (Calendar years - Multi-table handling)
    {
        "id": "p4_u001",
        "file_name": "p4_t02.xlsx",
        "query": "What was the agricultural export value for the calendar year 2020? Answer with the number rounded to two decimal places.",
        "expected": "149.67"
    },
    {
        "id": "p4_u002",
        "file_name": "p4_t02.xlsx",
        "query": "What was the agricultural import value for the calendar year 2021? Answer with the number rounded to two decimal places.",
        "expected": "170.59"
    },
    {
        "id": "p4_u003",
        "file_name": "p4_t02.xlsx",
        "query": "In calendar year 2020, was the trade balance positive? Answer with only Yes or No.",
        "expected": "Yes"
    },
    {
        "id": "p4_u004",
        "file_name": "p4_t02.xlsx",
        "query": "What was the trade balance for the calendar year 2022? Answer with the number rounded to two decimal places.",
        "expected": "-2.56"
    },
    {
        "id": "p4_u005",
        "file_name": "p4_t02.xlsx",
        "query": "Did the agricultural export value in calendar year 2021 exceed that in calendar year 2020? Answer with only Yes or No.",
        "expected": "Yes"
    },

    # Group 2: p4_t10.xlsx (Demographic hierarchy: Men vs Women in specific age brackets)
    {
        "id": "p4_u006",
        "file_name": "p4_t10.xlsx",
        "query": "How many men aged 25 to 54 years were at work? Answer with only the integer, without commas or units.",
        "expected": "52886"
    },
    {
        "id": "p4_u007",
        "file_name": "p4_t10.xlsx",
        "query": "How many women aged 25 to 54 years were at work? Answer with only the integer, without commas or units.",
        "expected": "45646"
    },
    {
        "id": "p4_u008",
        "file_name": "p4_t10.xlsx",
        "query": "What is the absolute difference between the number of men and women aged 25 to 54 years at work? Answer with only the integer, without commas or units.",
        "expected": "7240"
    },
    {
        "id": "p4_u009",
        "file_name": "p4_t10.xlsx",
        "query": "Among people aged 55 years and over, did more men work than women? Answer with only Yes or No.",
        "expected": "Yes"
    },
    {
        "id": "p4_u010",
        "file_name": "p4_t10.xlsx",
        "query": "How many women aged 55 years and over were at work? Answer with only the integer, without commas or units.",
        "expected": "16265"
    },

    # Group 3: p4_t03.xlsx (Deep Indent Levels 3 & 4)
    {
        "id": "p4_u011",
        "file_name": "p4_t03.xlsx",
        "query": "What was the relative importance of 'Fuel oil' in September 2024? Answer with only the number.",
        "expected": "0.07"
    },
    {
        "id": "p4_u012",
        "file_name": "p4_t03.xlsx",
        "query": "What was the unadjusted percent change for 'Gasoline (all types)' from September 2024 to October 2024? Answer with only the number.",
        "expected": "-1.9"
    },
    {
        "id": "p4_u013",
        "file_name": "p4_t03.xlsx",
        "query": "What was the relative importance of 'Dairy and related products'? Answer with only the number.",
        "expected": "0.732"
    },
    {
        "id": "p4_u014",
        "file_name": "p4_t03.xlsx",
        "query": "What was the unadjusted index for 'Cereals and bakery products' in October 2024? Answer with only the number rounded to three decimal places.",
        "expected": "359.007"
    },
    {
        "id": "p4_u015",
        "file_name": "p4_t03.xlsx",
        "query": "Was the relative importance of 'Gasoline (all types)' greater than that of 'Fuel oil'? Answer with only Yes or No.",
        "expected": "Yes"
    },

    # Group 4: p4_t07.xlsx (Lower-half rows 40-114 that were previously truncated)
    {
        "id": "p4_u016",
        "file_name": "p4_t07.xlsx",
        "query": "How many men were employed in 'Public administration'? Answer with only the integer, without commas or units.",
        "expected": "4313"
    },
    {
        "id": "p4_u017",
        "file_name": "p4_t07.xlsx",
        "query": "How many women were employed in 'Education and health services'? Answer with only the integer, without commas or units.",
        "expected": "27056"
    },
    {
        "id": "p4_u018",
        "file_name": "p4_t07.xlsx",
        "query": "How many women were employed in 'Public administration'? Answer with only the integer, without commas or units.",
        "expected": "3670"
    },
    {
        "id": "p4_u019",
        "file_name": "p4_t07.xlsx",
        "query": "In 'Financial activities', did more women work than men? Answer with only Yes or No.",
        "expected": "Yes"
    },
    {
        "id": "p4_u020",
        "file_name": "p4_t07.xlsx",
        "query": "What is the total number of men employed in 'Financial activities'? Answer with only the integer, without commas or units.",
        "expected": "5384"
    },

    # Group 5: test_multisheet.xlsx and Typo Resilience
    {
        "id": "p4_u021",
        "file_name": "test_multisheet.xlsx",
        "query": "According to the Department_Sales sheet, what was the total sales for Electronics? Answer with only the integer, without commas or units.",
        "expected": "330000"
    },
    {
        "id": "p4_u022",
        "file_name": "test_multisheet.xlsx",
        "query": "Based on the Employee_Headcount sheet, how many full-time employees work in the Furniture department? Answer with only the integer, without commas or units.",
        "expected": "28"
    },
    {
        "id": "p4_u023",
        "file_name": "test_multisheet.xlsx",
        "query": "What is the total staff headcount in the Apparel department? Answer with only the integer, without commas or units.",
        "expected": "53"
    },
    {
        "id": "p4_u024",
        "file_name": "test_multisheet.xlsx",
        "query": "What is Q1_Sales for the Furnitur departmnt in the Department_Sales sheet? Answer with only the integer, without commas or units.",
        "expected": "85000"
    },
    {
        "id": "p4_u025",
        "file_name": "test_multisheet.xlsx",
        "query": "In the Employee_Headcount sheet, does the Electrnics department have more than 50 total staff? Answer with only Yes or No.",
        "expected": "Yes"
    }
]

def run_unseen_evaluation():
    pipeline = QAPipeline()
    results = []
    correct_count = 0
    total_time = 0.0

    print("=" * 60)
    print(f"=== Running Unseen Evaluation Benchmark ({len(UNSEEN_QUERIES)} Queries) ===")
    print("=" * 60)

    for idx, item in enumerate(UNSEEN_QUERIES, 1):
        q_id = item["id"]
        fname = item["file_name"]
        fpath = f"xlsx_files/{fname}"
        query = item["query"]
        expected = str(item["expected"]).strip()

        print(f"\n[{idx}/{len(UNSEEN_QUERIES)}] {q_id} ({fname})...")
        print(f"  Query:    {query}")

        start = time.time()
        res = pipeline.answer_query(fpath, query)
        elapsed = time.time() - start
        total_time += elapsed

        pred = str(res["answer"]).strip()
        is_match = (pred == expected)
        if is_match:
            correct_count += 1

        print(f"  Pred:     '{pred}'")
        print(f"  Expected: '{expected}'")
        print(f"  Match:    {is_match} | Time: {elapsed:.2f}s | Retries: {res.get('retries', 0)}")
        if not is_match and res.get("error"):
            print(f"  Error:    {res['error'][:100]}")

        results.append({
            "id": q_id,
            "file": fname,
            "query": query,
            "predicted": pred,
            "expected": expected,
            "match": is_match,
            "time_seconds": round(elapsed, 2),
            "retries": res.get("retries", 0),
            "code": res.get("code")
        })

    accuracy = (correct_count / len(UNSEEN_QUERIES)) * 100
    avg_time = total_time / len(UNSEEN_QUERIES)

    print("\n" + "=" * 60)
    print("UNSEEN EVALUATION BENCHMARK SUMMARY:")
    print(f"Total Queries:  {len(UNSEEN_QUERIES)}")
    print(f"Exact Matches:  {correct_count} / {len(UNSEEN_QUERIES)} ({accuracy:.1f}%)")
    print(f"Total Time:     {total_time:.2f}s (Avg: {avg_time:.2f}s/query)")
    print("=" * 60)

    with open("unseen_evaluation_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "correct_count": correct_count,
            "total_queries": len(UNSEEN_QUERIES),
            "total_time_seconds": round(total_time, 2),
            "average_time_seconds": round(avg_time, 2),
            "details": results
        }, f, indent=2, ensure_ascii=False)
    print("Saved detailed report to 'unseen_evaluation_report.json'")

if __name__ == "__main__":
    run_unseen_evaluation()
