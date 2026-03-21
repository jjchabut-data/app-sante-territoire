-- stg_apl_kines_2023.sql
with source as (
    select * from {{ source('raw', 'apl_kines_2023') }}
),

renamed as (
    select
        `Code commune INSEE`                                          as code_commune,
        cast(`APL aux kinésithérapeutes`                              as float64) as apl_kines,
    from source
    where `Code commune INSEE` not like 'Lecture%'
      and `Code commune INSEE` not like 'Champ%'
      and `Code commune INSEE` not like 'Source%'
      and `Code commune INSEE` is not null
)

select * from renamed