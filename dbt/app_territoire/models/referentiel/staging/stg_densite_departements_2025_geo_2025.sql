-- referentiel/staging/stg_densite_departements_2025_geo_2025.sql
with source as (
    select * from {{ source('raw', 'densite_dept_2025_geo_2025') }}
),

renamed as (
    select
        DEP             as code_departement,
        LIB_DEP         as nom_departement,
        DENS            as code_densite,
        LIBDENS         as libelle_densite,
        P_RURAL         as pct_rural
    from source
)

select * from renamed