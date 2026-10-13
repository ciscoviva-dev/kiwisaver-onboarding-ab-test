{{ config(materialized='table') }}

-- One row per user: where they got to in the funnel, when, and the outcome.
with e as (
    select * from {{ ref('stg_events') }}
),

pivoted as (
    select
        user_id,
        experiment_id,
        variant,

        min(event_timestamp) filter (where event_name = 'viewed_kiwisaver_landing')  as landed_at,
        min(event_timestamp) filter (where event_name = 'viewed_fund_selection')     as viewed_selection_at,
        min(event_timestamp) filter (where event_name = 'selected_base_fund')        as selected_fund_at,
        min(event_timestamp) filter (where event_name = 'confirmed_plan')            as confirmed_plan_at,
        min(event_timestamp) filter (where event_name = 'submitted_application')     as submitted_at,
        min(event_timestamp) filter (where event_name = 'switched_base_fund')        as switched_fund_at,
        min(event_timestamp) filter (where event_name = 'transfer_balance_set')      as transfer_set_at,
        min(event_timestamp) filter (where event_name = 'contribution_setup_completed') as contribution_setup_at,

        min(transfer_balance_nzd) filter (where event_name = 'transfer_balance_set') as transfer_balance_nzd,
        max(selected_fund_risk)   filter (where event_name = 'selected_base_fund')   as selected_fund_risk,
        max(profile_risk)         filter (where event_name = 'selected_base_fund')   as profile_risk,
        max(case when fund_profile_match then 1 else 0 end) filter (where event_name = 'selected_base_fund') as fund_profile_match
    from e
    group by user_id, experiment_id, variant
)

select
    user_id,
    experiment_id,
    variant,
    landed_at,
    viewed_selection_at,
    selected_fund_at,
    confirmed_plan_at,
    submitted_at,
    switched_fund_at,
    transfer_set_at,
    contribution_setup_at,
    transfer_balance_nzd,
    selected_fund_risk,
    profile_risk,
    cast(fund_profile_match as boolean)                                 as fund_profile_match,
    -- reached the experiment's starting line (the primary-metric denominator)
    (viewed_selection_at is not null)                                   as reached_selection,
    (submitted_at is not null)                                          as converted,
    -- selected a fund but never confirmed (abandonment guardrail)
    (selected_fund_at is not null and confirmed_plan_at is null)        as abandoned_after_selection,
    -- switched base fund within the 14-day window (regret guardrail)
    (switched_fund_at is not null
        and submitted_at is not null
        and switched_fund_at >= submitted_at
        and switched_fund_at <= submitted_at + interval 14 days)        as switched_fund_14d,
    date_diff('day', viewed_selection_at, submitted_at)                 as days_to_convert,
    (submitted_at is not null
        and date_diff('day', viewed_selection_at, submitted_at)
            <= {{ var("conversion_window_days") }})                     as converted_in_window
from pivoted
