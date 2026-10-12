{{ config(materialized='table') }}

-- Step-level funnel counts per arm, for the funnel chart. Denominator is all
-- assigned users (so the landing-page drop-off is visible).
with steps as (
    select 'viewed_kiwisaver_landing' as step_name, 0 as step_order
    union all select 'started_questionnaire', 1
    union all select 'completed_questionnaire', 2
    union all select 'viewed_fund_selection', 3
    union all select 'selected_base_fund', 4
    union all select 'confirmed_plan', 5
    union all select 'submitted_application', 6
),

reached as (
    select variant, event_name as step_name, count(distinct user_id) as users
    from {{ ref('stg_events') }}
    where event_name in (select step_name from steps)
    group by variant, event_name
),

assigned as (
    select variant, count(*) as assigned_users from {{ ref('stg_users') }} group by variant
)

select
    s.step_order,
    s.step_name,
    r.variant,
    r.users,
    a.assigned_users,
    r.users * 1.0 / a.assigned_users as pct_of_assigned
from steps s
join reached r using (step_name)
join assigned a using (variant)
order by s.step_order, r.variant
