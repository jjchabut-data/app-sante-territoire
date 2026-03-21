-- referentiel/staging/stg_regions.sql
with source as (
    select * from {{ source('raw', 'ref_region_geom_2026') }}
),

renamed as (
    select
        code_insee      as code_region,
        nom_officiel    as nom_region,
        lon,
        lat,
        geometry
    from source
    where code_insee is not null
)

select * from renamed