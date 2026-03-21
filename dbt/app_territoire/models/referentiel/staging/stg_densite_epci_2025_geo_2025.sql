-- referentiel/staging/stg_densite_epci_2025_geo_2025.sql
with source as (
    select * from {{ source('raw', 'densite_epci_2025_geo_2025') }}
),

renamed as (
    select
        ECPI            as code_epci,
        LIB_EPCI        as nom_epci,
        DENS            as code_densite,
        LIBDENS         as libelle_densite,
        PMUN22          as population_2022,
        P1              as pct_cat1,
        P2              as pct_cat2,
        P3              as pct_cat3
    from source
)

select * from renamed