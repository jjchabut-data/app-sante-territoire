-- referentiel/marts/mart_ref_communes.sql
with communes as (
    select
        code,
        nom,
        population,
        code_departement,
        code_region,
        codes_epci,
        longitude,
        latitude
    from {{ ref('int_ref_communes') }}
)

select * from communes
