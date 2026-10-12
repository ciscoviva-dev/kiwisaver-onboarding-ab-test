{{ config(materialized='table') }}

-- Primary metric: conversion within the window, among users who reached the
-- fund-selection step (a fair, shared starting line for both arms).
select
    variant,
    count(*)                                                          as reached_selection_users,
    sum(case when converted_in_window then 1 else 0 end)              as converted_users,
    avg(case when converted_in_window then 1.0 else 0.0 end)          as conversion_rate
from {{ ref('mart_experiment_users') }}
where reached_selection
group by variant
