-- referentiel/marts/mart_ref_departements.sql
select
    code,
    nom,
    longitude,
    latitude
from {{ ref('int_ref_departements') }}