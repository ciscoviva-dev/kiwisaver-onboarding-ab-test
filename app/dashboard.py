"""Interactive dashboard for the KiwiSaver onboarding A/B experiment.

Four panels: Beliefs, Evidence, Decision, Guardrails. A rollout risk-slider in
the Decision panel lets a reviewer argue with the analysis and watch the
recommendation change.

Run:  uv run streamlit run app/dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import streamlit as st

_ROOOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOOT / "src"))

import analyze as az  # noqa: E402

DB_PATH = _ROOOT / "warehouse.duckdb"

st.set_page_config(page_title="KiwiSaver onboarding A/B", layout="wide")


@st.cache_data(show_spinner=False)
def load(db_mtime: float):
    users = az.q(DB_PATH, "select * from mart_experiment_users")
    primary = az.q(DB_PATH, "select * from mart_primary_metric").set_index("variant")
    guard = az.q(DB_PATH, "select * from mart_guardrails").set_index("variant")
    cohorts = az.q(DB_PATH, "select * from mart_cohorts")
    comm = az.q(DB_PATH, "select * from mart_commercial_inputs").set_index("variant")
    return users, primary, guard, cohorts, comm


if not DB_PATH.exists():
    st.error("warehouse.duckdb not found. Run `make all` first.")
    st.stop()

users, primary, guard_df, cohorts, comm_df = load(DB_PATH.stat().st_mtime)

st.title("KiwiSaver onboarding: Bayesian A/B test")
st.caption(
    "Synthetic experiment (40k users, 14 days). Quiz-based fund selection (B) vs "
    "the standard fund list (A). Primary metric: sign-up within 7 days of viewing fund selection."
)

# --- sidebar: prior controls -------------------------------------------------
with st.sidebar:
    st.header("Beliefs (prior)")
    a0 = st.slider("Prior alpha", 1.0, 30.0, az.PRIOR_A0, 1.0)
    b0 = st.slider("Prior beta", 1.0, 30.0, az.PRIOR_B0, 1.0)
    st.caption(f"Prior mean conversion = {a0 / (a0 + b0):.1%}")
    st.header("Decision tolerance")
    loss_threshold = st.slider(
        "Acceptable expected loss (percentage points)", 0.0, 1.0, 0.25, 0.05
    )
    st.caption("The conversion you'd give up, on average, if you pick wrong.")

rng = np.random.default_rng(az.ANALYSIS_SEED)
arm_a = az.summarize_arm(int(primary.loc["A", "converted_users"]),
                         int(primary.loc["A", "reached_selection_users"]), rng, a0, b0)
arm_b = az.summarize_arm(int(primary.loc["B", "converted_users"]),
                         int(primary.loc["B", "reached_selection_users"]), rng, a0, b0)
decision = az.decision_outputs(arm_a["_draws"], arm_b["_draws"], arm_a["posterior_mean"])

# --- headline ----------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("A conversion", f"{arm_a['rate']:.2%}")
c2.metric("B conversion", f"{arm_b['rate']:.2%}", f"{decision['abs_lift_mean']:+.2%}")
c3.metric("P(B > A)", f"{decision['prob_b_beats_a']:.2%}")
c4.metric("Expected loss (choose B)", f"{decision['expected_loss_choosing_b']:.3%}")

tab_belief, tab_evidence, tab_decision, tab_guard = st.tabs(
    ["Beliefs", "Evidence", "Decision", "Guardrails"]
)

with tab_belief:
    fig, ax = az.plt.subplots(figsize=(8, 4))
    xs = np.linspace(0.30, 0.52, 1000)
    from scipy import stats as _st
    ax.plot(xs, _st.beta.pdf(xs, a0, b0), color=az.GREY, ls="--", label="Prior")
    for arm, color, label in [(arm_a, az.BLUE, "A posterior"), (arm_b, az.ORANGE, "B posterior")]:
        ax.plot(xs, _st.beta.pdf(xs, arm["posterior_alpha"], arm["posterior_beta"]),
                color=color, lw=2, label=label)
    ax.set_xlabel("Conversion rate")
    ax.set_ylabel("Density")
    ax.legend(frameon=False)
    st.pyplot(fig)

with tab_evidence:
    fig = az.plt.figure(figsize=(8, 4))
    days = np.arange(0, 8)
    for variant, color in [("A", az.BLUE), ("B", az.ORANGE)]:
        sub = users[(users.variant == variant) & users.reached_selection]
        n = len(sub)
        means = [((sub.converted_in_window) & (sub.days_to_convert <= d)).mean() for d in days]
        az.plt.plot(days, means, color=color, marker="o", label=f"Variant {variant}")
    az.plt.xlabel("Days since viewing fund selection")
    az.plt.ylabel("Cumulative conversion")
    az.plt.legend(frameon=False)
    st.pyplot(fig)
    st.caption("The gap opens early and holds -- no novelty spike that reverses.")

with tab_decision:
    st.markdown(
        f"**P(B > A) = {decision['prob_b_beats_a']:.3%}** &nbsp;|&nbsp; "
        f"absolute lift **{decision['abs_lift_mean']:+.2%}** "
        f"(95% CrI {decision['abs_lift_ci'][0]:+.2%} to {decision['abs_lift_ci'][1]:+.2%})"
    )
    thr = loss_threshold / 100.0
    if decision["expected_loss_choosing_b"] <= thr:
        candidate = 100
    elif decision["expected_loss_choosing_b"] <= 2 * thr:
        candidate = 50
    else:
        candidate = 0
    regret_ratio = (guard_df.loc["B", "fund_switch_regret_rate"]
                    / guard_df.loc["A", "fund_switch_regret_rate"])
    gated = regret_ratio > 1.5
    final = min(candidate, 25) if gated else candidate
    st.subheader(f"Recommended rollout: {final}%")
    st.write(
        f"- Conversion favours B (expected loss {decision['expected_loss_choosing_b']:.3%} "
        f"vs your {thr:.2%} threshold) -> candidate {candidate}%."
    )
    if gated:
        st.warning(
            f"Guardrail gate applied: fund-switch regret is {regret_ratio:.1f}x worse under B "
            f"({guard_df.loc['A','fund_switch_regret_rate']:.1%} -> "
            f"{guard_df.loc['B','fund_switch_regret_rate']:.1%}). Capping at 25% until the "
            "confirmation-step reassurance is added."
        )
    st.caption("Move the tolerance slider to see the recommendation change.")

with tab_guard:
    fig = az.plt.figure(figsize=(8, 4))
    labels = ["Abandonment", "14-day regret", "Fund/profile mismatch"]
    keys = ["post_selection_abandonment_rate", "fund_switch_regret_rate", "fund_profile_mismatch_rate"]
    x = np.arange(len(labels))
    w = 0.36
    az.plt.bar(x - w / 2, [guard_df.loc["A", k] for k in keys], w, color=az.BLUE, label="A")
    az.plt.bar(x + w / 2, [guard_df.loc["B", k] for k in keys], w, color=az.ORANGE, label="B")
    az.plt.xticks(x, labels, fontsize=9)
    az.plt.legend(frameon=False)
    st.pyplot(fig)
    st.caption(
        "Counter-intuitive: B *improves* fund fit (mismatch falls) yet raises regret. "
        "The likely mechanism is speed -- the quiz short-circuits the deliberation that "
        "normally precedes a commitment, so more users later revisit their choice. That is "
        "the reason to stage the rollout, not a fund-selection problem."
    )

st.divider()
commercial = az.commercial_model(
    {"A": arm_a, "B": arm_b},
    {
        "converters": int(comm_df.loc["A", "converters"]),
        "converters_with_balance": int(comm_df.loc["A", "converters_with_balance"]),
        "mean_transfer_balance_nzd": float(comm_df.loc["A", "mean_transfer_balance_nzd"]),
    },
)
with st.expander("Exec summary", expanded=True):
    import json as _json
    import os as _os

    guard = {v: {k: float(guard_df.loc[v, k]) for k in
                 ["post_selection_abandonment_rate", "fund_switch_regret_rate",
                  "fund_profile_mismatch_rate"]}
             for v in ["A", "B"]}
    payload = az.summary_payload({"A": arm_a, "B": arm_b}, decision,
                                 {"z": 0.0, "p_value": 0.0}, guard, commercial)
    payload["frequentist"] = {"note": "z/p computed in notebooks; see reports/summary.md"}

    llm_available = bool(_os.environ.get("ANTHROPIC_API_KEY"))
    cache_key = f"llm_summary::{hash(_json.dumps(payload, sort_keys=True))}"

    col1, col2 = st.columns([4, 1])
    with col2:
        gen = st.button("Write with Claude", disabled=not llm_available,
                        help=None if llm_available else "Set ANTHROPIC_API_KEY to enable")
    if gen:
        with st.spinner("Asking Claude..."):
            st.session_state[cache_key] = az.llm_summary(payload)

    llm_text = st.session_state.get(cache_key)
    if llm_text:
        st.markdown(llm_text)
        st.caption(f"- written by `{_os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')}` "
                   "from the numbers above only")
    else:
        st.markdown(az.deterministic_summary(payload))
        st.caption(
            "Deterministic template. "
            + ("Click **Write with Claude** for the LLM version."
               if llm_available else
               "Set `ANTHROPIC_API_KEY` to enable the LLM-written version "
               "(falls back to this template otherwise).")
        )
