# Project Constitution

## Version: 1.0.0

## Principles

1. **Deterministic Reproducibility**: All synthetic generation (`src/simulate.py`) and analysis simulations must remain strictly deterministic from pinned seeds, producing identical outputs and recovering the injected effect within tolerances.
2. **Oracle Separation**: The analysis pipeline (`dbt/` -> `src/analyze.py` -> `notebooks/`) must NEVER read `ground_truth.yaml`. Ground truth exists solely as an external oracle for verification tests (`tests/test_recovery.py`).
3. **Decisions Over Raw Significance**: Prioritize decision-theoretic evaluation (expected loss, credible intervals, business upside, and guardrail trade-offs) over rote p-value thresholds.
4. **Defensive Analytics Engineering**: Data models in dbt must handle edge cases cleanly (e.g., proper `NULL` propagation for unobserved funnel steps, explicit timestamp window boundaries for guardrails, and automated sample ratio mismatch checks).
5. **No Blind Hallucinations / High Presentation Standards**: Narrative summaries, HTML reports, and README documentation must strictly reflect executed outputs and maintain plain-English clarity suitable for senior-level stakeholder review.
