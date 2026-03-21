-- stg_apl_medecins_2023.sql
with source as (
    select * from {{ source('raw', 'apl_medecins_2023') }}
),

renamed as (
    select
        `Code commune INSEE`                                     as code_commune,
        cast(`APL aux médecins généralistes`                     as float64) as apl_medecins,
        cast(`APL aux médecins généralistes de 65 ans et moins ` as float64) as apl_med_65,
        cast(`APL aux médecins généralistes de 62 ans et moins ` as float64) as apl_med_62,
        cast(`APL aux médecins généralistes de 60 ans et moins ` as float64) as apl_med_60
    from source
    where `Code commune INSEE` not like 'Lecture%'
      and `Code commune INSEE` not like 'Champ%'
      and `Code commune INSEE` not like 'Source%'
      and `Code commune INSEE` is not null
)

select * from renamed