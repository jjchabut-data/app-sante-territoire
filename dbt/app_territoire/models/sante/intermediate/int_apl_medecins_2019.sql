-- int_apl_medecins_2019.sql
-- NB: les brackets d'âge (apl_65/62/60) ne sont pas disponibles pour 2019
with source as (
    select
        code_commune,
        apl            as apl_medecins,
        population_std as pop_std_med
    from {{ ref('stg_apl_medecins_2019') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_medecins,
        s.pop_std_med
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_medecins * pop_std_med) / nullif(sum(pop_std_med), 0) as apl_medecins,
        sum(pop_std_med) as pop_std_med
    from fusioned
    group by code_commune_2026
),

with_quintiles as (
    select
        code_commune,

        pop_std_med,

        apl_medecins,
        ntile(5) over (order by apl_medecins)   as quintile_medecins,
        case ntile(5) over (order by apl_medecins)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_medecins,

        (apl_medecins - avg(apl_medecins) over ())
        / nullif(stddev(apl_medecins) over (), 0) as apl_medecins_std

    from agregated
)

select * from with_quintiles
