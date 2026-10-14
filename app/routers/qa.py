import os
import json
import csv
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.models.schemas import QueryItem, QueryResponse, BatchQueryRequest, EvaluationMetric
from app.dependencies import get_qa_pipeline
from app.services.pipeline import QAPipeline

router = APIRouter(prefix="/qa", tags=["Question Answering"])

@router.post("/ask", response_model=QueryResponse)
def ask_single_query(
    query_item: QueryItem,
    input_dir: str = "xlsx_files",
    pipeline: QAPipeline = Depends(get_qa_pipeline)
):
    fpath = os.path.join(input_dir, query_item.file_name)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail=f"File not found: {fpath}")

    res = pipeline.answer_query(fpath, query_item.query)
    return QueryResponse(
        id=query_item.id,
        query=query_item.query,
        answer=res["answer"],
        raw_result=res["raw_result"],
        code=res["code"],
        retries=res["retries"],
        elapsed_seconds=res["elapsed_seconds"]
    )

@router.post("/batch", response_model=EvaluationMetric)
def run_batch_evaluation(
    req: BatchQueryRequest,
    pipeline: QAPipeline = Depends(get_qa_pipeline)
):
    if not os.path.exists(req.queries_file):
        raise HTTPException(status_code=404, detail=f"Queries file not found: {req.queries_file}")

    with open(req.queries_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Load ground truth if exists
    ground_truth = {}
    if os.path.exists("sample_submission.csv"):
        with open("sample_submission.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 2:
                    ground_truth[row[0]] = row[1]

    submission_rows = [["id", "answer"]]
    correct = 0
    total_time = 0.0

    for item in queries:
        qid = item["id"]
        fname = item["file_name"]
        qtext = item["query"]
        fpath = os.path.join(req.input_dir, fname)

        if not os.path.exists(fpath):
            pred = ""
        else:
            res = pipeline.answer_query(fpath, qtext)
            pred = res["answer"]
            total_time += res["elapsed_seconds"]

        if qid in ground_truth and ground_truth[qid] == pred:
            correct += 1

        submission_rows.append([qid, pred])

    if req.output_file:
        with open(req.output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(submission_rows)

    total_q = len(queries)
    return EvaluationMetric(
        total_queries=total_q,
        exact_matches=correct,
        accuracy_percentage=round((correct / total_q) * 100, 2) if total_q > 0 else 0.0,
        total_time_seconds=round(total_time, 2),
        avg_time_per_query=round(total_time / total_q, 2) if total_q > 0 else 0.0
    )
