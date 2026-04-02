-- referentiel/staging/stg_ref_arrond_municipaux.sql
with source as (
    select * from {{ source('raw', 'ref_arr_muni_geom_2026') }}
),

renamed as (
    select
        code_insee                          as code_arrondissement,
        nom_officiel                        as nom_arrondissement,
        numero_de_l_arrondissement_municipal as numero_arrondissement,
        code_insee_de_la_commune_de_rattach as code_commune_rattachement,
        population,
        code_postal,
        lon                             as longitude,
        lat                             as latitude,
        geometry
    from source
    where code_insee is not null
)

select * from renamed