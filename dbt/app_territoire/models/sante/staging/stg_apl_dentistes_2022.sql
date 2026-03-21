-- stg_apl_dentistes_2022.sql
with source as (
    select * from {{ source('raw', 'apl_dentistes_2022') }}
),

renamed as (
    select
        `Code commune INSEE`                                          as code_commune,
        cast(`APL aux chirurgiens-dentistes`                          as float64) as apl,
        cast(`Population standardisée 2020 pour les chirurgiens-dentistes` as float64) as population_std,
        cast(`Population totale 2020`                                 as int64)   as population_totale,
        2022                                                          as annee,
        'dentiste'                                                    as profession
    from source
    where `Code commune INSEE` not like 'Lecture%'
      and `Code commune INSEE` not like 'Champ%'
      and `Code commune INSEE` not like 'Source%'
      and `Code commune INSEE` is not null
)

select * from renamed