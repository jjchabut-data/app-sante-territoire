-- referentiel/staging/stg_densite_bassinvie_2025_geo_2025.sql
with source as (
    select * from {{ source('raw', 'densite_bassinvie_2025_geo_2025') }}
),

renamed as (
    select
        BV              as code_bassinvie,
        LIB_BV          as nom_bassinvie,
        DENS            as code_densite,
        LIBDENS         as libelle_densite,
        PMUN22          as population_2022,
        P1              as pct_cat1,
        P2              as pct_cat2,
        P3              as pct_cat3
    from source
)

select * from renamed