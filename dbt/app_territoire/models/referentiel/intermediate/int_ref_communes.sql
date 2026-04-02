-- referentiel/intermediate/int_ref_communes.sql
with communes as (
    select
        code_commune as code,
        nom_commune as nom,
        population,
        code_departement,
        code_region,
        codes_epci,
        longitude,
        latitude
    from {{ ref('stg_ref_communes') }}
)

select * from communes