-- int_apl_sagefemmes_2023.sql
with source as (
    select
        code_commune,
        apl            as apl_sagefemmes,
        population_std as pop_std_sagefemme
    from {{ ref('stg_apl_sagesfemmes_2023') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_sagefemmes,
        s.pop_std_sagefemme
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_sagefemmes * pop_std_sagefemme) / nullif(sum(pop_std_sagefemme), 0) as apl_sagefemmes,
        sum(pop_std_sagefemme) as pop_std_sagefemme
    from fusioned
    group by code_commune_2026
),

with_quintiles as (
    select
        code_commune,

        pop_std_sagefemme,

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
        / nullif(stddev(apl_sagefemmes) over (), 0) as apl_sagefemmes_std

    from agregated
)

select * from with_quintiles
