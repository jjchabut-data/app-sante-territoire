-- socio_demo/staging/stg_isd_mortalite_2025.sql
-- Colonnes déjà propres en sortie de load_isd_api.py (pivot direct vers le
-- schéma large) : pas de renommage à refaire ici. `nb_deces_domicilies`
-- est absent pour 2025 : la DREES ne l'avait pas encore publié au moment
-- du chargement (2026-09-23).
with source as (
    select * from {{ source('raw', 'isd_c03_tx_mortalite_2025') }}
)

select *
from source
where code_departement is not null
