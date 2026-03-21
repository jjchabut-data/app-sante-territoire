-- socio_demo/staging/stg_isd_mortalite_2024.sql
with source as (
    select * from {{ source('raw', 'isd_c03_tx_mortalite_2024') }}
),

renamed as (
    select
        `code dept`                                         as code_departement,
        `Département`                                       as nom_departement,
        `Taux brut de mortalite`                            as tx_mortalite_brut,
        `Taux brut de mortalite des femmes`                 as tx_mortalite_brut_femmes,
        `Taux brut de mortalite des hommes`                 as tx_mortalite_brut_hommes,
        `Taux de mortalite standard des 0 a 64 ans`         as tx_mortalite_std_0_64,
        `Taux de mortalite standard des 65 ans ou plus`     as tx_mortalite_std_65_plus,
        `Taux de mortalite infantile`                       as tx_mortalite_infantile,
        `Nombre de deces domicilies`                        as nb_deces_domicilies
    from source
    where `code dept` is not null
)

select * from renamed