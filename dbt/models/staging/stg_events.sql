{{ config(materialized='view') }}

-- Raw event stream (one row per UI event). Light typing + metadata unpacking.
with source as (
    select * from read_parquet('{{ var("raw_events") }}')
)

select
    event_id,
    user_id,
    session_id,
    cast(event_timestamp as timestamp)      as event_timestamp,
    event_name,
    experiment_id,
    variant,
    platform,
    acquisition_channel,
    app_version,
    metadata,
    -- unpack the JSON payload once, here, so downstream models stay clean
    try_cast(json_extract_string(metadata, '$.amount_nzd') as double)      as transfer_balance_nzd,
    json_extract_string(metadata, '$.fund_id')                            as selected_fund_id,
    json_extract_string(metadata, '$.fund_risk')                          as selected_fund_risk,
    json_extract_string(metadata, '$.profile_risk')                       as profile_risk,
    try_cast(json_extract_string(metadata, '$.match') as boolean)         as fund_profile_match
from source
