-- sante/intermediate/int_tps_acces_urg_current.sql
select
    code_commune,
    su,
    smur,
    mcs,
    heli_smur,
    heli_sc,
    type_equipement,
    tps_su_smur,
    tps_su_smur_mcs,
    tps_heli_smur,
    tps_heli
from {{ ref('stg_temps_acces_urgences_' ~ var('annee_tps_acces_urgences')) }}