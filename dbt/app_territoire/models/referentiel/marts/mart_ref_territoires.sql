-- marts/mart_ref_territoires.sql

select code, nom, type, longitude, latitude
from {{ ref('int_ref_territoires') }}