-- referentiel/intermediate/int_ref_arrond_municipaux.sql
with communes as (
    select
        code_arrondissement as code,
        nom_arrondissement as nom,
        population,
        numero_arrondissement,
        code_commune_rattachement,
        longitude,
        latitude
    from {{ ref('stg_ref_arrond_municipaux') }}
)

select * from communes