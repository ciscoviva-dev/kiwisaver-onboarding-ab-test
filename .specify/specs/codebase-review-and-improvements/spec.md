# Feature Specification: Codebase Review & Quality Improvements

**Feature Branch**: `review-improvements`  
**Created**: 2026-10-14  
**Status**: Draft  
**Input**: User description: "a review of this codebase for issues and improvements"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Simulator Recommendation Continuity & Data Correctness (Priority: P1)

As a data analyst or reviewer evaluating the synthetic KiwiSaver onboarding experiment, I need Variant B's simulated user journey to faithfully reflect the stated product premise ("a 3-question quiz that recommends a base fund with one-click confirm"), so that the selected fund matches the recommended fund rather than re-rolling a random selection independently.

**Why this priority**: Currently, 63.9% of Variant B users select a different fund from what the quiz recommended because `_choose_fund` is called a second time. Fixing this aligns the synthetic data with the core business narrative.

**Independent Test**: Can be tested by running `simulate.py` and querying DuckDB to confirm $\ge 85\%$ of Variant B selectors choose the exact fund recommended in their `completed_risk_quiz` event metadata.

**Acceptance Scenarios**:
1. **Given** a user assigned to Variant B who completes the risk quiz, **When** they select a base fund, **Then** by default (90% probability) their selected fund matches `recommended_fund_id` from the quiz, with 10% exploring an alternative fund.
2. **Given** the simulator runs with the pinned seed, **When** ground-truth effect recovery is evaluated via `test_recovery.py`, **Then** the primary conversion lift recovery passes within tolerance ($|observed - expected| < 0.015$).

---

### User Story 2 - Defensively Hardened dbt Funnel & Guardrail Models (Priority: P1)

As an analytics engineer reviewing the dbt pipeline, I need the data models to handle unobserved funnel steps cleanly and enforce precise timestamp boundaries, so that metrics are robust and free of data distortion.

**Why this priority**: In `int_funnel.sql`, `fund_profile_match` currently evaluates to `0` / `false` for non-selectors instead of `NULL`. Furthermore, `switched_fund_14d` lacks an explicit interval filter (`submitted_at` to `submitted_at + 14d`).

**Independent Test**: Can be tested by running `dbt build` and asserting that users who never reached fund selection have `fund_profile_match IS NULL`, and switch events strictly fall within the 14-day post-conversion window.

**Acceptance Scenarios**:
1. **Given** a user who abandoned the funnel before reaching base fund selection, **When** `mart_experiment_users` is built, **Then** `fund_profile_match` is `NULL` (not `false`).
2. **Given** a converter who switches base funds, **When** `int_funnel` evaluates `switched_fund_14d`, **Then** the switch event timestamp is verified to occur between `submitted_at` and `submitted_at + interval 14 days`.
3. **Given** `mart_guardrails`, **When** post-selection abandonment is reported, **Then** both selector-denominated rate and reached-selection-denominated rate are clearly defined and computed.

---

### User Story 3 - Guardrail Uncertainty Quantification & Statistical Rigor (Priority: P2)

As a decision-maker or reviewer evaluating the commercial recommendation, I need to know the statistical certainty of the guardrail regressions (abandonment and 14-day regret) rather than relying solely on point estimates.

**Why this priority**: Guardrails operate on smaller sample denominators. Providing Beta-Binomial posterior credible intervals and $P(B > A)$ for regret elevates the analysis to senior-level standards.

**Independent Test**: Can be tested by running `src/analyze.py` and verifying that `results.json` and `summary.md` report 95% Credible Intervals for both guardrail metrics alongside the primary conversion metric.

**Acceptance Scenarios**:
1. **Given** the experiment results in `warehouse.duckdb`, **When** `analyze.py` runs, **Then** it computes Beta-Binomial posteriors and 95% credible intervals for abandonment and regret for both arms.
2. **Given** the frequentist cross-check, **When** calculating two-proportion confidence intervals, **Then** the critical z-value is dynamically derived from the configured `CRED` level rather than hardcoded to `1.96`.

---

### User Story 4 - Comprehensive Unit Testing & Code Quality Tooling (Priority: P2)

As a maintainer of the repository, I need unit tests for data simulation and statistical functions, as well as modern linter configuration (`ruff`), so that any future changes can be verified quickly without breaking reproducibility.

**Why this priority**: Currently, only 1 test file with 4 tests exists. Expanding unit tests for `simulate.py` and `analyze.py` ensures robust regression protection.

**Independent Test**: Can be tested by executing `uv run pytest` and `uv run ruff check .` across the repo.

