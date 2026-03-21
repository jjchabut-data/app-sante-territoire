-- int_apl_infirmiers.sql
with source as (
    select
        code_commune,
        apl_infirmiers
    from {{ ref('stg_apl_infirmiers_2023') }}
),

with_quintiles as (
    select
        code_commune,

        apl_infirmiers,
        ntile(5) over (order by apl_infirmiers)  as quintile_infirmiers,
        case ntile(5) over (order by apl_infirmiers)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                       as quintile_label_infirmiers,

        (apl_infirmiers - avg(apl_infirmiers) over ()) 
        / nullif(stddev(apl_infirmiers) over (), 0) as apl_infirmiers_std,

    from source
)

select * from with_quintiles