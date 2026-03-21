-- int_apl_sagefemmes.sql
with source as (
    select
        code_commune,
        apl_sagefemmes
    from {{ ref('stg_apl_sagesfemmes_2023') }}
),

with_quintiles as (
    select
        code_commune,

        apl_sagefemmes,
        ntile(5) over (order by apl_sagefemmes)  as quintile_sagefemmes,
        case ntile(5) over (order by apl_sagefemmes)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                       as quintile_label_sagefemmes,

        (apl_sagefemmes - avg(apl_sagefemmes) over ()) 
        / nullif(stddev(apl_sagefemmes) over (), 0) as apl_sagefemmes_std,

    from source
)

select * from with_quintiles