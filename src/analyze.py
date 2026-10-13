"""Analyse the KiwiSaver onboarding experiment and write reports.

Pipeline:  DuckDB marts (dbt)  ->  this script  ->  reports/figures + reports/*.json/md

Reads ONLY the built marts (never ground_truth.yaml). Produces:
  * conjugate Beta-Binomial posteriors + decision-theoretic outputs
  * a frequentist two-proportion cross-check
  * guardrail comparisons
  * a first-year + 5-year NPV commercial estimate
  * figures + a machine-readable results.json

Usage:
    uv run python src/analyze.py [--db warehouse.duckdb] [--out reports]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import matplotlib

# Use the headless Agg backend when run as a script, but leave the backend alone
# inside a notebook (where `%matplotlib inline` must keep working). `get_ipython`
# only exists in an IPython/Jupyter kernel.
try:
    get_ipython  # type: ignore[name-defined]  # noqa: B018
except NameError:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# --- modelling configuration (analysis-time, not ground truth) ---------------
ANALYSIS_SEED = 20261013
N_DRAWS = 200_000
PRIOR_A0, PRIOR_B0 = 4.0, 6.0          # weakly informative, mean 0.40
SENS_A0, SENS_B0 = 1.0, 1.0            # uninformative sensitivity prior
CRED = 0.95

# --- commercial assumptions (see assumptions.md) -----------------------------
PLATFORM_REVENUE_RATE = 0.0075   # blended provider margin + self-select admin
RETENTION_ANNUAL = 0.92
DISCOUNT_RATE = 0.08
BALANCE_GROWTH = 0.06
HORIZON_YEARS = 5
EXPERIMENT_DAYS = 14
STAGED_EXPOSURE = 0.25           # headline recommendation: roll to 25%

BLUE, ORANGE, GREY = "#2b6cb0", "#dd6b20", "#718096"


def q(db: Path, sql: str):
    with duckdb.connect(str(db), read_only=True) as con:
        return con.execute(sql).df()


def beta_posterior(y: int, n: int, a0: float = PRIOR_A0, b0: float = PRIOR_B0):
    return a0 + y, b0 + (n - y)


def summarize_arm(y: int, n: int, rng: np.random.Generator, a0, b0) -> dict:
    a, b = beta_posterior(y, n, a0, b0)
    draws = rng.beta(a, b, N_DRAWS)
    lo, hi = np.quantile(draws, [(1 - CRED) / 2, 1 - (1 - CRED) / 2])
    return {
        "n": int(n),
        "converted": int(y),
        "rate": y / n,
        "posterior_alpha": a,
        "posterior_beta": b,
        "posterior_mean": a / (a + b),
        "credible_interval": [float(lo), float(hi)],
        "_draws": draws,  # internal, stripped before serialisation
    }


def decision_outputs(draws_a: np.ndarray, draws_b: np.ndarray, a_mean: float) -> dict:
    diff = draws_b - draws_a
    rel = diff / draws_a
    return {
        "prob_b_beats_a": float(np.mean(draws_b > draws_a)),
        "expected_loss_choosing_b": float(np.mean(np.maximum(draws_a - draws_b, 0))),
        "expected_loss_choosing_a": float(np.mean(np.maximum(draws_b - draws_a, 0))),
        "abs_lift_mean": float(diff.mean()),
        "abs_lift_ci": [float(np.quantile(diff, 0.025)), float(np.quantile(diff, 0.975))],
        "rel_lift_mean": float(rel.mean()),
        "rel_lift_ci": [float(np.quantile(rel, 0.025)), float(np.quantile(rel, 0.975))],
        "prob_lift_gt_1pp": float(np.mean(diff > 0.01)),
        "prob_lift_gt_2pp": float(np.mean(diff > 0.02)),
        "baseline_rate": float(a_mean),
    }


def frequentist_crosscheck(y_a, n_a, y_b, n_b) -> dict:
    p_a, p_b = y_a / n_a, y_b / n_b
    pooled = (y_a + y_b) / (n_a + n_b)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    se_unpooled = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    diff = p_b - p_a
    return {
        "z": float(z),
        "p_value": float(p_value),
        "abs_lift": float(diff),
        "ci95": [float(diff - 1.96 * se_unpooled), float(diff + 1.96 * se_unpooled)],
    }


def npv5(annual_revenue: float) -> float:
    return sum(
        annual_revenue * (1 + BALANCE_GROWTH) ** (t - 1) * RETENTION_ANNUAL ** (t - 1)
        / (1 + DISCOUNT_RATE) ** t
        for t in range(1, HORIZON_YEARS + 1)
    )


def commercial_model(primary: dict, commercial: dict) -> dict:
    reached = primary["A"]["n"] + primary["B"]["n"]
    annual_reached = reached * (365 / EXPERIMENT_DAYS)
    lift = primary["B"]["rate"] - primary["A"]["rate"]

    # expected AUM per converter (balances only apply to a subset)
    c = commercial
    aum = (c["converters_with_balance"] / c["converters"]) * c["mean_transfer_balance_nzd"]
    annual_rev_per_member = aum * PLATFORM_REVENUE_RATE

    delta_members_annual = lift * annual_reached
    return {
        "expected_aum_per_converter_nzd": float(aum),
        "annual_revenue_per_member_nzd": float(annual_rev_per_member),
        "npv5_per_member_nzd": float(npv5(annual_rev_per_member)),
        "incremental_members_annual": float(delta_members_annual),
        "first_year_revenue_full_rollout_nzd": float(delta_members_annual * annual_rev_per_member),
        "npv5_full_rollout_nzd": float(delta_members_annual * npv5(annual_rev_per_member)),
        "npv5_staged_25pct_nzd": float(delta_members_annual * npv5(annual_rev_per_member) * STAGED_EXPOSURE),
        "staged_exposure": STAGED_EXPOSURE,
    }


# --- plain-English summary ----------------------------------------------------
RECOMMENDATION = (
    "Stage the rollout to 25% with a confirmation-step reassurance, then "
    "re-evaluate before scaling to 50% and 100%."
)


def summary_payload(primary: dict, decision: dict, freq: dict,
                    guard: dict, commercial: dict) -> dict:
    """Assemble the exact numbers the summary is allowed to use."""
    return {
        "primary": {
            "control_rate": round(primary["A"]["rate"], 4),
            "variant_rate": round(primary["B"]["rate"], 4),
        },
        "decision": {
            "abs_lift": round(decision["abs_lift_mean"], 4),
            "abs_lift_ci95": [round(decision["abs_lift_ci"][0], 4),
                              round(decision["abs_lift_ci"][1], 4)],
            "prob_b_beats_a": round(decision["prob_b_beats_a"], 4),
            "expected_loss_choosing_b": round(decision["expected_loss_choosing_b"], 6),
        },
        "frequentist": {"z": round(freq["z"], 2), "p_value": freq["p_value"]},
        "guardrails": {
            "abandonment": {k: round(v["post_selection_abandonment_rate"], 4) for k, v in guard.items()},
            "regret_14d": {k: round(v["fund_switch_regret_rate"], 4) for k, v in guard.items()},
            "fund_mismatch": {k: round(v["fund_profile_mismatch_rate"], 4) for k, v in guard.items()},
        },
        "commercial": {
            "incremental_members_annual": round(commercial["incremental_members_annual"]),
            "npv5_full_rollout_nzd": round(commercial["npv5_full_rollout_nzd"]),
            "npv5_staged_25pct_nzd": round(commercial["npv5_staged_25pct_nzd"]),
        },
        "recommendation": RECOMMENDATION,
    }


def deterministic_summary(p: dict) -> str:
    d, g, c = p["decision"], p["guardrails"], p["commercial"]
    return (
        f"Variant B lifts sign-up conversion from {p['primary']['control_rate']:.2%} to "
        f"{p['primary']['variant_rate']:.2%} ({d['abs_lift']:+.2%}, 95% CrI "
        f"{d['abs_lift_ci95'][0]:+.2%} to {d['abs_lift_ci95'][1]:+.2%}), with a "
        f"{d['prob_b_beats_a']:.1%} probability of being the better arm. "
        f"That is worth about {c['npv5_staged_25pct_nzd']:,.0f} NZD in 5-year NPV at a "
        f"staged 25% rollout (~{c['incremental_members_annual']:,} members/yr annualised). "
        f"But B also raises post-selection abandonment from {g['abandonment']['A']:.1%} to "
        f"{g['abandonment']['B']:.1%} and 14-day fund-switch regret from "
        f"{g['regret_14d']['A']:.1%} to {g['regret_14d']['B']:.1%} (it *improves* fund fit). "
        f"Recommendation: {p['recommendation']}"
    )


# --- figures -----------------------------------------------------------------
def fig_prior_posterior(arm_a, arm_b, out: Path) -> None:
    xs = np.linspace(0.30, 0.52, 1000)
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    ax.plot(xs, stats.beta.pdf(xs, PRIOR_A0, PRIOR_B0), color=GREY, ls="--",
            label=f"Prior Beta({PRIOR_A0:g},{PRIOR_B0:g})")
    for arm, color, label in [(arm_a, BLUE, "A (control)"), (arm_b, ORANGE, "B (quiz)")]:
        ax.plot(xs, stats.beta.pdf(xs, arm["posterior_alpha"], arm["posterior_beta"]),
                color=color, lw=2, label=f"{label} posterior")
        lo, hi = arm["credible_interval"]
        ax.axvline(arm["posterior_mean"], color=color, lw=0.8, alpha=0.5)
    ax.set_xlabel("Conversion rate (within 7 days of fund selection)")
    ax.set_ylabel("Density")
    ax.set_title("Beliefs: prior vs posterior conversion by arm")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_prior_posterior.png")
    plt.close(fig)


def fig_cumulative(users_df, out: Path) -> None:
    days = np.arange(0, 8)
    rng = np.random.default_rng(ANALYSIS_SEED)
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    for variant, color in [("A", BLUE), ("B", ORANGE)]:
        sub = users_df[(users_df.variant == variant) & users_df.reached_selection]
        n = len(sub)
        means, los, his = [], [], []
        for d in days:
            y = int(((sub.converted_in_window) & (sub.days_to_convert <= d)).sum())
            a, b = beta_posterior(y, n)
            dr = rng.beta(a, b, 20000)
            means.append(dr.mean())
            lo, hi = np.quantile(dr, [0.025, 0.975])
            los.append(lo)
            his.append(hi)
        ax.plot(days, means, color=color, marker="o", label=f"Variant {variant}")
        ax.fill_between(days, los, his, color=color, alpha=0.15)
    ax.set_xlabel("Days since viewing fund selection")
    ax.set_ylabel("Cumulative conversion rate")
    ax.set_title("Evidence accumulates: cumulative conversion (95% CrI)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_cumulative_conversion.png")
    plt.close(fig)


def fig_guardrails(guard: dict, out: Path) -> None:
    labels = ["Post-selection\nabandonment", "14-day\nfund-switch regret", "Fund/profile\nmismatch"]
    keys = ["post_selection_abandonment_rate", "fund_switch_regret_rate", "fund_profile_mismatch_rate"]
    a = [guard["A"][k] for k in keys]
    b = [guard["B"][k] for k in keys]
    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    ax.bar(x - w / 2, a, w, color=BLUE, label="A (control)")
    ax.bar(x + w / 2, b, w, color=ORANGE, label="B (quiz)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Rate")
    ax.set_title("Guardrails: a mixed verdict (B raises abandonment + regret, improves fund fit)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_guardrails.png")
    plt.close(fig)


def fig_cohorts(cohorts, out: Path) -> None:
    sub = cohorts[cohorts.segment_type == "fund_risk_profile"]
    order = ["conservative", "balanced", "growth", "high_growth"]
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    x = np.arange(len(order))
    w = 0.36
    for i, (variant, color) in enumerate([("A", BLUE), ("B", ORANGE)]):
        vals = [
            float(sub[(sub.segment == s) & (sub.variant == variant)]["conversion_rate"].iloc[0])
            if len(sub[(sub.segment == s) & (sub.variant == variant)]) else 0.0
            for s in order
        ]
        ax.bar(x + (i - 0.5) * w, vals, w, color=color, label=f"Variant {variant}")
    ax.set_xticks(x)
    ax.set_xticklabels(order, fontsize=8)
    ax.set_ylabel("Conversion rate")
    ax.set_title("Where the uplift lands: conversion by fund risk profile")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "fig_cohorts.png")
    plt.close(fig)


def main() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="warehouse.duckdb")
    ap.add_argument("--out", default="reports")
    args = ap.parse_args()

    db = Path(args.db)
    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)

    users_df = q(db, "select * from mart_experiment_users")
    primary_df = q(db, "select * from mart_primary_metric").set_index("variant")
    guard_df = q(db, "select * from mart_guardrails").set_index("variant")
    comm_df = q(db, "select * from mart_commercial_inputs").set_index("variant")
    cohorts = q(db, "select * from mart_cohorts")

    rng = np.random.default_rng(ANALYSIS_SEED)
    arm_a = summarize_arm(int(primary_df.loc["A", "converted_users"]),
                          int(primary_df.loc["A", "reached_selection_users"]), rng, PRIOR_A0, PRIOR_B0)
    arm_b = summarize_arm(int(primary_df.loc["B", "converted_users"]),
                          int(primary_df.loc["B", "reached_selection_users"]), rng, PRIOR_A0, PRIOR_B0)
    decision = decision_outputs(arm_a["_draws"], arm_b["_draws"], arm_a["posterior_mean"])
    freq = frequentist_crosscheck(arm_a["converted"], arm_a["n"], arm_b["converted"], arm_b["n"])

    commercial = commercial_model(
        {"A": arm_a, "B": arm_b},
        {
            "converters": int(comm_df.loc["A", "converters"]),
            "converters_with_balance": int(comm_df.loc["A", "converters_with_balance"]),
            "mean_transfer_balance_nzd": float(comm_df.loc["A", "mean_transfer_balance_nzd"]),
        },
    )

    guard = {
        v: {k: float(guard_df.loc[v, k]) for k in
            ["post_selection_abandonment_rate", "fund_switch_regret_rate", "fund_profile_mismatch_rate"]}
        for v in ["A", "B"]
    }

    # figures
    figdir = out / "figures"
    fig_prior_posterior(arm_a, arm_b, figdir)
    fig_cumulative(users_df, figdir)
    fig_guardrails(guard, figdir)
    fig_cohorts(cohorts, figdir)

    # plain-English summary payload + text
    payload = summary_payload({"A": arm_a, "B": arm_b}, decision, freq, guard, commercial)

    # serialise (drop internal draws)
    clean = lambda d: {k: v for k, v in d.items() if not k.startswith("_")}
    results = {
        "primary": {"A": clean(arm_a), "B": clean(arm_b)},
        "decision": decision,
        "frequentist": freq,
        "guardrails": guard,
        "commercial": commercial,
        "exec_summary": deterministic_summary(payload),
        "summary_payload": payload,
        "config": {
            "prior": [PRIOR_A0, PRIOR_B0],
            "sensitivity_prior": [SENS_A0, SENS_B0],
            "credible": CRED,
            "n_draws": N_DRAWS,
        },
    }
    with (out / "results.json").open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    # plain-English summary
    d = decision
    lines = [
        "# Results summary",
        "",
        deterministic_summary(payload),
        "",
        "---",
        f"- **Primary conversion**: A = {arm_a['rate']:.2%}, B = {arm_b['rate']:.2%}"
        f" (absolute lift **{d['abs_lift_mean']:+.2%}**, 95% CrI "
        f"{d['abs_lift_ci'][0]:+.2%} to {d['abs_lift_ci'][1]:+.2%})",
        f"- **P(B > A)** = {d['prob_b_beats_a']:.3%}  |  "
        f"expected loss of choosing B = {d['expected_loss_choosing_b']:.4%}",
        f"- **Frequentist cross-check**: z = {freq['z']:.2f}, p = {freq['p_value']:.2e}",
        f"- **Guardrails**: abandonment {guard['A']['post_selection_abandonment_rate']:.1%} -> "
        f"{guard['B']['post_selection_abandonment_rate']:.1%}; "
        f"regret {guard['A']['fund_switch_regret_rate']:.1%} -> {guard['B']['fund_switch_regret_rate']:.1%}",
        f"- **Commercial**: +{commercial['incremental_members_annual']:,.0f} members/yr;"
        f" 5-yr NPV ~ ${commercial['npv5_full_rollout_nzd']:,.0f} (full) /"
        f" ${commercial['npv5_staged_25pct_nzd']:,.0f} (staged 25%)",
    ]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print((out / "summary.md").read_text(encoding="utf-8"))
    print(f"\nfigures -> {figdir}")


if __name__ == "__main__":
    main()
