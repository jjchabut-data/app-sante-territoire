-- stg_cog_remembrement_2026.sql
select
    code_insee                          as code_commune_deleguee,
    code_insee_de_la_commune_de_rattach as code_commune_nouvelle,
    nom_officiel                        as nom_commune_deleguee,
    nature,                             -- type : déléguée ou associée
    population
from {{ source('raw', 'ref_comm_remembrement_2026') }}
where code_insee_de_la_commune_de_rattach is not null