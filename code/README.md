# Multi-Modal Evidence Review System

Automated damage claim verification system that analyzes images, claim conversations, user history, and evidence requirements to determine claim validity.

## Setup

Requires Python 3.10+ and Claude CLI (`claude`) installed and authenticated.

```bash
# Ensure claude CLI is available
claude --version
```

No additional Python dependencies required (uses only stdlib + claude CLI).

## Usage

### Run on test claims (produces output.csv)
```bash
cd /path/to/repo
python3 code/main.py test
```

### Run on sample claims (for evaluation)
```bash
python3 code/main.py sample
```

### Run evaluation
```bash
python3 code/evaluation/main.py
```

## Architecture

1. **Input parsing**: Reads claims.csv, user_history.csv, evidence_requirements.csv
2. **Prompt construction**: Builds a detailed prompt for each claim with:
   - Claim conversation context
   - User risk history
   - Relevant evidence requirements
   - Calibrated output instructions with field-level guidance
3. **Vision analysis**: Calls `claude -p --model sonnet` with image files for multimodal analysis
4. **Output validation**: Ensures all fields match allowed enum values
5. **CSV output**: Writes structured predictions to output.csv

## Output Schema

| Field | Description |
|-------|-------------|
| evidence_standard_met | Whether images meet minimum evidence requirements |
| risk_flags | Semicolon-separated risk indicators |
| issue_type | Visible damage type (dent, scratch, crack, etc.) |
| object_part | Affected component |
| claim_status | supported / contradicted / not_enough_information |
| severity | none / low / medium / high / unknown |
