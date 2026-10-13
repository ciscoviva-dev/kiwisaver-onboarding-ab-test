# Tasks: Codebase Review & Quality Improvements

**Input**: Design documents from `.specify/specs/codebase-review-and-improvements/`
**Prerequisites**: `spec.md`, `plan.md`

## Organization
Tasks are organized by User Story and Phase to enable independent implementation, testing, and progressive verification.

- **[P]**: Can run in parallel
- **[Story]**: US1 (Simulator), US2 (dbt Models), US3 (Analyze/Stats), US4 (Testing/Tooling), US5 (Docs/UX)

---

## Phase 1: Setup & Developer Tooling (US4)

- [x] T001 [P] [US4] Update `pyproject.toml` to add `ruff>=0.8.0` to `[dependency-groups] dev` and configure `[tool.ruff]`.
- [x] T002 [US4] Run `uv sync` to install dev dependencies including ruff.

---

## Phase 2: User Story 1 - Simulator Recommendation Continuity & Data Correctness (Priority: P1)

**Goal**: Ensure Variant B user journey preserves the recommended fund from the risk quiz with an explicit 90% adherence rate, and optimize simulator performance.
**Independent Test**: `tests/test_simulate.py` verifies seed determinism, valid catalog matches, and quiz recommendation alignment.

- [x] T003 [P] [US1] Create unit tests in `tests/test_simulate.py` checking seed reproducibility, timestamp sequence, metadata schema, and recommendation retention.
- [x] T004 [US1] Modify `src/simulate.py` to preserve `rec_fund` / `rec_cat` into `selected_base_fund` (90% adopt, 10% override) and refactor `tick` closure.
- [x] T005 [US1] Execute `uv run python src/simulate.py` to regenerate `data/raw/users.parquet` and `data/raw/events.parquet`.
- [x] T006 [US1] Run `uv run pytest tests/test_simulate.py` to verify simulator tests pass.

---

## Phase 3: User Story 2 - Defensively Hardened dbt Funnel & Guardrail Models (Priority: P1)

**Goal**: Harden dbt models for proper NULL propagation, enforce timestamp interval windows for regret, and support dual abandonment denominators.
**Independent Test**: `uv run dbt build --project-dir dbt --profiles-dir dbt` passes with 0 errors.

- [x] T007 [US2] Update `dbt/models/intermediate/int_funnel.sql` to cleanly return `NULL` for `fund_profile_match` on non-selectors, and filter `switched_fund_14d` strictly between `submitted_at` and `submitted_at + interval 14 days`.
- [x] T008 [US2] Update `dbt/models/marts/mart_guardrails.sql` to output both `post_selection_abandonment_reached_rate` and `post_selection_abandonment_selector_rate`, retaining backwards-compatible aliases.
- [x] T009 [US2] Update `dbt/models/marts/schema.yml` to validate new guardrail columns.
- [x] T010 [US2] Update `dbt/tests/assert_ab_split_healthy.sql` to include Pearson $\chi^2$ goodness-of-fit alongside percentage deviation.
- [x] T011 [US2] Run `uv run dbt build --project-dir dbt --profiles-dir dbt` and `uv run pytest tests/test_recovery.py` to confirm model build and effect recovery.

---

## Phase 4: User Story 3 - Guardrail Uncertainty Quantification & Statistical Rigor (Priority: P2)

**Goal**: Model uncertainty on guardrails via Beta-Binomial posteriors, dynamically compute critical z-scores, add inline baseline annotations, and export SVG charts.
**Independent Test**: `tests/test_analyze.py` passes and `reports/results.json` contains credible intervals for guardrail rates.

- [x] T012 [P] [US3] Create unit tests in `tests/test_analyze.py` verifying `beta_posterior`, `decision_outputs`, `frequentist_crosscheck`, and `npv5` closed-form solutions.
- [x] T013 [US3] Update `src/analyze.py` to compute Beta posteriors and 95% CrIs for abandonment and regret, replace hardcoded 1.96 with dynamic critical z-value, add baseline AUM comments, and save vector `.svg` figures.
- [x] T014 [US3] Run `uv run python src/analyze.py` and verify `reports/results.json`, `reports/summary.md`, and `reports/figures/` update cleanly.
- [x] T015 [US3] Run `uv run pytest tests/test_analyze.py` to verify all analysis unit tests pass.

---

## Phase 5: User Story 5 - Documentation, UX & Interview Alignment (Priority: P3)

**Goal**: Fix Windows asyncio warning, eliminate stale Streamlit references, add direct GitHub Jupyter links, and enhance the docs portal.
**Independent Test**: `uv run python src/render_notebooks.py` runs without Windows Proactor warnings, and `docs/index.html` displays refined portal navigation.

- [x] T016 [US5] Update `src/render_notebooks.py` to configure `WindowsSelectorEventLoopPolicy` on Windows and enhance `index_page()` with direct notebook links.
- [x] T017 [US5] Update `README.md` to link directly to `notebooks/01_eda.ipynb`, `02_ab_test.ipynb`, and `03_bandits_and_peeking.ipynb` for GitHub web viewers, and document dual guardrail metrics.
- [x] T018 [US5] Update `interview_notes.md` and `EXPLAINER.md` to replace retired Streamlit demo instructions with the executed notebooks and HTML portal walkthrough.
- [x] T019 [US5] Re-render notebooks via `uv run python src/render_notebooks.py`.

---

## Phase 6: End-to-End Verification & Quality Audit (All Stories)

- [x] T020 Run full test suite: `uv run pytest -v` (asserting all recovery and unit tests pass).
- [x] T021 Run full dbt test suite: `uv run dbt test --project-dir dbt --profiles-dir dbt`.
- [x] T022 Run `uv run ruff check .` and `uv run ruff format --check .` to ensure pristine code style.
- [x] T023 Run `git status` to verify repository cleanliness and prepare walkthrough report.
