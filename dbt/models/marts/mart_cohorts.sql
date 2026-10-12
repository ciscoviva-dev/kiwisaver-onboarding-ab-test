{{ config(materialized='table') }}

-- Customer cohorts (JD: "develop customer profiles, cohorts and audiences").
-- Where does B's uplift concentrate? Long format so several segmentations can
-- share one mart.
with base as (
    select * from {{ ref('mart_experiment_users') }} where reached_selection
),

unioned as (
    select 'fund_risk_profile' as segment_type, fund_risk_profile as segment, variant, converted_in_window from base
    union all
    select 'is_existing_kiwisaver', case when is_existing_kiwisaver then 'existing' else 'new' end, variant, converted_in_window from base
    union all
    select 'device', device, variant, converted_in_window from base
    union all
    select 'age_band', age_band, variant, converted_in_window from base
)

select
    segment_type,
    segment,
    variant,
    count(*)                                                 as users,
    sum(case when converted_in_window then 1 else 0 end)     as converted,
    avg(case when converted_in_window then 1.0 else 0.0 end) as conversion_rate
from unioned
group by segment_type, segment, variant
order by segment_type, segment, variant
