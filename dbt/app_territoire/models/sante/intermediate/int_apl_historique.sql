-- int_apl_historique.sql
-- Historique APL par commune pour les 4 professions comparables (sans dentistes)
-- Millésimes : 2017, 2019, 2022, 2023 — COG harmonisé 2026

with passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

-- 2017 : staging en format long → pivot conditionnel + COG
source_2017 as (
    select
        code_commune,
        max(case when profession = 'medecin'    then apl            end) as apl_medecins,
        max(case when profession = 'medecin'    then population_std end) as pop_std_med,
        max(case when profession = 'infirmier'  then apl            end) as apl_infirmiers,
        max(case when profession = 'infirmier'  then population_std end) as pop_std_infirmier,
        max(case when profession = 'kine'       then apl            end) as apl_kines,
        max(case when profession = 'kine'       then population_std end) as pop_std_kine,
        max(case when profession = 'sage_femme' then apl            end) as apl_sagefemmes,
        max(case when profession = 'sage_femme' then population_std end) as pop_std_sagefemme
    from {{ ref('stg_apl_wide_2017') }}
    group by code_commune
),

fusioned_2017 as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune_2026,
        s.apl_medecins,    s.pop_std_med,
        s.apl_infirmiers,  s.pop_std_infirmier,
        s.apl_kines,       s.pop_std_kine,
        s.apl_sagefemmes,  s.pop_std_sagefemme
    from source_2017 s
    left join passage p on s.code_commune = p.code_ini
),

annee_2017 as (
    select
        code_commune_2026 as code_commune,
        2017              as annee,
        sum(apl_medecins   * pop_std_med)         / nullif(sum(pop_std_med),         0) as apl_medecins,
        sum(apl_infirmiers * pop_std_infirmier)   / nullif(sum(pop_std_infirmier),   0) as apl_infirmiers,
        sum(apl_kines      * pop_std_kine)        / nullif(sum(pop_std_kine),        0) as apl_kines,
        sum(apl_sagefemmes * pop_std_sagefemme)   / nullif(sum(pop_std_sagefemme),   0) as apl_sagefemmes,
        sum(pop_std_med)         as pop_std_med,
        sum(pop_std_infirmier)   as pop_std_infirmier,
        sum(pop_std_kine)        as pop_std_kine,
        sum(pop_std_sagefemme)   as pop_std_sagefemme
    from fusioned_2017
    group by code_commune_2026
),

-- 2019 : référence les intermédiaires avec COG déjà appliqué
annee_2019 as (
    select
        coalesce(m.code_commune, i.code_commune, k.code_commune, s.code_commune) as code_commune,
        2019 as annee,
        m.apl_medecins,
        i.apl_infirmiers,
        k.apl_kines,
        s.apl_sagefemmes,
        m.pop_std_med,
        i.pop_std_infirmier,
        k.pop_std_kine,
        s.pop_std_sagefemme
    from {{ ref('int_apl_medecins_2019') }}   m
    full outer join {{ ref('int_apl_infirmiers_2019') }}  i on m.code_commune = i.code_commune
    full outer join {{ ref('int_apl_kines_2019') }}       k on m.code_commune = k.code_commune
    full outer join {{ ref('int_apl_sagefemmes_2019') }}  s on m.code_commune = s.code_commune
),

-- 2022 : référence les intermédiaires avec COG déjà appliqué
annee_2022 as (
    select
        coalesce(m.code_commune, i.code_commune, k.code_commune, s.code_commune) as code_commune,
        2022 as annee,
        m.apl_medecins,
        i.apl_infirmiers,
        k.apl_kines,
        s.apl_sagefemmes,
        m.pop_std_med,
        i.pop_std_infirmier,
        k.pop_std_kine,
        s.pop_std_sagefemme
    from {{ ref('int_apl_medecins_2022') }}   m
    full outer join {{ ref('int_apl_infirmiers_2022') }}  i on m.code_commune = i.code_commune
    full outer join {{ ref('int_apl_kines_2022') }}       k on m.code_commune = k.code_commune
    full outer join {{ ref('int_apl_sagefemmes_2022') }}  s on m.code_commune = s.code_commune
),

-- 2023 : référence les intermédiaires avec COG déjà appliqué
annee_2023 as (
    select
        coalesce(m.code_commune, i.code_commune, k.code_commune, s.code_commune) as code_commune,
        2023 as annee,
        m.apl_medecins,
        i.apl_infirmiers,
        k.apl_kines,
        s.apl_sagefemmes,
        m.pop_std_med,
        i.pop_std_infirmier,
        k.pop_std_kine,
        s.pop_std_sagefemme
    from {{ ref('int_apl_medecins_2023') }}   m
    full outer join {{ ref('int_apl_infirmiers_2023') }}  i on m.code_commune = i.code_commune
    full outer join {{ ref('int_apl_kines_2023') }}       k on m.code_commune = k.code_commune
    full outer join {{ ref('int_apl_sagefemmes_2023') }}  s on m.code_commune = s.code_commune
)

select * from annee_2017
union all
select * from annee_2019
union all
select * from annee_2022
union all
select * from annee_2023
