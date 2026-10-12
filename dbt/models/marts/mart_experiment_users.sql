{{ config(materialized='table') }}

-- The analysis table. One row per assigned user, with the outcome flags and
-- the attributes needed for segmentation. This is the input to the Bayesian
-- model in src/analyze.py.
select
    f.user_id,
    f.experiment_id,
    f.variant,
    u.assigned_at,
    u.market,
    u.device,
    u.channel,
    u.age_band,
    u.sex,
    u.income_band,
    u.fund_risk_profile,
    u.is_existing_kiwisaver,

    f.reached_selection,
    f.converted,
    f.converted_in_window,
    f.days_to_convert,
    f.abandoned_after_selection,
    f.switched_fund_14d,
    f.selected_fund_risk,
    cast(f.fund_profile_match as boolean) as fund_profile_match,
    f.transfer_balance_nzd,
    (f.contribution_setup_at is not null) as contribution_setup_30d
from {{ ref('int_funnel') }} f
join {{ ref('stg_users') }} u using (user_id)
