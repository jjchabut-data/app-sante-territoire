-- socio_demo/staging/stg_isd_vieillissement.sql
with source as (
    select * from {{ source('raw', 'isd_c02_ind_vieillisement_1999_2025') }}
),

renamed as (
    select
        code_departement,
        nom_departement,
        `En 1999`   as indice_1999,
        `En 2016`   as indice_2016,
        `En 2022`   as indice_2022,
        `En 2024`   as indice_2024,
        `En 2025`   as indice_2025
    from source
    where code_departement is not null
)

select * from renamed