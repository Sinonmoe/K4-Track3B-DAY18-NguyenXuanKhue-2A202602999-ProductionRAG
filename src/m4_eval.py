from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


DIAGNOSTIC_TREE = {
    "faithfulness": (
        "LLM tự bịa câu trả lời ngoài tài liệu",
        "Thắt chặt system prompt, giảm nhiệt độ (temperature) về 0",
    ),
    "context_recall": (
        "Hệ thống tìm kiếm bỏ sót đoạn văn đúng",
        "Cải thiện lại bước cắt đoạn hoặc bổ sung từ khóa BM25",
    ),
    "context_precision": (
        "Đoạn văn không liên quan bị xếp lên đầu",
        "Bổ sung tầng Cross-Encoder reranking hoặc lọc theo metadata",
    ),
    "answer_relevancy": (
        "Câu trả lời bị lệch trọng tâm câu hỏi",
        "Viết lại prompt hướng dẫn mô hình trả lời trực tiếp hơn",
    ),
}


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        df = result.to_pandas()
        per_question = [
            EvalResult(
                question=str(row.get("question", "")),
                answer=str(row.get("answer", "")),
                contexts=list(row.get("contexts", [])),
                ground_truth=str(row.get("ground_truth", "")),
                faithfulness=float(row.get("faithfulness", 0.0) or 0.0),
                answer_relevancy=float(row.get("answer_relevancy", 0.0) or 0.0),
                context_precision=float(row.get("context_precision", 0.0) or 0.0),
                context_recall=float(row.get("context_recall", 0.0) or 0.0),
            )
            for _, row in df.iterrows()
        ]

        def _get_metric_val(name: str) -> float:
            if name in result:
                val = result[name]
                return float(val) if isinstance(val, (int, float)) else 0.0
            if name in df and not df[name].empty:
                return float(df[name].mean())
            return 0.0

        return {
            "faithfulness": _get_metric_val("faithfulness"),
            "answer_relevancy": _get_metric_val("answer_relevancy"),
            "context_precision": _get_metric_val("context_precision"),
            "context_recall": _get_metric_val("context_recall"),
            "per_question": per_question,
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": [],
        }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []

    failures = []
    for r in eval_results:
        metrics = {
            "faithfulness": float(r.faithfulness),
            "answer_relevancy": float(r.answer_relevancy),
            "context_precision": float(r.context_precision),
            "context_recall": float(r.context_recall),
        }
        avg_score = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics, key=lambda k: metrics[k])
        worst_score = metrics[worst_metric]
        diagnosis, suggested_fix = DIAGNOSTIC_TREE.get(
            worst_metric, ("Unknown issue", "Review pipeline")
        )
        failures.append({
            "question": r.question,
            "avg_score": round(avg_score, 4),
            "worst_metric": worst_metric,
            "score": round(worst_score, 4),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })

    failures.sort(key=lambda x: x["avg_score"])
    return failures[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
