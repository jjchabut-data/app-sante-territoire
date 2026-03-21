-- stg_apl_sagesfemmes_2023.sql
with source as (
    select * from {{ source('raw', 'apl_sagesfemmes_2023') }}
),

renamed as (
    select
        `Code commune INSEE`                                              as code_commune,
        cast(`APL aux sages-femmes`                                       as float64) as apl_sagefemmes
    from source
    where `Code commune INSEE` not like 'Lecture%'
      and `Code commune INSEE` not like 'Champ%'
      and `Code commune INSEE` not like 'Source%'
      and `Code commune INSEE` is not null
)

select * from renamed