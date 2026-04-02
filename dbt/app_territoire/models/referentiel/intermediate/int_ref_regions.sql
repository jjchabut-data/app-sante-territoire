-- referentiel/intermediate/int_ref_regions.sql
with regions as (
    select
        code_region as code,
        nom_region as nom,
        longitude,
        latitude
    from {{ ref('stg_ref_regions') }}
)

select * from regions