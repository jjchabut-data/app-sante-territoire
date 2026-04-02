-- sante/marts/mart_apl_historique.sql
-- Historique APL par commune (2017, 2019, 2022, 2023) enrichi du contexte géographique
with historique as (
    select
        code_commune,
        annee,
        apl_medecins,
        apl_infirmiers,
        apl_kines,
        apl_sagefemmes,
        pop_std_med,
        pop_std_infirmier,
        pop_std_kine,
        pop_std_sagefemme
    from {{ ref('int_apl_historique') }}
),

population as (
    select
        code_commune,
        annee,
        population
    from {{ ref('int_hist_pop_comm_cog') }}
),

communes as (
    select
        code            as code_commune,
        nom             as nom_commune,
        codes_epci,
        code_departement,
        code_region,
        longitude,
        latitude
    from {{ ref('mart_ref_comm_plus_arrond') }}
),

final as (
    select
        c.code_commune,
        c.nom_commune,
        c.codes_epci,
        c.code_departement,
        c.code_region,
        c.longitude,
        c.latitude,
        h.annee,
        h.apl_medecins,
        h.apl_infirmiers,
        h.apl_kines,
        h.apl_sagefemmes,
        h.pop_std_med,
        h.pop_std_infirmier,
        h.pop_std_kine,
        h.pop_std_sagefemme,
        p.population
    from communes c
    left join historique h on c.code_commune = h.code_commune
    left join population p on c.code_commune = p.code_commune
                           and h.annee = p.annee
)

select * from final