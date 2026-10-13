"""Effect-recovery test.

The whole point of simulating data with a *known* injected effect is that we can
assert the pipeline recovers it. These tests read the built marts and compare
against the committed ground truth (an oracle the analysis itself never sees).

Skipped automatically if the warehouse has not been built yet (run `make all`).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "warehouse.duckdb"
TRUTH = yaml.safe_load((ROOT / "ground_truth.yaml").read_text(encoding="utf-8"))


def _query(sql: str):
    if not WAREHOUSE.exists():
        pytest.skip("warehouse.duckdb not built; run `make all` first")
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        return con.execute(sql).df()


def _ground_truth_lift() -> float:
    f = TRUTH["funnel"]

    def end_to_end(arm: str) -> float:
        return (
            f["viewed_sel_to_selected"][arm]
            * f["selected_to_confirmed"][arm]
            * f["confirmed_to_submitted"][arm]
        )

    return end_to_end("variant") - end_to_end("control")


def test_primary_lift_recovers_ground_truth():
    df = _query("select variant, conversion_rate from mart_primary_metric").set_index("variant")
    observed = float(df.loc["B", "conversion_rate"] - df.loc["A", "conversion_rate"])
    expected = _ground_truth_lift()
    assert abs(observed - expected) < 0.015, (
        f"observed lift {observed:.4f} vs injected {expected:.4f} -- outside tolerance"
    )


def test_variant_b_is_significantly_better_on_primary():
    df = _query("select variant, conversion_rate from mart_primary_metric").set_index("variant")
    assert df.loc["B", "conversion_rate"] > df.loc["A", "conversion_rate"]


def test_guardrail_tension_is_present():
    df = _query("select variant, fund_switch_regret_rate from mart_guardrails").set_index("variant")
    assert df.loc["B", "fund_switch_regret_rate"] > df.loc["A", "fund_switch_regret_rate"], (
        "the whole narrative depends on B having WORSE regret; the simulator regressed"
    )


def test_assignment_is_not_sample_ratio_mismatched():
    df = _query("select variant, count(*) n from mart_experiment_users group by variant")
    totals = df["n"].sum()
    for _, row in df.iterrows():
        assert abs(row["n"] / totals - 0.5) < 0.02
