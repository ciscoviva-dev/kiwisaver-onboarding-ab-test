# Implementation Plan: Codebase Review & Quality Improvements

**Branch**: `review-improvements` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `.specify/specs/codebase-review-and-improvements/spec.md`

## Summary

This plan outlines the concrete technical architecture, refactor paths, and testing strategies to address simulation discrepancies, SQL edge cases, statistical guardrail modeling, unit test coverage, and documentation alignment in the KiwiSaver onboarding A/B test project.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `numpy`, `pandas`, `scipy`, `duckdb`, `dbt-duckdb`, `matplotlib`, `nbconvert`, `nbformat`, `pytest`, `ruff` (new)  
**Storage**: DuckDB (`warehouse.duckdb`), Parquet files (`data/raw/*.parquet`)  
**Testing**: `pytest` (effect recovery + simulation & analysis unit tests), `dbt test` (schema, uniqueness, accepted values, SRM check)  
**Target Platform**: Cross-platform (Windows / macOS / Linux)  
**Project Type**: Analytics engineering & decision science portfolio project  
**Performance Goals**: Synthetic simulation < 3s; full dbt pipeline < 10s; test suite < 10s  
**Constraints**: Zero regression on ground-truth effect recovery ($|observed - expected| < 0.015$); strict separation of oracle (`ground_truth.yaml`) from analysis code  
**Scale/Scope**: 40,000 synthetic users; 9 dbt models; 3 Jupyter notebooks  

## Constitution Check

- [x] **Deterministic Reproducibility**: Seed pinned in simulation and analysis; verified by tests.
- [x] **Oracle Separation**: Analysis and models never import or query `ground_truth.yaml`.
- [x] **Decisions Over Raw Significance**: Expected loss, credible intervals, and guardrail trade-offs emphasized alongside frequentist checks.
- [x] **Defensive Analytics Engineering**: Explicit NULL propagation, timestamp interval enforcement, and dual-denominator guardrail tracking.
- [x] **High Presentation Standards**: Plain-English notebooks rendered to HTML, vector figure outputs, clean GitHub navigation.

## Project Structure

### Documentation & Specs
```text
.specify/
├── memory/
│   └── constitution.md
└── specs/codebase-review-and-improvements/
    ├── spec.md
    ├── plan.md
    └── tasks.md (Phase 3)
```

### Source Code
```text
src/
├── simulate.py             # Seeded synthetic event generator (recommendation continuity fix + performance)
├── analyze.py              # Bayesian & frequentist analysis (guardrail uncertainty, dynamic z, SVG export)
└── render_notebooks.py     # HTML renderer (Windows event loop fix, portal upgrade)

dbt/
├── models/
│   ├── staging/            # stg_events, stg_users
│   ├── intermediate/       # int_funnel (NULL match handling, 14d timestamp window)
│   └── marts/              # mart_guardrails (dual abandonment rates), mart_primary_metric, etc.
└── tests/
    └── assert_ab_split_healthy.sql  # SRM check (threshold + Pearson chi-square)

tests/
├── test_recovery.py        # Oracle effect recovery tests
├── test_simulate.py        # NEW: Unit tests for generator, schema, and catalog
└── test_analyze.py         # NEW: Unit tests for Bayesian updates, decision outputs, and commercial NPV

notebooks/                  # 01_eda.ipynb, 02_ab_test.ipynb, 03_bandits_and_peeking.ipynb
reports/                    # results.json, summary.md, figures/*.png, figures/*.svg
docs/                       # index.html, executed HTML notebooks
```

## Technical Design & Strategy

### 1. Fix Quiz Recommendation Continuity (`src/simulate.py`)
- When generating events for Variant B:
  1. User completes risk quiz -> calls `_choose_fund(rng, user["fund_risk_profile"], "B")` returning `rec_fund, rec_cat`. Emitted in `completed_risk_quiz` with `{"recommended_fund_id": rec_fund, "questions": 3}`.
  2. When user advances to `selected_base_fund`: with probability 0.90, `fund_id, fund_cat = rec_fund, rec_cat`. With probability 0.10, they override and pick another fund via `_choose_fund(rng, user["fund_risk_profile"], "A")`.
  3. Store `rec_fund` per user during iteration.
- Replace `users.iterrows()` with `users.itertuples(index=False)` to cut generator overhead by 5x.
- Extract `tick` helper to avoid defining 40,000 closures.

### 2. Defensive SQL Modeling (`dbt/models/intermediate/int_funnel.sql` & `mart_guardrails.sql`)
- In `int_funnel.sql`:
  - Change `max(case when event_name = 'selected_base_fund' and fund_profile_match then 1 else 0 end)` to `max(case when fund_profile_match then 1 else 0 end) filter (where event_name = 'selected_base_fund')`.
  - In final select, `case when selected_fund_at is not null then cast(fund_profile_match as boolean) else null end as fund_profile_match`.
  - Enforce `switched_fund_14d`: `(switched_fund_at is not null and submitted_at is not null and switched_fund_at between submitted_at and submitted_at + interval 14 days)`.
- In `mart_guardrails.sql`:
  - Calculate `post_selection_abandonment_reached_rate` (denom: reached selection).
  - Calculate `post_selection_abandonment_selector_rate` (denom: selected base fund).
  - Maintain backwards-compatible alias `post_selection_abandonment_rate = post_selection_abandonment_reached_rate`.

### 3. Guardrail Uncertainty Quantification (`src/analyze.py`)
- In `analyze.py`:
  - Run `summarize_arm` for guardrails:
    - Post-selection abandonment: $y_{aband}, n_{reached}$ (and selector base).
    - 14-day regret: $y_{switch}, n_{conv}$.
  - Compute credible intervals and probability that B has worse regret: $P(\text{regret}_B > \text{regret}_A)$.
  - Dynamically compute critical value: `stats.norm.ppf(1 - (1 - CRED) / 2)` instead of hardcoded 1.96.
  - Save figures with both `fig.savefig(..., dpi=150)` and `fig.savefig(..., format="svg")`.

### 4. Windows Event Loop & Portal Refinement (`src/render_notebooks.py`)
- At the top of `render_notebooks.py`, configure:
  ```python
  import sys, asyncio

  if sys.platform == "win32":
      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
  ```
- Enhance `index_page()` template with clean cards and GitHub notebook direct links.

### 5. Test Suite Expansion & Developer Tooling (`tests/`, `pyproject.toml`)
- Add `tests/test_simulate.py`:
  - Verify seed determinism: repeating `make_users` + `simulate_events` with same seed gives identical rows and hashes.
  - Verify timestamp sequence: `viewed_landing <= started <= completed_q <= viewed_selection <= selected <= confirmed <= submitted`.
  - Verify JSON payload validity.
- Add `tests/test_analyze.py`:
  - Verify `beta_posterior` closed-form properties ($\alpha = \alpha_0 + y, \beta = \beta_0 + n - y$).
  - Verify `decision_outputs` symmetry when arms are identical ($P(B>A) \approx 0.50$, expected loss equal).
  - Verify `npv5` closed-form calculation against formula.
- In `pyproject.toml`:
  - Add `ruff>=0.8.0` to `[dependency-groups] dev`.
  - Add `[tool.ruff]` configuration with clean defaults.
