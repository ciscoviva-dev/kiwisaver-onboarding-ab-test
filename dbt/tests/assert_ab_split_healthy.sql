-- Sample-Ratio-Mismatch (SRM) guard: fails if either arm deviates from a 50/50
-- split by more than 2 percentage points, or if the Pearson chi-square test
-- indicates significant mismatch (p < 0.001, critical value 10.828 for 1 df).
with counts as (
    select variant, count(*) as n
    from {{ ref('stg_users') }}
    group by variant
),

totals as (
    select sum(n) as total from counts
),

stats as (
    select
        c.variant,
        c.n,
        t.total,
        abs(c.n * 1.0 / t.total - 0.5) as deviation_from_even,
        power(c.n - (t.total * 0.5), 2) / (t.total * 0.5) as chi2_component
    from counts c
    cross join totals t
)

select
    variant,
    n,
    total,
    deviation_from_even,
    chi2_component
from stats
where deviation_from_even > 0.02 or chi2_component > 5.414
