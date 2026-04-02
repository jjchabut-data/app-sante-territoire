-- int_hist_pop_comm_cog.sql
-- Population municipale historique par commune sur COG 2026
-- Jointure table de passage + agrégation pour communes fusionnées
-- Source : stg_pop_communale_historique + int_ref_table_passage_current

with source as (
    select * from {{ ref('stg_pop_commune_historique') }}
),

passage as (
    select code_ini, code_current
    from {{ ref('int_ref_table_passage_current') }}
),

fusion as (
    select
        coalesce(p.code_current, s.code_commune) as code_commune,
        s.annee,
        s.population
    from source s
    left join passage p on s.code_commune = p.code_ini
),

agregation as (
    select
        code_commune,
        annee,
        sum(population) as population
    from fusion
    group by code_commune, annee
)

select * from agregation