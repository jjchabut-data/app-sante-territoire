-- referentiel/staging/stg_densite_bassinvie_2025_geo_2026.sql
-- Édition 2026 : population PMUN23 (RP 2023) au lieu de PMUN22.
with source as (
    select * from {{ source('raw', 'densite_bassinvie_2025_geo_2026') }}
),

renamed as (
    select
        BV              as code_bassinvie,
        LIB_BV          as nom_bassinvie,
        DENS            as code_densite,
        LIBDENS         as libelle_densite,
        PMUN23          as population_2023,
        P1              as pct_cat1,
        P2              as pct_cat2,
        P3              as pct_cat3
    from source
)

select * from renamed
