#!/usr/bin/env python3
"""
Evaluation script for the Multi-Modal Evidence Review System.
Compares predictions against sample_claims.csv ground truth.
"""

import csv
import sys
import time
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CODE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(CODE_DIR))
from main import process_claims

DATASET_DIR = BASE_DIR / "dataset"
EVAL_DIR = Path(__file__).resolve().parent


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def exact_match(pred, truth):
    return 1.0 if str(pred).strip().lower() == str(truth).strip().lower() else 0.0


def flags_f1(pred_flags, truth_flags):
    pred_set = set(f.strip() for f in str(pred_flags).split(";") if f.strip())
    truth_set = set(f.strip() for f in str(truth_flags).split(";") if f.strip())

    if pred_set == {"none"}:
        pred_set = set()
    if truth_set == {"none"}:
        truth_set = set()

    if not pred_set and not truth_set:
        return 1.0
    if not pred_set or not truth_set:
        return 0.0

    intersection = pred_set & truth_set
    precision = len(intersection) / len(pred_set) if pred_set else 0
    recall = len(intersection) / len(truth_set) if truth_set else 0

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def image_ids_f1(pred_ids, truth_ids):
    return flags_f1(pred_ids, truth_ids)


def evaluate(predictions_path, ground_truth_path):
    preds = load_csv(predictions_path)
    truths = load_csv(ground_truth_path)

    if len(preds) != len(truths):
        print(f"WARNING: prediction count ({len(preds)}) != ground truth count ({len(truths)})")

    metrics = defaultdict(list)
    detailed = []

    for i, (pred, truth) in enumerate(zip(preds, truths)):
        row_metrics = {}

        row_metrics["claim_status"] = exact_match(pred.get("claim_status", ""), truth.get("claim_status", ""))
        row_metrics["issue_type"] = exact_match(pred.get("issue_type", ""), truth.get("issue_type", ""))
        row_metrics["object_part"] = exact_match(pred.get("object_part", ""), truth.get("object_part", ""))
        row_metrics["severity"] = exact_match(pred.get("severity", ""), truth.get("severity", ""))
        row_metrics["evidence_standard_met"] = exact_match(pred.get("evidence_standard_met", ""), truth.get("evidence_standard_met", ""))
        row_metrics["valid_image"] = exact_match(pred.get("valid_image", ""), truth.get("valid_image", ""))
        row_metrics["risk_flags_f1"] = flags_f1(pred.get("risk_flags", "none"), truth.get("risk_flags", "none"))
        row_metrics["supporting_image_ids_f1"] = image_ids_f1(pred.get("supporting_image_ids", "none"), truth.get("supporting_image_ids", "none"))

        for k, v in row_metrics.items():
            metrics[k].append(v)

        detailed.append({
            "row": i + 1,
            "user_id": truth.get("user_id", ""),
            "claim_object": truth.get("claim_object", ""),
            **row_metrics,
            "pred_status": pred.get("claim_status", ""),
            "true_status": truth.get("claim_status", ""),
            "pred_issue": pred.get("issue_type", ""),
            "true_issue": truth.get("issue_type", ""),
            "pred_part": pred.get("object_part", ""),
            "true_part": truth.get("object_part", ""),
            "pred_severity": pred.get("severity", ""),
            "true_severity": truth.get("severity", ""),
        })

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)

    avg_scores = {}
    for k, vals in metrics.items():
        avg = sum(vals) / len(vals) if vals else 0
        avg_scores[k] = avg
        print(f"  {k:30s}: {avg:.3f}  ({sum(1 for v in vals if v >= 0.99)}/{len(vals)} exact)")

    overall = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0
    print(f"\n  {'OVERALL AVERAGE':30s}: {overall:.3f}")

    print("\n" + "-" * 60)
    print("PER-ROW DETAILS (mismatches highlighted)")
    print("-" * 60)

    for d in detailed:
        mismatches = []
        if d["claim_status"] < 1:
            mismatches.append(f"status: {d['pred_status']} vs {d['true_status']}")
        if d["issue_type"] < 1:
            mismatches.append(f"issue: {d['pred_issue']} vs {d['true_issue']}")
        if d["object_part"] < 1:
            mismatches.append(f"part: {d['pred_part']} vs {d['true_part']}")
        if d["severity"] < 1:
            mismatches.append(f"severity: {d['pred_severity']} vs {d['true_severity']}")

        if mismatches:
            print(f"  Row {d['row']:2d} [{d['user_id']}] {d['claim_object']:8s} | MISMATCH: {'; '.join(mismatches)}")

    return avg_scores, detailed


