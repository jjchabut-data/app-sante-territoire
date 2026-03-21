-- sante/staging/stg_temps_acces_urgences_2019.sql
with source as (
    select * from {{ source('raw', 'temps_acces_urgences_2019') }}
),

renamed as (
    select
        `Code commune Insee`    as code_commune,
        `Libellé commune`       as nom_commune,
        `Département`           as code_departement,
        `Région`                as code_region,
        null                    as nom_region,
        `SU`                    as su,
        `SMUR`                  as smur,
        `MCS`                   as mcs,
        `HéliSMUR`              as heli_smur,
        null                    as heli_sc,
        `Population 2017`       as population,
        `typ_equip`             as type_equipement,
        `tps_SU_SMUR`           as tps_su_smur,
        `tps_SU_SMUR_MCS`       as tps_su_smur_mcs,
        `tps_ychelismur`        as tps_heli_smur,
        `tps_ycheli`            as tps_heli,
        `com_equipee`           as commune_equipee,
        `densite`               as densite,
        2019                    as annee
    from source
    where `Code commune Insee` is not null
)

select * from renamed