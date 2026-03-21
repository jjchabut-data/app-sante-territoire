-- stg_apl_infirmiers_2019.sql
with source as (
    select * from {{ source('raw', 'apl_infirmiers_2019') }}
),

cleaned as (
    select
        `Commune`                                                                                    as code_commune,
        cast(`APL aux infirmiers`                                                                    as float64) as apl,
        cast(`Population standardisée par la consommation de soins infirmiers par tranche d'âge`    as float64) as population_std,
        null                                                                                         as population_totale,
        2019                                                                                         as annee,
        'infirmier'                                                                                  as profession
    from source
    where `Commune` not like 'Lecture%'
      and `Commune` not like 'Champ%'
      and `Commune` not like 'Source%'
      and `Commune` is not null
)

select * from cleaned