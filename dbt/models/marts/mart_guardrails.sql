{{ config(materialized='table') }}

-- Guardrail metrics per arm. These are the numbers that make the decision
-- non-trivial: B converts more, but is it worth the risk cost?
select
    variant,

    -- (1a) post-selection abandonment (denom: reached fund selection)
    avg(case when reached_selection
             then case when abandoned_after_selection then 1.0 else 0.0 end end) as post_selection_abandonment_reached_rate,

    -- (1b) post-selection abandonment (denom: actually selected a fund)
    avg(case when selected_fund_risk is not null
             then case when abandoned_after_selection then 1.0 else 0.0 end end) as post_selection_abandonment_selector_rate,

    -- Backwards-compatible alias
    avg(case when reached_selection
             then case when abandoned_after_selection then 1.0 else 0.0 end end) as post_selection_abandonment_rate,

    -- (2) 14-day fund-switch regret, among converters
    avg(case when converted
             then case when switched_fund_14d then 1.0 else 0.0 end end)         as fund_switch_regret_rate,

    -- (3) mechanistic proxy: share of selectors whose fund mismatches their risk profile
    avg(case when selected_fund_risk is not null
             then case when coalesce(fund_profile_match, false) then 0.0 else 1.0 end end) as fund_profile_mismatch_rate,

    -- Denominator & numerator counts for uncertainty / Bayesian credible intervals
    count(*) filter (where reached_selection)                                    as reached_selection_users,
    count(*) filter (where selected_fund_risk is not null)                       as selector_users,
    count(*) filter (where converted)                                            as converted_users,
    count(*) filter (where abandoned_after_selection)                            as abandoned_users,
    count(*) filter (where converted and switched_fund_14d)                       as switched_users,
    count(*) filter (where selected_fund_risk is not null and not coalesce(fund_profile_match, false)) as mismatched_users
from {{ ref('mart_experiment_users') }}
group by variant
