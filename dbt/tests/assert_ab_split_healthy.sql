-- Sample-Ratio-Mismatch (SRM) guard: fails if either arm deviates from a 50/50
-- split by more than 2 percentage points. Catches a broken randomiser before it
-- silently corrupts every downstream metric.
with counts as (
    select variant, count(*) as n
    from {{ ref('stg_users') }}
    group by variant
),

totals as (
    select sum(n) as total from counts
)

select
    c.variant,
    c.n,
    t.total,
    abs(c.n * 1.0 / t.total - 0.5) as deviation_from_even
from counts c
cross join totals t
where abs(c.n * 1.0 / t.total - 0.5) > 0.02
