"""Unit tests for statistical analysis module (src/analyze.py)."""

from __future__ import annotations

import numpy as np

from src.analyze import (
    beta_posterior,
    decision_outputs,
    frequentist_crosscheck,
    npv5,
    summarize_arm,
)


def test_beta_posterior_conjugate_update():
    y, n = 40, 100
    a0, b0 = 4.0, 6.0
    a_post, b_post = beta_posterior(y, n, a0, b0)
    assert a_post == 44.0
    assert b_post == 66.0


def test_summarize_arm_credible_interval():
    rng = np.random.default_rng(123)
    res = summarize_arm(400, 1000, rng, 4.0, 6.0)
    assert res["n"] == 1000
    assert res["converted"] == 400
    assert abs(res["rate"] - 0.4) < 1e-6
    lo, hi = res["credible_interval"]
    assert lo < res["posterior_mean"] < hi
    assert 0.36 < lo < 0.40
    assert 0.40 < hi < 0.44


def test_decision_outputs_identical_arms():
    rng = np.random.default_rng(123)
    draws_a = rng.beta(40, 60, 50000)
    draws_b = draws_a.copy()
    dec = decision_outputs(draws_a, draws_b, 0.40)
    assert dec["prob_b_beats_a"] == 0.0
    assert abs(dec["abs_lift_mean"]) < 1e-9
    assert dec["expected_loss_choosing_b"] == 0.0
    assert dec["expected_loss_choosing_a"] == 0.0


def test_decision_outputs_superior_arm():
    rng = np.random.default_rng(123)
    draws_a = rng.beta(300, 700, 50000)
    draws_b = rng.beta(600, 400, 50000)
    dec = decision_outputs(draws_a, draws_b, 0.30)
    assert dec["prob_b_beats_a"] == 1.0
    assert dec["expected_loss_choosing_b"] == 0.0
    assert dec["expected_loss_choosing_a"] > 0.25
    assert dec["abs_lift_mean"] > 0.25


def test_frequentist_crosscheck_standard_values():
    y_a, n_a = 400, 1000
    y_b, n_b = 450, 1000
    res = frequentist_crosscheck(y_a, n_a, y_b, n_b)
    assert abs(res["abs_lift"] - 0.05) < 1e-6
    # pooled p = 0.425, se = sqrt(0.425 * 0.575 * 2 / 1000) ~= 0.0221077
    # z ~= 0.05 / 0.0221077 ~= 2.26
    assert 2.2 < res["z"] < 2.3
    assert res["p_value"] < 0.05
    lo, hi = res["ci95"]
    assert lo < 0.05 < hi


def test_npv5_monotonic_scaling():
    rev1 = 100.0
    rev2 = 200.0
    val1 = npv5(rev1)
    val2 = npv5(rev2)
    assert abs(val2 - 2 * val1) < 1e-6
    assert val1 > rev1  # 5-year discounted sum exceeds 1-year revenue
