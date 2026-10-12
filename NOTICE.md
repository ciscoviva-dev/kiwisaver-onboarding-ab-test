# Notice & attribution

This is a **personal portfolio project**. It is **not affiliated with, endorsed
by, or produced for Sharesies**. It contains **no real customer data** — every
row in `data/raw/` is produced by the committed simulator (`src/simulate.py`)
from the parameters in `ground_truth.yaml`.

The domain — the onboarding flow, the base-fund names, and the fee schedule —
is modelled on **publicly available** information so that the analysis is
faithful to the real product. Those facts are reproduced here for
illustration only and remain the property of their owners.

## Public sources (accessed 2026-10-13)

| Fact used | Source |
|---|---|
| Join flow (questionnaire → investment plan → submit; ~10-day transfer, ~5-day new) | https://www.sharesies.nz/kiwisaver |
| 11 base funds and their risk bands | https://www.sharesies.nz/kiwisaver/base-funds |
| Base-fund annual charges, self-select 0.15% admin + 1%/0.1% transaction, 0.50% FX | https://www.sharesies.nz/pricing?tab=kiwisaver |
| Contribution rates, govt contribution, 62-day cooling-off | https://www.sharesies.nz/learn/behind-the-scenes-sharesies-kiwisaver-scheme |

Fees and contribution rules change over time. Anything below reflects the
sources **as of October 2026** and is used only to parameterise a simulation.

## Non-affiliation of all numbers

Conversion rates, uplift, guardrail rates, balances, and revenue are
**simulated assumptions**, not Sharesies figures. See `assumptions.md`.
