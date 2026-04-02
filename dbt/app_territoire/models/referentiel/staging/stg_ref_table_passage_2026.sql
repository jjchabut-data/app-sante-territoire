-- stg_ref_table_passage_2026.sql
select
    CODGEO_INI  as code_commune_ini,
    CODGEO_2026 as code_commune_2026,
    LIBGEO_2026 as nom_commune_2026
from {{ source('raw', 'table_passage_geo2003_geo2026') }}
where CODGEO_INI is not null
  and CODGEO_2026 is not null