**Acceptance Scenarios**:
1. **Given** `tests/test_simulate.py`, **When** pytest runs, **Then** it verifies deterministic reproducibility, JSON metadata validity, fund catalogue validity, and timestamp ordering.
2. **Given** `tests/test_analyze.py`, **When** pytest runs, **Then** it verifies mathematical correctness of Beta posteriors, decision metrics, and NPV calculations across edge cases.
3. **Given** `pyproject.toml`, **When** `ruff` is invoked, **Then** all files pass formatting and style standards.

---

### User Story 5 - Documentation, UX & Interview Alignment (Priority: P3)

As a portfolio reader or interviewer browsing the repository on GitHub, I need clean links to natively rendered notebooks, an improved HTML portal, and accurate interview notes that reflect the current notebook architecture rather than the retired Streamlit app.

**Why this priority**: Enhances the portfolio presentation and removes confusion during interview walkthroughs.

**Independent Test**: Can be tested by checking GitHub links in `README.md`, inspecting `docs/index.html`, and verifying that `interview_notes.md` / `EXPLAINER.md` correctly reference HTML and notebook walkthroughs.

**Acceptance Scenarios**:
1. **Given** `README.md`, **When** a user views the repo on GitHub, **Then** direct links to `.ipynb` files allow native rendering, and GitHub Pages instructions are clear.
2. **Given** `interview_notes.md` and `EXPLAINER.md`, **When** reviewed, **Then** references to `make app` and Streamlit tabs are replaced with the executed notebooks narrative.
3. **Given** `src/render_notebooks.py`, **When** executed on Windows, **Then** the Windows Proactor asyncio warning is cleanly suppressed.

---

## Edge Cases

- **Zero / Low Sample Subgroups**: Cohort mart and guardrail calculations must handle small or empty subsets gracefully using safe division or coalesce.
- **Timestamp Boundary Precision**: Users completing fund selection right at midnight or daylight saving shifts must evaluate correctly via timestamp intervals rather than naive calendar day diffs.
- **Extreme Statistical Arms**: Posteriors and expected loss calculations must handle 0 conversions or 100% conversion without division-by-zero errors.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `src/simulate.py` MUST preserve the quiz's `recommended_fund_id` into `selected_base_fund` for Variant B with an explicit 90% acceptance rate.
- **FR-002**: `src/simulate.py` MUST maintain deterministic reproducibility from the pinned seed.
- **FR-003**: `dbt/models/intermediate/int_funnel.sql` MUST evaluate `fund_profile_match` to `NULL` when no `selected_base_fund` event occurs.
- **FR-004**: `dbt/models/intermediate/int_funnel.sql` MUST enforce that `switched_fund_14d` requires `switched_fund_at` to fall within 14 days of `submitted_at`.
- **FR-005**: `dbt/models/marts/mart_guardrails.sql` MUST provide both selector-denominated and reached-selection-denominated abandonment metrics.
- **FR-006**: `dbt/tests/assert_ab_split_healthy.sql` MUST test sample split health via both deviation thresholds and Pearson $\chi^2$ testing.
- **FR-007**: `src/analyze.py` MUST calculate Beta-Binomial posteriors and 95% credible intervals for guardrail metrics.
- **FR-008**: `src/analyze.py` MUST export both PNG and scalable vector SVG figures.
- **FR-009**: `src/render_notebooks.py` MUST configure `WindowsSelectorEventLoopPolicy` on Windows systems to suppress ZMQ Proactor runtime warnings.
- **FR-010**: `tests/` MUST include comprehensive unit test suites for `simulate.py` and `analyze.py`.
- **FR-011**: `pyproject.toml` MUST configure `ruff` and document dependency groups.
- **FR-012**: `README.md`, `interview_notes.md`, and `EXPLAINER.md` MUST remove obsolete Streamlit references and provide direct GitHub Jupyter links.

### Key Entities

- **User**: Assigned entity with demographic attributes and experiment arm (`A` or `B`).
- **Event**: Granular UI interaction with timestamp, session, and JSON metadata.
- **FunnelMetric**: Aggregated milestone conversions anchored at fund selection.
- **GuardrailMetric**: Risk and regret health indicators (abandonment, 14-day switch, risk mismatch).
- **ExperimentDecision**: Bayesian decision-theoretic output ($P(B>A)$, expected loss, CrIs, NPV).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of Variant B selector events maintain valid quiz alignment ($\ge 85\%$ match rate).
- **SC-002**: `pytest` passes 100% of tests (recovery, simulation units, analysis units) in under 15 seconds.
- **SC-003**: `dbt build` passes all models and data tests with 0 errors and 0 warnings.
- **SC-004**: `ruff check .` runs cleanly with zero linting errors.
- **SC-005**: All notebooks render cleanly to `docs/*.html` without runtime warnings.
