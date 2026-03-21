-- socio_demo/staging/stg_isd_population_age_millesimes.sql
with source_2023 as (
    select * from {{ source('raw', 'isd_c01_pop_selon_age_2023') }}
),

source_2024 as (
    select * from {{ source('raw', 'isd_c01_pop_selon_age_2024') }}
),

source_2025 as (
    select * from {{ source('raw', 'isd_c01_pop_selon_age_2025') }}
),

unioned as (
    select * from source_2023
    union all
    select * from source_2024
    union all
    select * from source_2025
),

renamed as (
    select
        `code dept`             as code_departement,
        `nom dept`              as nom_departement,
        `Moins de 20 ans`       as pop_moins_20,
        `Moins de 25 ans`       as pop_moins_25,
        `25 à 64 ans`           as pop_25_64,
        `65 ans ou plus`        as pop_65_plus,
        `75 ans ou plus`        as pop_75_plus,
        `80 ans ou plus`        as pop_80_plus,
        `85 ans ou plus`        as pop_85_plus,
        `pop totale`            as pop_totale,
        `% Moins de 20 ans`   as pct_moins_20,
        `% Moins de 25 ans`    as pct_moins_25,
        `% 25 à 64 ans`        as pct_25_64,
        `% 65 ans ou plus`     as pct_65_plus,
        `% 75 ans ou plus`     as pct_75_plus,
        `% 80 ans ou plus`     as pct_80_plus,
        `% 85 ans ou plus`     as pct_85_plus,
        `annee`                as annee
    from unioned
    where `code dept` is not null
)

select * from renamed