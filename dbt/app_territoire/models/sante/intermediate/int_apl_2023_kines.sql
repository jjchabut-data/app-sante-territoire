-- int_apl_2023_kines.sql
with source as (
    select
        code_commune,
        apl_kines
    from {{ ref('stg_apl_kines_2023') }}
),

with_quintiles as (
    select
        code_commune,

        apl_kines,
        ntile(5) over (order by apl_kines)  as quintile_kines,
        case ntile(5) over (order by apl_kines)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                  as quintile_label_kines,

        (apl_kines - avg(apl_kines) over ()) 
        / nullif(stddev(apl_kines) over (), 0) as apl_kines_std,

    from source
)

select * from with_quintiles