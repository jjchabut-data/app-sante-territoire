-- referentiel/intermediate/int_ref_epci.sql
with epcis as (
    select
        code_epci as code,
        nom_epci as nom,
        type_epci as type,
        codes_communes_membres,
        codes_departements_membres,
        longitude,
        latitude
    from {{ ref('stg_ref_epci') }}
)

select * from epcis