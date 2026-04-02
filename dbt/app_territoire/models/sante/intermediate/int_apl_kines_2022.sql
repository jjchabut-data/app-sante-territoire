-- int_apl_kines_2022.sql
with source as (
    select
        code_commune,
        apl            as apl_kines,
        population_std as pop_std_kine
    from {{ ref('stg_apl_kines_2022') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_kines,
        s.pop_std_kine
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_kines * pop_std_kine) / nullif(sum(pop_std_kine), 0) as apl_kines,
        sum(pop_std_kine) as pop_std_kine
    from fusioned
    group by code_commune_2026
),

with_quintiles as (
    select
        code_commune,

        pop_std_kine,

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
        / nullif(stddev(apl_kines) over (), 0) as apl_kines_std

    from agregated
)

select * from with_quintiles
