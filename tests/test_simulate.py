"""Unit tests for synthetic event generator (src/simulate.py)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.simulate import FUND_CATALOG, RISK_ORDER, load_truth, make_users, simulate_events

ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = ROOT / "ground_truth.yaml"


def test_seed_determinism():
    truth = load_truth(TRUTH_PATH)
    seed = truth["experiment"]["seed"]

    rng1 = np.random.default_rng(seed)
    users1 = make_users(truth, rng1).head(500)
    rng1_exp = np.random.default_rng(seed + 1)
    events1 = simulate_events(users1, truth, rng1_exp)

    rng2 = np.random.default_rng(seed)
    users2 = make_users(truth, rng2).head(500)
    rng2_exp = np.random.default_rng(seed + 1)
    events2 = simulate_events(users2, truth, rng2_exp)

    pd.testing.assert_frame_equal(users1, users2)
    pd.testing.assert_frame_equal(events1, events2)


def test_timestamp_monotonicity():
    truth = load_truth(TRUTH_PATH)
    rng = np.random.default_rng(42)
    users = make_users(truth, rng).head(200)
    events = simulate_events(users, truth, rng)

    for _, group in events.groupby("user_id"):
        ts_list = group["event_timestamp"].tolist()
        assert ts_list == sorted(ts_list), (
            f"Timestamps out of order for user {group['user_id'].iloc[0]}"
        )


def test_metadata_json_validity():
    truth = load_truth(TRUTH_PATH)
    rng = np.random.default_rng(42)
    users = make_users(truth, rng).head(200)
    events = simulate_events(users, truth, rng)

    for _, row in events[events.metadata.notna()].iterrows():
        parsed = json.loads(row["metadata"])
        assert isinstance(parsed, dict)


def test_fund_catalog_consistency():
    truth = load_truth(TRUTH_PATH)
    rng = np.random.default_rng(42)
    users = make_users(truth, rng).head(500)
    events = simulate_events(users, truth, rng)

    sel_events = events[events.event_name == "selected_base_fund"]
    for _, row in sel_events.iterrows():
        meta = json.loads(row["metadata"])
        fund_id = meta["fund_id"]
        fund_risk = meta["fund_risk"]
        assert fund_risk in RISK_ORDER
        assert fund_id in FUND_CATALOG[fund_risk]


def test_variant_b_recommendation_retention():
    truth = load_truth(TRUTH_PATH)
    rng = np.random.default_rng(truth["experiment"]["seed"])
    users = make_users(truth, rng).head(1000)
    events = simulate_events(users, truth, rng)

    quiz_events = events[events.event_name == "completed_risk_quiz"].set_index("user_id")
    sel_events = events[events.event_name == "selected_base_fund"].set_index("user_id")

    b_common = quiz_events.index.intersection(sel_events.index)
    assert len(b_common) > 0

    matches = 0
    for uid in b_common:
        quiz_meta = json.loads(quiz_events.loc[uid, "metadata"])
        sel_meta = json.loads(sel_events.loc[uid, "metadata"])
        if quiz_meta["recommended_fund_id"] == sel_meta["fund_id"]:
            matches += 1

    match_rate = matches / len(b_common)
    # Target is ~90% adherence
    assert match_rate >= 0.85, f"Variant B recommended fund match rate too low: {match_rate:.2%}"
