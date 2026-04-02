-- referentiel/marts/mart_ref_regions.sql
select
    code,
    nom,
    longitude,
    latitude
from {{ ref('int_ref_regions') }}