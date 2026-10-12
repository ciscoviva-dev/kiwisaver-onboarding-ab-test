{{ config(materialized='view') }}

-- Assignment + user attributes (one row per user).
select
    user_id,
    experiment_id,
    variant,
    cast(assigned_at as timestamp) as assigned_at,
    market,
    is_existing_kiwisaver,
    device,
    channel,
    age_band,
    sex,
    income_band,
    fund_risk_profile,
    app_version
from read_parquet('{{ var("raw_users") }}')
