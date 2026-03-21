-- referentiel/staging/stg_ref_communes.sql
with source as (
    select * from {{ source('raw', 'ref_comm_geom_2026') }}
),

renamed as (
    select
        code_insee                      as code_commune,
        nom_officiel                    as nom_commune,
        statut,
        population,
        code_insee_du_departement       as code_departement,
        code_insee_de_la_region         as code_region,
        codes_siren_des_epci            as codes_epci,
        code_postal,
        superficie_cadastrale,
        lon                             as longitude,
        lat                             as latitude,
        geometry
    from source
    where code_insee is not null
)

select * from renamed