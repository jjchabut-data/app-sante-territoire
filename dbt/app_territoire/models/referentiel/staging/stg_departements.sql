-- referentiel/staging/stg_departements.sql
with source as (
    select * from {{ source('raw', 'ref_dept_geom_2026') }}
),

renamed as (
    select
        code_insee                  as code_departement,
        nom_officiel                as nom_departement,
        code_insee_de_la_region     as code_region,
        lon,
        lat,
        geometry
    from source
    where code_insee is not null
)

select * from renamed