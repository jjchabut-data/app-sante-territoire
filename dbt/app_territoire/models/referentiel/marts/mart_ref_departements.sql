-- referentiel/marts/mart_ref_departements.sql
select
    code_departement    as code,
    nom_departement     as nom,
    lon,
    lat
from {{ ref('stg_departements') }}