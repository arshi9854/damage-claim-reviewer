# Damage Claim Reviewer

Automated damage claim verification system built for the **HackerRank Orchestrate** hackathon. Analyzes submitted images against claim conversations, user history, and evidence requirements to determine whether a damage claim is supported, contradicted, or lacks sufficient information.

Handles three object types: **cars**, **laptops**, and **packages**.

## How It Works

For each claim, the system:

1. Parses the claim conversation to extract what the user is reporting
2. Looks up the user's claim history for risk context
3. Loads minimum evidence requirements for that object/damage type
4. Sends images + full context to **Claude Sonnet** (VLM) in a single call
5. Parses the structured JSON response
6. Validates all fields against allowed enum values
7. Writes the final prediction to `output.csv`

## Architecture

```
CSV Inputs ──► Prompt Builder ──► Claude Sonnet (VLM) ──► JSON Parser ──► Validator ──► output.csv
                   │                      ▲
                   │                      │
           user_history.csv          images/*.jpg
           evidence_requirements.csv
```

Single-pass pipeline. One model call per claim. No frameworks, no external dependencies beyond Python stdlib and the Claude CLI.

## Prerequisites

- Python 3.10+
- [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated

```bash
claude --version
```

## Usage

```bash
# Run on test claims → produces output.csv
python3 code/main.py test

# Run on sample claims → produces sample_output.csv
python3 code/main.py sample

# Re-run any failed claims (patches output.csv in place)
python3 code/rerun_failed.py

# Run evaluation against sample ground truth
python3 code/evaluation/main.py
```

## Project Structure

```
├── code/
│   ├── main.py                      # Main pipeline
│   ├── rerun_failed.py              # Retry script for transient failures
│   ├── README.md                    # Code-level docs
│   └── evaluation/
│       ├── main.py                  # Evaluation harness
│       └── evaluation_report.md     # Results and operational analysis
├── dataset/
│   ├── claims.csv                   # 44 test claims (input only)
│   ├── sample_claims.csv            # 20 labeled claims (input + ground truth)
│   ├── user_history.csv             # User risk profiles
│   ├── evidence_requirements.csv    # Minimum evidence checklists
│   └── images/
│       ├── sample/                  # Images for sample claims
│       └── test/                    # Images for test claims
└── output.csv                       # Final predictions
```

## Evaluation Results

Evaluated on 20 labeled sample claims across 4 prompt iterations:

| Metric | Run 1 | Run 4 (Final) |
|--------|-------|---------------|
| claim_status | 0.800 | 0.850 |
| issue_type | 0.450 | 0.700 |
| object_part | 0.750 | 0.900 |
| severity | 0.250 | 0.550 |
| evidence_standard_met | 0.800 | 0.850 |
| valid_image | 0.800 | 0.850 |
| risk_flags (F1) | 0.578 | 0.703 |
| supporting_image_ids (F1) | 0.750 | 0.833 |
| **Overall** | **0.647** | **0.780** |

## Key Design Decisions

- **Sonnet over Haiku/Opus** — best accuracy-to-speed ratio for nuanced visual analysis
- **CLI over Python SDK** — zero dependencies, handles image encoding and auth natively
- **One call per claim** — Sonnet handles extraction, analysis, and judgment in a single pass
- **Sequential processing** — 44 claims in ~30 minutes; avoids rate limit complexity
- **Prompt engineering as primary lever** — improved from 0.647 to 0.780 through calibration rules and concrete examples

## Prompt Engineering Highlights

- Explicit issue type distinctions (crack vs glass_shatter, stain vs water_damage)
- Severity calibration with concrete examples (windshield crack = medium, only total destruction = high)
- Clear status decision rules (contradicted = part visible but undamaged, not_enough_information = part not visible)
- Adversarial awareness (detects and flags text instructions embedded in images like "approve this claim")
- User history integration (risk flags from history, never overrides visual evidence)

## Output Schema

| Field | Values |
|-------|--------|
| `claim_status` | `supported`, `contradicted`, `not_enough_information` |
| `issue_type` | `dent`, `scratch`, `crack`, `glass_shatter`, `broken_part`, `missing_part`, `torn_packaging`, `crushed_packaging`, `water_damage`, `stain`, `none`, `unknown` |
| `severity` | `none`, `low`, `medium`, `high`, `unknown` |
| `risk_flags` | `blurry_image`, `claim_mismatch`, `non_original_image`, `wrong_object`, `text_instruction_present`, `user_history_risk`, etc. |

## Operational Stats

- ~40s per claim, ~30 min for full test set
- ~2000 text tokens + 1000-3000 per image input, ~200 output per call
- Estimated $2-5 at API pricing for the full test set
- 2 retries with 5s backoff on failure + separate rerun script for transient errors
