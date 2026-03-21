-- referentiel/marts/mart_ref_epci.sql
select
    code_epci   as code,
    nom_epci    as nom,
    type_epci,
    lon,
    lat
from {{ ref('stg_epci') }}