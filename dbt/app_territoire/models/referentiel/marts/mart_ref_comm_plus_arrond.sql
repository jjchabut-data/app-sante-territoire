-- referentiel/marts/mart_ref_comm_plus_arrond.sql
with communes as (
    select
        code_commune        as code,
        nom_commune         as nom,
        population,
        code_departement,
        code_region,
        codes_epci,
        longitude,
        latitude,
        'commune'           as type_geo
    from {{ ref('stg_ref_communes') }}
),

arrondissements as (
    select
        a.code_arrondissement   as code,
        a.nom_arrondissement    as nom,
        a.population,
        c.code_departement,
        c.code_region,
        c.codes_epci,
        a.lon                   as longitude,
        a.lat                   as latitude,
        'arrondissement'        as type_geo
    from {{ ref('stg_ref_arrond_municipaux') }} a
    left join {{ ref('stg_ref_communes') }} c
        on a.code_commune_rattachement = c.code_commune
)

select * from communes
union all
select * from arrondissements