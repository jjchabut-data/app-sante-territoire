-- int_apl_2023_dentistes.sql
with source as (
    select
        code_commune,
        apl_dentistes
    from {{ ref('stg_apl_dentistes_2023') }}
),

with_quintiles as (
    select
        code_commune,

        apl_dentistes,
        ntile(5) over (order by apl_dentistes)  as quintile_dentistes,
        case ntile(5) over (order by apl_dentistes)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_dentistes,
        -- z = (x - moyenne) / écart-type
        (apl_dentistes - avg(apl_dentistes) over ()) 
        / nullif(stddev(apl_dentistes) over (), 0) as apl_dentistes_std

    from source
)

select * from with_quintiles