# The KiwiSaver A/B Test — in plain English

A no-jargon guide for anyone (including me, when I started) who needs to
understand or *explain* this project. Part 1 is the pitch; Parts 2–8 explain the
ideas; Part 9 gives you scripts you can say out loud; Part 10 is a glossary.

---

## Part 1 — The 60-second story

KiwiSaver is New Zealand's retirement savings scheme — but people sign up to it
once and mostly forget it, so **getting someone to join is the hard part**. On
Sharesies' app, people browse the available funds, get overwhelmed by 11 options
and piles of disclosure documents, and **give up before they finish**.

We had an idea: what if, instead of making people wade through the fund list, we
asked them **three simple questions** about how they feel about risk and then
just **recommended a fund**? One click to confirm.

To find out if that actually helps, we ran an experiment: half the people saw the
normal fund list, half saw the quiz. We then measured how many finished signing up.

**The quiz won — and that's the easy part.** It lifted sign-ups by about **3
percentage points** (from ~40% to ~43%), and we're ~99.99% sure it's genuinely
better, not luck. But it also had a side effect: people were **twice as likely to
later change their mind** about the fund. So the recommendation isn't "ship it
everywhere" — it's "roll it out slowly, to a quarter of people, add a small
reassurance step, and watch." That's the difference between reading a number and
making a decision.

---

## Part 2 — The business question

Every business has a "leaky bucket": lots of people start a journey, few finish.
Here, the leak is at the fund-picking step. The question wasn't "is our app
nice?" — it was **"if we change this one screen, do more people sign up, and is
the change worth any side effects?"**

> **Analogy.** Imagine a café where customers must pick from a 3-page tea menu
> with tasting notes. Some love it; most freeze and leave. You try a board that
> says *"Not sure? Answer 2 questions and we'll pour you the right tea."* Does
> the line move faster? That's the experiment.

## Part 3 — What is an A/B test?

An A/B test is just **two versions of the same thing, shown to two groups at
random**, so any difference in the outcome can be blamed on the change — not on
the people being different.

- **Group A (Control):** the original experience. The "before".
- **Group B (Variant):** the new idea. The "what if".
- **Random** is the magic. We flip a coin per user. Because the *only* thing that
  differs between the groups is the coin, we can trust that any gap in results is
  caused by the change.
- **Primary metric:** the one number we're trying to move — here, *did they finish
  signing up within 7 days?*

**Why randomise?** If we just gave the quiz to whoever wanted it, the keen people
would pick it, and we'd learn nothing — we'd be measuring *enthusiasm*, not the
quiz. Randomness makes the two groups the same on average.

## Part 4 — What is "Bayesian" and why did we use it?

There are two main ways to analyse an experiment.

**The classic way (frequentist).** Ask *"if there were truly no difference, how
surprising is what we saw?"* That gives you a **p-value**. It answers a slightly
backwards question: "how weird is this data *assuming nothing is happening*?"

**The Bayesian way.** Start with a belief, then **update it as evidence arrives**.
That gives you a **posterior** — a full, honest picture of what's probably true
right now.

> **Analogy.** You meet a stranger. Before they speak, you assume they're about
> average height (your **prior**). Then they stand next to the doorframe and are
> clearly tall — you update your belief (**posterior**). Bayesian inference is just
> *doing that arithmetic formally with numbers instead of strangers*.

The reason we used it here is the reason a business cares: the decision-maker's
real questions are **"How likely is B actually better?"** and **"What does it cost
me if I'm wrong?"** The classic p-value doesn't answer those directly. The
Bayesian approach does — which is why this project leads with it and uses the
classic test only as a sanity check.

**A few Bayesian words, decoded:**

| Word | Plain meaning |
|---|---|
| **Prior** | What we believed before seeing the data (e.g. "conversion is probably around 40%") |
| **Likelihood** | How well the data fits a given possibility |
| **Posterior** | Our updated belief after seeing the data — the answer |
| **Credible interval** | The range that most likely contains the true value (e.g. "+1.7 to +4.4pp") |

We deliberately used a **weak prior** (a gentle guess, not a strong opinion), then
re-ran it with an even weaker one to show the conclusion doesn't depend on that
choice. That's a way of saying: *"I'm not cooking the books with my assumptions."*

## Part 5 — The key numbers, in one sentence each

| Number | What it says |
|---|---|
| **Conversion 39.5% → 42.6%** | Out of everyone who reached the fund screen, ~40% used to finish; now ~43% do |
| **+3.0pp ("percentage points")** | The difference is 3 points, not "3%". 3pp on a ~40% base is roughly a **7.6% relative** improvement |
| **95% credible interval +1.7 to +4.4pp** | The true improvement is very likely in this range — i.e. almost certainly positive |
| **P(B > A) = 99.99%** | If these two versions fought it out, B wins ~every time. Near-certain, not "maybe" |
| **Expected loss ≈ 0.00pp** | If we pick B and we're wrong, on average we lose essentially nothing. This is the "cost of being wrong" |
| **Guardrails** | The safety checks. A "win" that quietly hurts people isn't a win |
| **SRM check** | A tripwire that fails if the 50/50 split is broken — proof the experiment itself was healthy |

