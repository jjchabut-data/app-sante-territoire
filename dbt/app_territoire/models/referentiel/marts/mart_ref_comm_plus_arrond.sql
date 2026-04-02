-- referentiel/marts/mart_ref_comm_plus_arrond.sql
with communes as (
    select
        code,
        nom,
        population,
        code_departement,
        code_region,
        codes_epci,
        longitude,
        latitude,
        'commune'           as type_geo
    from {{ ref('int_ref_communes') }}
),

arrondissements as (
    select
        a.code,
        a.nom,
        a.population,
        c.code_departement,
        c.code_region,
        c.codes_epci,
        a.longitude,
        a.latitude,
        'arrondissement'        as type_geo
    from {{ ref('int_ref_arrond_municipaux') }} a
    left join communes c
        on a.code_commune_rattachement = c.code
)

select * from communes
union all
select * from arrondissements