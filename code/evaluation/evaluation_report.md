# Evaluation Report

## Strategy: Claude Sonnet VLM with Structured Prompting

### Approach
- Uses Claude CLI (`claude -p --model sonnet --output-format text`) for vision analysis
- Each claim processed individually with full context (user history, evidence requirements)
- Structured JSON output enforced via detailed prompt engineering with field-level calibration
- Images passed directly to CLI as positional arguments for multimodal analysis
- Validation layer ensures all output values match allowed enums

### Sample Set Metrics (20 claims)

| Metric | Run 1 (Baseline) | Run 2 (Calibrated) | Run 3 (Final) | Run 4 (Latest) |
|--------|------------------|--------------------|----|-----|
| claim_status | 0.800 | 0.700 | 0.800 | 0.850 |
| issue_type | 0.450 | 0.450 | 0.750 | 0.700 |
| object_part | 0.750 | 0.900 | 0.900 | 0.900 |
| severity | 0.250 | 0.300 | 0.650 | 0.550 |
| evidence_standard_met | 0.800 | 0.800 | 0.850 | 0.850 |
| valid_image | 0.800 | 0.900 | 0.900 | 0.850 |
| risk_flags_f1 | 0.578 | 0.755 | 0.646 | 0.703 |
| supporting_ids_f1 | 0.750 | 0.683 | 0.783 | 0.833 |
| **Overall** | **0.647** | **0.686** | **0.785** | **0.780** |

### Strategy Comparison

| Aspect | Strategy A: Sonnet (chosen) | Strategy B: Haiku (hypothetical) |
|--------|----------------------------|----------------------------------|
| Accuracy | 0.780-0.785 overall | Lower (~0.55-0.65 est.) - less nuanced reasoning |
| Speed | ~30-40s per claim | ~10-20s per claim |
| Cost | Moderate (via CLI subscription) | Lower |
| Risk flag detection | Good - catches mismatch, history flags | May miss subtle flags |
| Issue type accuracy | 0.700-0.750 | Lower - more confusion between crack/shatter/scratch |
| Severity calibration | 0.550-0.650 | Likely lower without calibration guidance |

**Final strategy:** Sonnet was chosen for superior accuracy on nuanced visual claims.

### Key Prompt Engineering Improvements

1. **Issue type calibration**: Explicit distinction between crack (fracture lines) vs glass_shatter (fully shattered), stain (discoloration) vs water_damage (package soaking)
2. **Severity calibration**: Concrete examples mapping common damage types to severity levels. Most real damage = "medium", only catastrophic = "high"
3. **Status decision rules**: Clear rules for when to use contradicted (visible but no damage) vs not_enough_information (can't see claimed part)
4. **Object part alignment**: Always use the USER's claimed part, not just what's visible
5. **Risk flag rules**: Explicit triggers for user_history_risk, claim_mismatch, text_instruction_present

### Remaining Error Patterns
- Severity calibration variance across runs (model sometimes inflates to "high")
- Occasional dent vs scratch confusion on ambiguous surface marks
- Borderline supported/contradicted on subtle damage (rows 12, 14, 20)
- Stock photo cases: model sometimes says unknown instead of identifying the visible damage type

### Per-Row Mismatches (Latest Run)

- Row 1 [user_001]: severity: high vs medium
- Row 2 [user_002]: issue: dent vs scratch; severity: medium vs low
- Row 5 [user_005]: issue: dent vs scratch; severity: medium vs low
- Row 8 [user_008]: issue: unknown vs broken_part; part: hood vs front_bumper; severity: unknown vs high
- Row 9 [user_009]: severity: high vs medium
- Row 12 [user_012]: status: contradicted vs supported; issue: none vs dent; severity: none vs low
- Row 14 [user_020]: status: supported vs contradicted; issue: dent vs none; severity: low vs none
- Row 19 [user_033]: part: box vs unknown; severity: unknown vs low
- Row 20 [user_034]: status: supported vs contradicted; issue: torn_packaging vs none; severity: medium vs none

### Operational Analysis

- **Model calls (sample):** 20 (one per claim, plus retries on timeout)
- **Model calls (test):** 44 (one per claim, plus 4 retries for transient failures)
- **Approx input tokens per call:** ~2000 text + ~1000-3000 per image (1-3 images)
- **Approx output tokens per call:** ~200
- **Total tokens (sample):** ~80K input, ~4K output
- **Total tokens (test):** ~180K input, ~9K output
- **Images processed (sample):** 29 images across 20 claims
- **Images processed (test):** ~80 images across 44 claims
- **Runtime (sample):** ~790s (~40s per claim including CLI overhead)
- **Runtime (test):** ~30 minutes
- **Estimated cost:** Using Claude CLI (included in subscription), estimated $2-5 if using API directly
- **TPM/RPM:** Sequential processing at ~1 request per 30-40s, well within rate limits
- **Retry strategy:** Up to 2 retries with 5s backoff on timeout or parse failure; separate rerun script for transient failures
- **Caching:** No explicit caching; sequential processing avoids rate limit issues
- **Batching:** Not used (each claim needs different images); could parallelize with concurrent subprocesses for speed