## Part 6 — How to read each chart

- **Prior vs posterior** — three humps. The flat dashed one is our starting guess.
  The two tall coloured ones are the two versions after evidence. **The further
  apart the two tall humps, the more confident we are they differ.** They barely
  overlap here → strong result.
- **Cumulative conversion** — two lines rising over 7 days. The gap between them
  *persists* — it isn't a day-one adrenaline spike that fades, which would be a
  red flag ("novelty effect").
- **Guardrails** — three pairs of bars. Two go **up** (bad: abandonment, regret),
  one goes **down** (good: better fund fit). This chart is *why* we pause.
- **Cohorts** — the same result cut by who the customer is. It shows *where* the
  win lives (new savers, higher-growth profiles) and who carries the regret risk.

## Part 7 — The twist (the bit that matters)

The quiz is a near-certain win on the headline number. So why not celebrate?

Because it also made people **twice as likely to switch their fund within two
weeks** afterwards. Counter-intuitively, the quiz actually made people pick a fund
that *fits their stated risk profile better* — so the regret isn't from a bad
recommendation. The best explanation is **speed**: the quiz removes friction, so
people commit *before they've fully thought it through*, then second-guess.

> **The lesson:** if we'd only looked at "did sign-ups go up?", we'd have shipped
> it and never noticed. Looking at the *side effects* is what separates an analyst
> from a number-reporting machine.

## Part 8 — The recommendation

**Roll it out to 25% of people, add a small reassurance at the confirmation step,
then re-check before going wider.** Roughly +15,700 members a year and ~$8M in
5-year value at full rollout — but a full instant rollout would lock in that trust
cost, so we stage it. The dashboard's risk slider lets a stakeholder say "I'll
accept this much risk" and watch the recommendation change live.

## Part 9 — Scripts you can say out loud

**30 seconds:** *"We tested replacing the confusing fund list with a 3-question
quiz that recommends a fund. Sign-ups rose ~3 points, and we're ~99.99% sure it's
real. But it doubled the rate of people changing their fund later, so I
recommended a staged rollout with a reassurance step, not a full launch."*

**When asked "what's a credible interval?"** *"It's the range that probably
contains the true number. Ours is +1.7 to +4.4 points — so even the low end is a
win."*

**When asked "why not just use a p-value?"** *"A p-value tests the data; the
business needs to make a decision. I want P(B beats A) and the cost of being
wrong, which is what the Bayesian framing gives."*

**When asked "is the +3 points good?"** *"Good, but the *decision* hinges on the
guardrails, not the headline. That's where a senior read differs from a junior
one."*

**When asked "why synthetic data?"** *"So I can prove the method works — I injected
a known effect and show the pipeline recovers it. Public datasets can't give you
ground truth."*

## Part 10 — Glossary

- **A/B test** — two versions shown to two randomly-chosen groups.
- **Control / Variant** — the "before" / the "new idea".
- **Conversion** — the success event we're counting (finishing sign-up).
- **Primary vs guardrail metric** — the goal vs the safety checks.
- **Lift** — the improvement. *Absolute* lift is in percentage points (+3.0pp);
  *relative* lift is the proportion (+7.6%).
- **pp (percentage points)** — the gap between two percentages; different from "%".
- **Prior / Posterior** — belief before / after the evidence.
- **Credible interval** — Bayesian "range that probably contains the truth".
- **P(B > A)** — probability the variant truly beats the control.
- **Expected loss** — average downside if you pick the wrong option.
- **SRM** — sample-ratio mismatch; a tripwire for a broken randomiser.
- **Power / MDE** — whether the test was big enough to detect a meaningful change.
- **Novelty effect** — an early fake-positive that fades; checked for and absent.
- **CUPED** — a variance-reduction trick to detect effects sooner (a next step).

## Part 11 — How to avoid sounding junior

1. **Lead with the decision, not the statistics.** Open with the recommendation.
2. **Say "percentage points", not "%".** It signals you know the difference.
3. **Bring up the guardrails yourself.** Don't wait to be asked.
4. **Say what you'd do next** (reassurance test, CUPED, sequential testing).
5. **Own the limitations first** (synthetic data, single-node, NZ-only). Naming
   them before the interviewer does reads as confidence, not weakness.

---

See also [`assumptions.md`](assumptions.md) (every assumption, sourced) and
[`README.md`](README.md) (the technical write-up).
