-- referentiel/intermediate/int_ref_territoires.sql

select code, nom, 'commune' as type, longitude, latitude
from {{ ref('int_ref_communes') }}
union all
select code, nom, 'commune' as type, longitude, latitude
from {{ ref('int_ref_arrond_municipaux') }}
union all
select code, nom, 'epci' as type, longitude, latitude  
from {{ ref('int_ref_epci') }}
union all
select code, nom, 'departement' as type, longitude, latitude
from {{ ref('int_ref_departements') }}
union all
select code, nom, 'region' as type, longitude, latitude
from {{ ref('int_ref_regions') }}