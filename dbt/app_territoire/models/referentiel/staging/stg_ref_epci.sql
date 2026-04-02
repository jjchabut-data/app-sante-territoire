-- referentiel/staging/stg_ref_epci.sql
with source as (
    select * from {{ source('raw', 'ref_epci_geom_2026') }}
),

renamed as (
    select
        code_siren                          as code_epci,
        nom_officiel                        as nom_epci,
        nature                              as type_epci,
        codes_insee_des_communes_membres    as codes_communes_membres,
        codes_insee_des_departements_membres as codes_departements_membres,
        lon                             as longitude,
        lat                             as latitude,
        geometry
    from source
    where code_siren is not null
)

select * from renamed