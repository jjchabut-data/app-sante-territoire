-- int_apl_infirmiers_2023.sql
with source as (
    select
        code_commune,
        apl            as apl_infirmiers,
        population_std as pop_std_infirmier
    from {{ ref('stg_apl_infirmiers_2023') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_infirmiers,
        s.pop_std_infirmier
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_infirmiers * pop_std_infirmier) / nullif(sum(pop_std_infirmier), 0) as apl_infirmiers,
        sum(pop_std_infirmier) as pop_std_infirmier
    from fusioned
    group by code_commune_2026
),

with_quintiles as (
    select
        code_commune,

        pop_std_infirmier,

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
        / nullif(stddev(apl_infirmiers) over (), 0) as apl_infirmiers_std

    from agregated
)

select * from with_quintiles
