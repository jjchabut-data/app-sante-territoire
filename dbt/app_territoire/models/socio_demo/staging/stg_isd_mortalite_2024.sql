-- socio_demo/staging/stg_isd_mortalite_2024.sql
-- Colonnes déjà renommées en amont par load_isd_mortalite.py (RENAME_MAP),
-- avant chargement dans raw : pas de renommage à refaire ici.
with source as (
    select * from {{ source('raw', 'isd_c03_tx_mortalite_2024') }}
)

select *
from source
where code_departement is not null