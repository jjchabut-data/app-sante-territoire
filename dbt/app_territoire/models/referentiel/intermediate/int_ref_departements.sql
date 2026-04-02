-- referentiel/intermediate/int_ref_departements.sql
with departements as (
    select
        code_departement as code,
        nom_departement as nom,
        longitude,
        latitude
    from {{ ref('stg_ref_departements') }}
)

select * from departements