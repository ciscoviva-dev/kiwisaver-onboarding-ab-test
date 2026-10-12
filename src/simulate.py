"""Generate the synthetic KiwiSaver onboarding A/B dataset.

Reads the true parameters from ground_truth.yaml and emits two raw tables:

    data/raw/events.parquet  -- one row per UI event (the messy raw layer)
    data/raw/users.parquet   -- one row per user (assignment + attributes)

The dataset is deterministic: the same seed always produces byte-identical
output, so the whole repo is reproducible from the committed simulator.

It is deliberately *raw*: events carry JSON metadata and no analysis-ready
flags. Turning these tables into experiment metrics is the job of the dbt
models in dbt/.

Usage:
    uv run python src/simulate.py [--truth ground_truth.yaml] [--out data/raw]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

APP_VERSIONS = ["8.12.0", "8.13.0", "8.14.1"]
EXPERIMENT_STEP_ORDER = [
    "viewed_kiwisaver_landing",
    "started_questionnaire",
    "completed_questionnaire",
    "viewed_fund_selection",
    "browsed_fund_list",       # control intervention
    "completed_risk_quiz",     # variant intervention
    "selected_base_fund",
    "added_self_select",
    "confirmed_plan",
    "submitted_application",
    "transfer_balance_set",
    "contribution_setup_completed",
    "switched_base_fund",      # 14-day regret guardrail
]

# The 11 real Sharesies KiwiSaver base funds, grouped by risk.
FUND_CATALOG = {
    "conservative": ["Sharesies Smart Conservative Fund"],
    "balanced": ["Sharesies Smart Balanced Fund", "Sharesies Milford Balanced Fund"],
    "growth": [
        "Sharesies Pathfinder Ethical Growth Fund",
        "Sharesies Smart Growth Fund",
        "Sharesies Fisher Funds Growth Fund",
    ],
    "high_growth": [
        "Sharesies Milford Aggressive Fund",
        "Sharesies US500 Fund",
        "Sharesies Total World Share Fund",
        "Sharesies Generate Focused Growth Fund",
        "Sharesies Pie Global Growth 2 Fund",
    ],
}
RISK_ORDER = ["conservative", "balanced", "growth", "high_growth"]


def load_truth(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _pick(rng: np.random.Generator, weights: dict) -> np.ndarray:
    keys = list(weights.keys())
    probs = np.array([weights[k] for k in keys], dtype=float)
    probs = probs / probs.sum()
    return rng.choice(keys, size=None, p=probs)


def _pick_many(rng: np.random.Generator, weights: dict, n: int) -> np.ndarray:
    keys = list(weights.keys())
    probs = np.array([weights[k] for k in keys], dtype=float)
    probs = probs / probs.sum()
    return rng.choice(keys, size=n, p=probs)


def make_users(truth: dict, rng: np.random.Generator) -> pd.DataFrame:
    exp = truth["experiment"]
    pop = truth["population"]
    n = exp["n_users"]
    start = pd.Timestamp(exp["start_date"], tz="UTC")
    duration = exp["duration_days"]

    variant = rng.choice(
        ["A", "B"], size=n, p=[exp["split"]["control"], exp["split"]["variant"]]
    )
    # Users arrive uniformly across the experiment window.
    offset_hours = rng.uniform(0, duration * 24, size=n)
    assigned_at = start + pd.to_timedelta(offset_hours, unit="h")

    users = pd.DataFrame(
        {
            "user_id": [f"u_{i:06d}" for i in range(n)],
            "experiment_id": exp["experiment_id"],
            "variant": variant,
            "assigned_at": assigned_at,
            "market": "nz",
            "is_existing_kiwisaver": rng.random(n) < pop["is_existing_kiwisaver_prob"],
            "device": _pick_many(rng, pop["device_weights"], n),
            "channel": _pick_many(rng, pop["channel_weights"], n),
            "age_band": _pick_many(rng, pop["age_band_weights"], n),
            "sex": _pick_many(rng, pop["sex_weights"], n),
            "income_band": _pick_many(rng, pop["income_band_weights"], n),
            "fund_risk_profile": _pick_many(rng, pop["risk_profile_weights"], n),
            "app_version": rng.choice(APP_VERSIONS, size=n),
        }
    )
    return users


def _advance(
    rng: np.random.Generator, truth: dict, cond_key: str, arm_row: pd.Series
) -> bool:
    probs = truth["funnel"][cond_key]
    p = probs["control"] if arm_row["variant"] == "A" else probs["variant"]
    return rng.random() < p


def _conversion_delay_days(rng: np.random.Generator, truth: dict) -> float:
    t = truth["timing"]["conversion_delay_days"]
    u = rng.random()
    if u < t["same_session_prob"]:
        return rng.uniform(0, 1 / 24)          # < 1 hour
    u -= t["same_session_prob"]
    if u < t["within_1_day_prob"]:
        return rng.uniform(1 / 24, 1)          # 1h - 1d
    u -= t["within_1_day_prob"]
    if u < t["within_3_days_prob"]:
        return rng.uniform(1, 3)               # 1 - 3d
    return rng.uniform(3, 7)                   # 3 - 7d (window edge)


def _choose_fund(
    rng: np.random.Generator, profile: str, variant: str
) -> tuple[str, str]:
    """Return (fund_id, category).

    Variant B's quiz is *better aligned* to the risk profile (lower mismatch) but
    has a mild growth tilt; variant A's browse-the-list users pick an adjacent,
    often mismatched, fund more often (decision paralysis).
    """
    idx = RISK_ORDER.index(profile)
    cat_idx = idx
    if variant == "A":
        # Decision paralysis -> some users pick an adjacent (often mismatched) fund.
        if rng.random() < 0.25:
            cat_idx = int(np.clip(idx + rng.choice([-1, 1]), 0, len(RISK_ORDER) - 1))
    else:
        # Quiz over-recommends higher growth -> the mechanistic cause of regret.
        if rng.random() < 0.15 and idx < len(RISK_ORDER) - 1:
            cat_idx = idx + 1
    category = RISK_ORDER[cat_idx]
    fund = str(rng.choice(FUND_CATALOG[category]))
    return fund, category


def simulate_events(
    users: pd.DataFrame, truth: dict, rng: np.random.Generator
) -> pd.DataFrame:
    exp = truth["experiment"]
    rows: list[dict] = []
    counter = 0

    def emit(
        user: pd.Series,
        session_id: str,
        ts: pd.Timestamp,
        name: str,
        metadata: dict | None = None,
    ) -> None:
        nonlocal counter
        rows.append(
            {
                "event_id": f"evt_{counter:09d}",
                "user_id": user["user_id"],
                "session_id": session_id,
                "event_timestamp": ts,
                "event_name": name,
                "experiment_id": exp["experiment_id"],
                "variant": user["variant"],
                "platform": user["device"],
                "acquisition_channel": user["channel"],
                "app_version": user["app_version"],
                "metadata": json.dumps(metadata) if metadata else None,
            }
        )
        counter += 1

    for _, user in users.iterrows():
        session_id = f"sess_{user['user_id']}"
        t = user["assigned_at"]

        def tick(lo: float, hi: float) -> pd.Timestamp:
            return t + pd.Timedelta(seconds=float(rng.uniform(lo, hi)))

        emit(user, session_id, t, "viewed_kiwisaver_landing")

        if not _advance(rng, truth, "landing_to_started", user):
            continue
        t = tick(20, 90)
        emit(user, session_id, t, "started_questionnaire")

        if not _advance(rng, truth, "started_to_completed_q", user):
            continue
        t = tick(60, 240)
        emit(user, session_id, t, "completed_questionnaire")

        if not _advance(rng, truth, "completed_q_to_viewed_sel", user):
            continue
        t = tick(3, 20)
        emit(user, session_id, t, "viewed_fund_selection")
        intervention_ts = t

        if user["variant"] == "A":
            t = tick(60, 180)
            emit(
                user, session_id, t, "browsed_fund_list",
                {"funds_viewed": int(rng.integers(2, 11))},
            )
        else:
            t = tick(60, 180)
            rec_fund, _ = _choose_fund(rng, user["fund_risk_profile"], "B")
            emit(
                user, session_id, t, "completed_risk_quiz",
                {"recommended_fund_id": rec_fund, "questions": 3},
            )
        intervention_ts = t

        if not _advance(rng, truth, "viewed_sel_to_selected", user):
            continue

        fund_id, fund_cat = _choose_fund(rng, user["fund_risk_profile"], user["variant"])
        t = intervention_ts + pd.Timedelta(seconds=float(rng.uniform(20, 90)))
        emit(
            user, session_id, t, "selected_base_fund",
            {
                "fund_id": fund_id,
                "fund_risk": fund_cat,
                "profile_risk": user["fund_risk_profile"],
                "match": fund_cat == user["fund_risk_profile"],
            },
        )
        selected_ts = t

        if rng.random() < 0.30:
            t = selected_ts + pd.Timedelta(seconds=float(rng.uniform(30, 120)))
            emit(user, session_id, t, "added_self_select", {"picks": int(rng.integers(1, 5))})

        if not _advance(rng, truth, "selected_to_confirmed", user):
            continue

        # Converters may finish across sessions, giving a 0-7 day conversion curve.
        delay = _conversion_delay_days(rng, truth)
        span = pd.Timedelta(days=delay)
        confirm_ts = intervention_ts + span * 0.6
        if confirm_ts < selected_ts:
            confirm_ts = selected_ts + pd.Timedelta(seconds=float(rng.uniform(20, 60)))
        emit(user, session_id, confirm_ts, "confirmed_plan")

        if not _advance(rng, truth, "confirmed_to_submitted", user):
            continue
        submit_ts = intervention_ts + span
        if submit_ts < confirm_ts:
            submit_ts = confirm_ts + pd.Timedelta(seconds=float(rng.uniform(10, 40)))
        emit(user, session_id, submit_ts, "submitted_application")

        # --- secondary metrics, measured among converters ---
        sec = truth["secondary"]
        bal_p = (
            sec["transfer_balance_prob"]["control"]
            if user["variant"] == "A"
            else sec["transfer_balance_prob"]["variant"]
        )
        if rng.random() < bal_p:
            ln = sec["transfer_balance_lognormal"]
            shift = ln["control_shift"] if user["variant"] == "A" else ln["variant_shift"]
            amount = float(
                np.exp(np.log(ln["median_nzd"]) + ln["sigma"] * rng.standard_normal() + shift)
            )
            emit(
                user, session_id, submit_ts + pd.Timedelta(hours=float(rng.uniform(1, 48))),
                "transfer_balance_set", {"amount_nzd": round(amount, 2)},
            )

        contrib_p = (
            sec["contribution_setup_30d_prob"]["control"]
            if user["variant"] == "A"
            else sec["contribution_setup_30d_prob"]["variant"]
        )
        if rng.random() < contrib_p:
            emit(
                user, session_id,
                submit_ts + pd.Timedelta(days=float(rng.uniform(1, 30))),
                "contribution_setup_completed", None,
            )

        # --- 14-day regret guardrail ---
        g = truth["guardrails"]["fund_switch_regret_14d"]
        regret_p = g["control"] if user["variant"] == "A" else g["variant"]
        if rng.random() < regret_p:
            new_fund, new_cat = _choose_fund(rng, user["fund_risk_profile"], user["variant"])
            emit(
                user, session_id,
                submit_ts + pd.Timedelta(days=float(rng.uniform(1, 14))),
                "switched_base_fund",
                {"from_fund_id": fund_id, "to_fund_id": new_fund, "to_risk": new_cat},
            )

    return pd.DataFrame(rows, columns=[
        "event_id", "user_id", "session_id", "event_timestamp", "event_name",
        "experiment_id", "variant", "platform", "acquisition_channel",
        "app_version", "metadata",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", default="ground_truth.yaml")
    parser.add_argument("--out", default="data/raw")
    args = parser.parse_args()

    truth = load_truth(Path(args.truth))
    rng = np.random.default_rng(truth["experiment"]["seed"])

    users = make_users(truth, rng)
    events = simulate_events(users, truth, rng)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    users.to_parquet(out / "users.parquet", index=False)
    events.to_parquet(out / "events.parquet", index=False)

    n_conv = (
        events[events.event_name == "submitted_application"]
        .groupby("variant").size().reindex(["A", "B"]).fillna(0).astype(int)
    )
    print(f"users={len(users):,}  events={len(events):,}")
    print(f"conversions: A={n_conv['A']:,}  B={n_conv['B']:,}")
    print(f"-> {out/'users.parquet'}\n-> {out/'events.parquet'}")


if __name__ == "__main__":
    main()
