-- stg_pop_commune_historique.sql
-- Population municipale (PMUN) par commune depuis 2015
-- Source : base_pop_historiques_1876_2023 (INSEE)
-- Format : long (commune × année)
-- Millésimes : 2015 → 2023

with source as (
    select
        CODGEO                          as code_commune,
        cast(PMUN2015 as int64)         as pmun_2015,
        cast(PMUN2016 as int64)         as pmun_2016,
        cast(PMUN2017 as int64)         as pmun_2017,
        cast(PMUN2018 as int64)         as pmun_2018,
        cast(PMUN2019 as int64)         as pmun_2019,
        cast(PMUN2020 as int64)         as pmun_2020,
        cast(PMUN2021 as int64)         as pmun_2021,
        cast(PMUN2022 as int64)         as pmun_2022,
        cast(PMUN2023 as int64)         as pmun_2023
    from {{ source('raw', 'base_pop_historiques_1876_2023') }}
    where CODGEO is not null
),

unpivot as (
    select code_commune, 2015 as annee, pmun_2015 as population from source
    union all
    select code_commune, 2016, pmun_2016 from source
    union all
    select code_commune, 2017, pmun_2017 from source
    union all
    select code_commune, 2018, pmun_2018 from source
    union all
    select code_commune, 2019, pmun_2019 from source
    union all
    select code_commune, 2020, pmun_2020 from source
    union all
    select code_commune, 2021, pmun_2021 from source
    union all
    select code_commune, 2022, pmun_2022 from source
    union all
    select code_commune, 2023, pmun_2023 from source
)

select
    code_commune,
    annee,
    population
from unpivot
where population is not null
  and population > 0
order by code_commune, annee