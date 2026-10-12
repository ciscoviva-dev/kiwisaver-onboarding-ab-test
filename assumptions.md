# Assumptions

Everything the analysis depends on that is *not* derived from the data is listed
here, with its source or its justification. If a reviewer wants to argue with a
number, this is where the number comes from.

## 1. Domain facts (from public Sharesies pages, Oct 2026)

See `NOTICE.md` for URLs. These shape the simulation but are not "results".

| Fact | Value used |
|---|---|
| Onboarding steps | questionnaire -> investment plan (base fund, optional self-select) -> submit |
| Base funds | 11, across conservative / balanced / growth / high-growth risk bands |
| Time to transfer an existing KiwiSaver | ~10 business days |
| Time to set up a new KiwiSaver | ~5 business days |
| Cooling-off period | 62 days |

## 2. Simulated experiment parameters

All in `ground_truth.yaml`. The true end-to-end conversion lift (from
`viewed_fund_selection`) is:

```
A: 0.550 x 0.80 x 0.90 = 0.3960
B: 0.620 x 0.76 x 0.90 = 0.4241
=> injected absolute lift = +2.81pp
```

The headline in the README is the *recovered* number from the built marts, not
this constant.

## 3. Statistical choices

| Choice | Value | Why |
|---|---|---|
| Prior | Beta(4, 6), mean 0.40 | Weakly informative around a plausible baseline; prior-sensitivity run with Beta(1,1) is reported alongside |
| Credible level | 95% | Convention |
| Monte Carlo draws | 200,000 | Stable to <0.1pp on all reported quantities |
| Analysis seed | fixed | Reproducible decision outputs |

## 4. Commercial model

KiwiSaver revenue at Sharesies is a **provider margin**, not the gross fund
charge (fund providers pay Sharesies to be on the platform). Modelling the full
0.09%-1.49% annual charge as revenue would overstate it, so we model a blended
platform revenue rate.

| Assumption | Value | Justification |
|---|---|---|
| Platform revenue rate | 0.75% p.a. of AUM | Blended fund-provider margin + self-select admin fee (0.15%), bracketed by the real charge table |
| Expected AUM per converter | from data | `P(transfers a balance) x E[balance]` measured from `mart_commercial_inputs` |
| Annual retention | 92% | KiwiSaver is sticky/illiquid; deliberately conservative |
| Discount rate | 8% | Standard corporate hurdle |
| Balance growth | 6% p.a. | Member 3-4% + employer 3-4% contributions |
| Horizon | 5 years | Matches the "long-term wealth" framing |
| Experiment -> annual scale | x 365 / 14 | The 14-day window is a slice of steady-state traffic |

**What this model is not:** it ignores fees earned on *on-going* contributions
separately (folded into balance growth), and treats the incremental member as
average. It is a decision aid, not a revenue forecast.

## 5. Known limitations

- Synthetic data: effect sizes are *chosen*, so the analysis validates the
  *method*, not a real business effect.
- NZ only; the Australian market dimension is out of scope.
- Single-node DuckDB; no genuine seasonality, novelty, or interference effects.
- Guardrail power is lower than primary-metric power (guardrails are measured on
  smaller denominators).
