-- stg_densite_communes_2025_geo_2026.sql
-- Édition 2026 : population PMUN23 (RP 2023) au lieu de PMUN22 (RP 2022).
with source as (
    select * from {{ source('raw', 'densite_comm_2025_geo_2026') }}
)

select
    CODGEO      as code_commune,
    DENS        as code_densite,
    LIBDENS     as libelle_densite,
    DENS7       as code_densite_7,
    LIBDENS7    as libelle_densite_7,
    DENS_AAV    as code_densite_aav,
    LIBDENS_AAV as libelle_densite_aav,
    PMUN23      as population,
    P1          as pct_cat1,
    P2          as pct_cat2,
    P3          as pct_cat3
from source
