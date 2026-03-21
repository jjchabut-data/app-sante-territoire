-- sante/marts/mart_apl_commune.sql
with apl as (
    select
        code_commune,
        apl_medecins,
        quintile_medecins,
        quintile_label_medecins,
        apl_med_65,
        quintile_med_65,
        quintile_label_med_65,
        apl_med_62,
        quintile_med_62,
        quintile_label_med_62,
        apl_med_60,
        quintile_med_60,
        quintile_label_med_60,
        apl_dentistes,
        quintile_dentistes,
        quintile_label_dentistes,
        apl_infirmiers,
        quintile_infirmiers,
        quintile_label_infirmiers,
        apl_kines,
        quintile_kines,
        quintile_label_kines,
        apl_sagefemmes,
        quintile_sagefemmes,
        quintile_label_sagefemmes,
        apl_medecins_std,
        apl_med_65_std,
        apl_med_62_std,
        apl_med_60_std,
        apl_dentistes_std,
        apl_infirmiers_std,
        apl_kines_std,
        apl_sagefemmes_std,
        score_apl,
        score_apl_std,
        quintile_apl_nat
    from {{ ref('int_apl_current_all') }}
),

communes as (
    select
        code            as code_commune,
        nom             as nom_commune,
        population,
        codes_epci,
        code_departement,
        code_region,
        longitude,
        latitude
    from {{ ref('mart_ref_comm_plus_arrond') }}
),

densites as (
    select
        code_commune,
        code_densite_7,
        libelle_densite_7,
        urbanite_score
    from {{ ref('int_densite_communes_current') }}
),

temps_access as (
    select
        code_commune,
        tps_su_smur,
        tps_su_smur_mcs,
        tps_heli_smur
    from {{ ref('int_tps_acces_urg_current') }}
),

final as (
    select
        c.code_commune,
        c.nom_commune,
        c.population,
        c.codes_epci,
        c.code_departement,
        c.code_region,
        c.longitude,
        c.latitude,
        a.apl_medecins,
        a.quintile_medecins,
        a.quintile_label_medecins,
        a.apl_med_65,
        a.quintile_med_65,
        a.quintile_label_med_65,
        a.apl_med_62,
        a.quintile_med_62,
        a.quintile_label_med_62,
        a.apl_med_60,
        a.quintile_med_60,
        a.quintile_label_med_60,
        a.apl_dentistes,
        a.quintile_dentistes,
        a.quintile_label_dentistes,
        a.apl_infirmiers,
        a.quintile_infirmiers,
        a.quintile_label_infirmiers,
        a.apl_kines,
        a.quintile_kines,
        a.quintile_label_kines,
        a.apl_sagefemmes,
        a.quintile_sagefemmes,
        a.quintile_label_sagefemmes,
        a.apl_medecins_std,
        a.apl_med_65_std,
        a.apl_med_62_std,
        a.apl_med_60_std,
        a.apl_dentistes_std,
        a.apl_infirmiers_std,
        a.apl_kines_std,
        a.apl_sagefemmes_std,
        a.score_apl,
        a.score_apl_std,
        a.quintile_apl_nat,
        dn.code_densite_7,
        dn.libelle_densite_7,
        dn.urbanite_score,
        ta.tps_su_smur,
        ta.tps_su_smur_mcs,
        ta.tps_heli_smur
    from communes c 
    left join apl a on c.code_commune = a.code_commune
    left join densites dn on c.code_commune = dn.code_commune
    left join temps_access ta on c.code_commune = ta.code_commune
)

select * from final