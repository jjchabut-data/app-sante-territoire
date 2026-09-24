-- referentiel/staging/stg_densite_epci_2025_geo_2026.sql
-- Édition 2026 : colonne "EPCI" (coquille "ECPI" de l'édition 2025 corrigée
-- par l'INSEE), population PMUN23 (RP 2023) au lieu de PMUN22.
with source as (
    select * from {{ source('raw', 'densite_epci_2025_geo_2026') }}
),

renamed as (
    select
        EPCI            as code_epci,
        LIB_EPCI        as nom_epci,
        DENS            as code_densite,
        LIBDENS         as libelle_densite,
        PMUN23          as population_2023,
        P1              as pct_cat1,
        P2              as pct_cat2,
        P3              as pct_cat3
    from source
)

select * from renamed
