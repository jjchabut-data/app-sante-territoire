-- referentiel/marts/mart_meta_sources.sql
-- Millésime actuellement servi par l'app pour chaque source de données,
-- dérivé directement des vars dbt_project.yml — jamais à mettre à jour à
-- la main : ce mart reflète toujours la combinaison réellement en place.
-- Consommé par la page Streamlit "Sources & millésimes" (src/pages/).
select
    {{ var('annee_apl') }}                as millesime_apl,
    {{ var('annee_COG') }}                as millesime_geo,
    '{{ var('version_densite') }}'        as millesime_densite,
    {{ var('annee_pop_selon_age') }}      as millesime_pop_age,
    {{ var('annee_vieillissement') }}     as millesime_vieillissement,
    {{ var('annee_taux_mortalite') }}     as millesime_mortalite,
    {{ var('annee_esperance_vie') }}      as millesime_esperance_vie,
    {{ var('annee_tps_acces_urgences') }} as millesime_urgences
