{{ config(materialized='table') }}

-- Guardrail metrics per arm. These are the numbers that make the decision
-- non-trivial: B converts more, but is it worth the risk cost?
select
    variant,

    -- (1) post-selection abandonment: reached fund selection but never confirmed
    avg(case when reached_selection
             then case when abandoned_after_selection then 1.0 else 0.0 end end) as post_selection_abandonment_rate,

    -- (2) 14-day fund-switch regret, among converters
    avg(case when converted
             then case when switched_fund_14d then 1.0 else 0.0 end end)         as fund_switch_regret_rate,

    -- (3) mechanistic proxy: share of selectors whose fund mismatches their risk profile
    avg(case when selected_fund_risk is not null
             then case when coalesce(fund_profile_match, false) then 0.0 else 1.0 end end) as fund_profile_mismatch_rate
from {{ ref('mart_experiment_users') }}
group by variant
