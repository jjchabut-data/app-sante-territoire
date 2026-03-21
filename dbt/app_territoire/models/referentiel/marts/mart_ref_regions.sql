-- referentiel/marts/mart_ref_regions.sql
select
    code_region     as code,
    nom_region      as nom,
    lon,
    lat
from {{ ref('stg_regions') }}