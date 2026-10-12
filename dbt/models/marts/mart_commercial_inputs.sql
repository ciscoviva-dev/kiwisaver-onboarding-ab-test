{{ config(materialized='table') }}

-- Inputs to the commercial model: transfer balance distribution and the
-- 30-day contribution-setup rate, measured among converters.
select
    variant,
    count(*)                                                          as converters,
    count(transfer_balance_nzd)                                       as converters_with_balance,
    avg(transfer_balance_nzd)                                         as mean_transfer_balance_nzd,
    median(transfer_balance_nzd)                                      as median_transfer_balance_nzd,
    avg(case when contribution_setup_30d then 1.0 else 0.0 end)       as contribution_setup_30d_rate
from {{ ref('mart_experiment_users') }}
where converted
group by variant
