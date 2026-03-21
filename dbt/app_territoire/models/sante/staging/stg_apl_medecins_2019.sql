with source as (
    select * from {{ source('raw', 'apl_medecins_2019') }}
),

cleaned as (
    select
        `Commune`                                                                                           as code_commune,
        cast(`APL aux médecins généralistes`                                                                as float64) as apl,
        null                                                                                                as apl_65,
        null                                                                                                as apl_62,
        null                                                                                                as apl_60,
        cast(`Population standardisée par la consommation de soins de médecine générale par tranche d'âge` as float64) as population_std,
        null                                                                                                as population_totale,
        2019                                                                                                as annee,
        'medecin'                                                                                           as profession
    from source
    where `Commune` not like 'Lecture%'
      and `Commune` not like 'Champ%'
      and `Commune` not like 'Source%'
      and `Commune` is not null
)

select * from cleaned