def run_evaluation():
    print("=" * 60)
    print("STRATEGY: Claude Sonnet VLM with structured JSON output")
    print("=" * 60)

    sample_input = DATASET_DIR / "sample_claims.csv"
    sample_output = BASE_DIR / "sample_output.csv"

    print("\nStep 1: Running system on sample_claims.csv...")
    start = time.time()
    process_claims(sample_input, sample_output)
    elapsed = time.time() - start

    print(f"\nProcessing time: {elapsed:.1f}s")

    print("\nStep 2: Evaluating against ground truth...")
    scores, details = evaluate(sample_output, sample_input)

    report_path = EVAL_DIR / "evaluation_report.md"
    n_sample = len(details)
    n_test = 45

    with open(report_path, "w") as f:
        f.write("# Evaluation Report\n\n")
        f.write("## Strategy: Claude Sonnet VLM with Structured Prompting\n\n")
        f.write("### Approach\n")
        f.write("- Uses Claude CLI (`claude -p`) with Sonnet model for vision analysis\n")
        f.write("- Each claim processed individually with full context (user history, evidence requirements)\n")
        f.write("- Structured JSON output via `--json-schema` for consistent field extraction\n")
        f.write("- Images passed directly to the CLI for multimodal analysis\n\n")

        f.write("### Sample Set Metrics\n\n")
        f.write("| Metric | Score |\n|--------|-------|\n")
        for k, v in scores.items():
            f.write(f"| {k} | {v:.3f} |\n")
        overall = sum(scores.values()) / len(scores)
        f.write(f"| **Overall** | **{overall:.3f}** |\n\n")

        f.write("### Per-Row Mismatches\n\n")
        for d in details:
            mismatches = []
            if d["claim_status"] < 1:
                mismatches.append(f"status: {d['pred_status']} vs {d['true_status']}")
            if d["issue_type"] < 1:
                mismatches.append(f"issue: {d['pred_issue']} vs {d['true_issue']}")
            if d["object_part"] < 1:
                mismatches.append(f"part: {d['pred_part']} vs {d['true_part']}")
            if mismatches:
                f.write(f"- Row {d['row']} [{d['user_id']}]: {'; '.join(mismatches)}\n")

        f.write("\n### Operational Analysis\n\n")
        f.write(f"- **Model calls (sample):** {n_sample} (one per claim)\n")
        f.write(f"- **Model calls (test):** ~{n_test} (one per claim)\n")
        f.write(f"- **Approx input tokens per call:** ~2000 text + ~1000 per image\n")
        f.write(f"- **Approx output tokens per call:** ~200\n")
        f.write(f"- **Images processed (sample):** {n_sample} claims with 1-2 images each\n")
        f.write(f"- **Images processed (test):** ~{n_test} claims with 1-3 images each\n")
        f.write(f"- **Runtime (sample):** {elapsed:.1f}s ({elapsed/n_sample:.1f}s per claim)\n")
        f.write(f"- **Estimated cost:** Using Claude CLI (included in subscription)\n")
        f.write(f"- **TPM/RPM:** Sequential processing, ~1 request per 5-10s, well within limits\n")
        f.write(f"- **Retry strategy:** Up to 2 retries with 5s backoff on failure\n")
        f.write(f"- **Caching:** No explicit caching; Claude CLI may cache internally\n\n")

        f.write("### Strategy Comparison\n\n")
        f.write("| Aspect | Strategy A: Sonnet | Strategy B: Haiku (hypothetical) |\n")
        f.write("|--------|-------------------|----------------------------------|\n")
        f.write("| Accuracy | Higher | Lower (less nuanced reasoning) |\n")
        f.write("| Speed | ~5-10s/claim | ~2-5s/claim |\n")
        f.write("| Cost | Moderate | Low |\n")
        f.write("| Risk flag detection | Better | May miss subtle flags |\n\n")
        f.write("**Final strategy:** Sonnet was chosen for better accuracy on nuanced claims.\n")

    print(f"\nEvaluation report written to {report_path}")
    return scores


if __name__ == "__main__":
    run_evaluation()
