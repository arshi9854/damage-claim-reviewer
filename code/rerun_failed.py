#!/usr/bin/env python3
"""Re-run failed claims and patch output.csv"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from main import (
    load_user_history, load_evidence_requirements, get_relevant_requirements,
    build_prompt, call_claude, validate_output, DATASET_DIR, BASE_DIR
)

def main():
    output_csv = BASE_DIR / "output.csv"

    with open(output_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys())
    user_history = load_user_history()
    evidence_reqs = load_evidence_requirements()

    fail_phrases = ["Unable to process claim", "could not be accessed", "could not be loaded", "was not accessible"]
    failed_indices = [i for i, r in enumerate(rows) if any(p in r.get("evidence_standard_met_reason", "") or p in r.get("claim_status_justification", "") for p in fail_phrases)]
    print(f"Re-running {len(failed_indices)} failed claims...")

    for idx in failed_indices:
        row = rows[idx]
        print(f"\n  Re-running row {idx+1}: {row['user_id']} - {row['claim_object']}")

        image_paths_raw = row["image_paths"].split(";")
        image_ids = [Path(p).stem for p in image_paths_raw]
        user_hist = user_history.get(row["user_id"])
        req_text = get_relevant_requirements(evidence_reqs, row["claim_object"])

        prompt = build_prompt(row, user_hist, req_text, image_ids)
        result = call_claude(prompt, image_paths_raw, retries=3)
        result = validate_output(result, row["claim_object"])

        rows[idx]["evidence_standard_met"] = str(result["evidence_standard_met"]).lower()
        rows[idx]["evidence_standard_met_reason"] = result["evidence_standard_met_reason"]
        rows[idx]["risk_flags"] = result["risk_flags"]
        rows[idx]["issue_type"] = result["issue_type"]
        rows[idx]["object_part"] = result["object_part"]
        rows[idx]["claim_status"] = result["claim_status"]
        rows[idx]["claim_status_justification"] = result["claim_status_justification"]
        rows[idx]["supporting_image_ids"] = result["supporting_image_ids"]
        rows[idx]["valid_image"] = str(result["valid_image"]).lower()
        rows[idx]["severity"] = result["severity"]

        print(f"    -> {result['claim_status']} | {result['issue_type']} | {result['object_part']} | {result['severity']}")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nPatched output written to {output_csv}")

if __name__ == "__main__":
    main()
