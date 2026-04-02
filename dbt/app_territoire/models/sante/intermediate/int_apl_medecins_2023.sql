-- int_apl_medecins_2023.sql
with source as (
    select
        code_commune,
        apl          as apl_medecins,
        apl_65       as apl_med_65,
        apl_62       as apl_med_62,
        apl_60       as apl_med_60,
        population_std as pop_std_med
    from {{ ref('stg_apl_medecins_2023') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusioned as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_medecins,
        s.apl_med_65,
        s.apl_med_62,
        s.apl_med_60,
        s.pop_std_med
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregated as (
    select
        code_commune_2026 as code_commune,
        sum(apl_medecins * pop_std_med) / nullif(sum(pop_std_med), 0) as apl_medecins,
        sum(apl_med_65   * pop_std_med) / nullif(sum(pop_std_med), 0) as apl_med_65,
        sum(apl_med_62   * pop_std_med) / nullif(sum(pop_std_med), 0) as apl_med_62,
        sum(apl_med_60   * pop_std_med) / nullif(sum(pop_std_med), 0) as apl_med_60,
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

        apl_med_65,
        ntile(5) over (order by apl_med_65)     as quintile_med_65,
        case ntile(5) over (order by apl_med_65)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_65,

        apl_med_62,
        ntile(5) over (order by apl_med_62)     as quintile_med_62,
        case ntile(5) over (order by apl_med_62)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_62,

        apl_med_60,
        ntile(5) over (order by apl_med_60)     as quintile_med_60,
        case ntile(5) over (order by apl_med_60)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_60,

        (apl_medecins - avg(apl_medecins) over ())
        / nullif(stddev(apl_medecins) over (), 0) as apl_medecins_std,

        (apl_med_65 - avg(apl_med_65) over ())
        / nullif(stddev(apl_med_65) over (), 0) as apl_med_65_std,

        (apl_med_62 - avg(apl_med_62) over ())
        / nullif(stddev(apl_med_62) over (), 0) as apl_med_62_std,

        (apl_med_60 - avg(apl_med_60) over ())
        / nullif(stddev(apl_med_60) over (), 0) as apl_med_60_std,

        -- structure de l'offre par tranche d'âge
        apl_medecins - apl_med_65                        as offre_med_65_plus,
        apl_med_65   - apl_med_62                        as offre_med_63_64,
        apl_med_62   - apl_med_60                        as offre_med_61_62,
        apl_med_60                                       as offre_med_perenite,

        -- taux de pérennité
        apl_med_60 / nullif(apl_medecins, 0)             as taux_perenite_offre,

        -- quintile et label taux de pérennité
        ntile(5) over (order by apl_med_60 / nullif(apl_medecins, 0)) 
                                                         as quintile_perenite_offre,
        case ntile(5) over (order by apl_med_60 / nullif(apl_medecins, 0))
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                              as quintile_label_perenite_offre

    from agregated
)

select * from with_quintiles
