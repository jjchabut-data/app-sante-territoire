-- referentiel/marts/mart_ref_epci.sql
select
    code,
    nom,
    type,
    longitude,
    latitude
from {{ ref('int_ref_epci') }}