-- int_apl_dentistes_2023.sql
with source as (
    select
        code_commune,
        apl            as apl_dentistes,
        population_std as pop_std_dentiste
    from {{ ref('stg_apl_dentistes_2023') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,  -- résolution COG
        s.apl_dentistes,
        s.pop_std_dentiste
    from source s
    left join passage p on s.code_commune = p.code_ini
),
-- agrégation post-fusion pour les communes ayant fusionné, en pondérant par la population standardisée des dentistes
agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_dentistes * pop_std_dentiste) / nullif(sum(pop_std_dentiste), 0) as apl_dentistes,
        sum(pop_std_dentiste) as pop_std_dentiste
    from fusioned
    group by code_commune_2026
),

with_quintiles as (
    select
        code_commune,

        pop_std_dentiste,

        apl_dentistes,
        ntile(5) over (order by apl_dentistes)  as quintile_dentistes,
        case ntile(5) over (order by apl_dentistes)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_dentistes,

        (apl_dentistes - avg(apl_dentistes) over ())
        / nullif(stddev(apl_dentistes) over (), 0) as apl_dentistes_std

    from agregated
)

select * from with_quintiles
