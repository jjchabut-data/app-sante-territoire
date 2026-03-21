-- sante/marts/mart_apl_region.sql
with communes as (
    select
        code_region,
        population,
        apl_medecins,       apl_medecins_std,
        quintile_medecins,
        apl_med_65,         apl_med_65_std,
        apl_med_62,         apl_med_62_std,
        apl_med_60,         apl_med_60_std,
        apl_dentistes,      apl_dentistes_std,
        quintile_dentistes,
        apl_infirmiers,     apl_infirmiers_std,
        quintile_infirmiers,
        apl_kines,          apl_kines_std,
        quintile_kines,
        apl_sagefemmes,     apl_sagefemmes_std,
        quintile_sagefemmes,
        score_apl,          score_apl_std
    from {{ ref('mart_apl_commune') }}
    where code_region is not null
),

regions as (
    select code_region, nom_region
    from {{ ref('stg_regions') }}
),

aggregated as (
    select
        c.code_region,
        sum(c.population)                                                               as population_totale,
        count(*)                                                                        as nb_communes,

        -- Médecins
        sum(c.apl_medecins * c.population)      / nullif(sum(c.population), 0)         as apl_medecins,
        sum(c.apl_medecins_std * c.population)  / nullif(sum(c.population), 0)         as apl_medecins_std,
        sum(c.quintile_medecins * c.population) / nullif(sum(c.population), 0)         as indice_position_medecins,
        stddev(c.apl_medecins)                                                          as indice_heterogeneite_medecins,
        sum(c.apl_med_65 * c.population)        / nullif(sum(c.population), 0)         as apl_med_65,
        sum(c.apl_med_65_std * c.population)    / nullif(sum(c.population), 0)         as apl_med_65_std,
        sum(c.apl_med_62 * c.population)        / nullif(sum(c.population), 0)         as apl_med_62,
        sum(c.apl_med_62_std * c.population)    / nullif(sum(c.population), 0)         as apl_med_62_std,
        sum(c.apl_med_60 * c.population)        / nullif(sum(c.population), 0)         as apl_med_60,
        sum(c.apl_med_60_std * c.population)    / nullif(sum(c.population), 0)         as apl_med_60_std,

        -- Dentistes
        sum(c.apl_dentistes * c.population)      / nullif(sum(c.population), 0)        as apl_dentistes,
        sum(c.apl_dentistes_std * c.population)  / nullif(sum(c.population), 0)        as apl_dentistes_std,
        sum(c.quintile_dentistes * c.population) / nullif(sum(c.population), 0)        as indice_position_dentistes,
        stddev(c.apl_dentistes)                                                         as indice_heterogeneite_dentistes,

        -- Infirmiers
        sum(c.apl_infirmiers * c.population)      / nullif(sum(c.population), 0)       as apl_infirmiers,
        sum(c.apl_infirmiers_std * c.population)  / nullif(sum(c.population), 0)       as apl_infirmiers_std,
        sum(c.quintile_infirmiers * c.population) / nullif(sum(c.population), 0)       as indice_position_infirmiers,
        stddev(c.apl_infirmiers)                                                        as indice_heterogeneite_infirmiers,

        -- Kinés
        sum(c.apl_kines * c.population)      / nullif(sum(c.population), 0)            as apl_kines,
        sum(c.apl_kines_std * c.population)  / nullif(sum(c.population), 0)            as apl_kines_std,
        sum(c.quintile_kines * c.population) / nullif(sum(c.population), 0)            as indice_position_kines,
        stddev(c.apl_kines)                                                             as indice_heterogeneite_kines,

        -- Sages-femmes
        sum(c.apl_sagefemmes * c.population)      / nullif(sum(c.population), 0)       as apl_sagefemmes,
        sum(c.apl_sagefemmes_std * c.population)  / nullif(sum(c.population), 0)       as apl_sagefemmes_std,
        sum(c.quintile_sagefemmes * c.population) / nullif(sum(c.population), 0)       as indice_position_sagefemmes,
        stddev(c.apl_sagefemmes)                                                        as indice_heterogeneite_sagefemmes,

        -- Score synthétique
        sum(c.score_apl * c.population)     / nullif(sum(c.population), 0)             as score_apl,
        sum(c.score_apl_std * c.population) / nullif(sum(c.population), 0)             as score_apl_std,
        stddev(c.score_apl)                                                             as indice_heterogeneite_score

    from communes c
    group by c.code_region
),

final as (
    select
        a.code_region,
        r.nom_region,
        a.population_totale,
        a.nb_communes,
        a.apl_medecins,             a.apl_medecins_std,             a.indice_position_medecins,     a.indice_heterogeneite_medecins,
        a.apl_med_65,               a.apl_med_65_std,
        a.apl_med_62,               a.apl_med_62_std,
        a.apl_med_60,               a.apl_med_60_std,
        a.apl_dentistes,            a.apl_dentistes_std,            a.indice_position_dentistes,    a.indice_heterogeneite_dentistes,
        a.apl_infirmiers,           a.apl_infirmiers_std,           a.indice_position_infirmiers,   a.indice_heterogeneite_infirmiers,
        a.apl_kines,                a.apl_kines_std,                a.indice_position_kines,        a.indice_heterogeneite_kines,
        a.apl_sagefemmes,           a.apl_sagefemmes_std,           a.indice_position_sagefemmes,   a.indice_heterogeneite_sagefemmes,
        a.score_apl,                a.score_apl_std,                a.indice_heterogeneite_score
    from aggregated a
    left join regions r on a.code_region = r.code_region
)

select * from final