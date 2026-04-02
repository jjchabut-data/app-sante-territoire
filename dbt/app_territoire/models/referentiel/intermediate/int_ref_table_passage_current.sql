-- referentiel/intermediate/int_ref_table_passage_current.sql

with source as (
    select 
        code_commune_ini as code_ini,
        code_commune_2026 as code_current,
        nom_commune_2026 as nom_current
    from {{ ref('stg_ref_table_passage_' ~ var('annee_COG')) }}
)

select code_ini, code_current
from source