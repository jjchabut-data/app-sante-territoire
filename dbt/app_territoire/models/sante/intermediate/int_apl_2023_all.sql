-- int_apl_2023_all.sql
with medecins as (
    select * from {{ ref('int_apl_2023_medecins') }}
),

dentistes as (
    select * from {{ ref('int_apl_2023_dentistes') }}
),

infirmiers as (
    select * from {{ ref('int_apl_2023_infirmiers') }}
),

kines as (
    select * from {{ ref('int_apl_2023_kines') }}
),

sagefemmes as (
    select * from {{ ref('int_apl_2023_sagefemmes') }}
),

scoreapl as (
    select
        coalesce(m.code_commune, d.code_commune, i.code_commune, k.code_commune, s.code_commune) as code_commune,

        m.apl_medecins,        m.apl_medecins_std,         m.quintile_medecins,        m.quintile_label_medecins,
        m.apl_med_65,          m.apl_med_65_std,           m.quintile_med_65,          m.quintile_label_med_65,
        m.apl_med_62,          m.apl_med_62_std,           m.quintile_med_62,          m.quintile_label_med_62,
        m.apl_med_60,          m.apl_med_60_std,           m.quintile_med_60,          m.quintile_label_med_60,

        d.apl_dentistes,       d.apl_dentistes_std,        d.quintile_dentistes,       d.quintile_label_dentistes,
        i.apl_infirmiers,      i.apl_infirmiers_std,       i.quintile_infirmiers,      i.quintile_label_infirmiers,
        k.apl_kines,           k.apl_kines_std,            k.quintile_kines,           k.quintile_label_kines,
        s.apl_sagefemmes,      s.apl_sagefemmes_std,       s.quintile_sagefemmes,      s.quintile_label_sagefemmes,
        (
            coalesce(m.apl_medecins_std,   0) * 0.35
          + coalesce(i.apl_infirmiers_std, 0) * 0.25
          + coalesce(k.apl_kines_std,      0) * 0.20
          + coalesce(d.apl_dentistes_std,  0) * 0.15
          + coalesce(s.apl_sagefemmes_std, 0) * 0.05
        ) as score_apl

    from medecins m
    full outer join dentistes  d on m.code_commune = d.code_commune
    full outer join infirmiers i on m.code_commune = i.code_commune
    full outer join kines      k on m.code_commune = k.code_commune
    full outer join sagefemmes s on m.code_commune = s.code_commune
),

final as (
    select
    code_commune,
    apl_medecins,        apl_medecins_std,         quintile_medecins,        quintile_label_medecins,
    apl_med_65,          apl_med_65_std,           quintile_med_65,          quintile_label_med_65,
    apl_med_62,          apl_med_62_std,           quintile_med_62,          quintile_label_med_62,
    apl_med_60,          apl_med_60_std,           quintile_med_60,          quintile_label_med_60,
    apl_dentistes,       apl_dentistes_std,        quintile_dentistes,       quintile_label_dentistes,
    apl_infirmiers,      apl_infirmiers_std,       quintile_infirmiers,      quintile_label_infirmiers,
    apl_kines,           apl_kines_std,           quintile_kines,           quintile_label_kines,
    apl_sagefemmes,      apl_sagefemmes_std,       quintile_sagefemmes,      quintile_label_sagefemmes,

    score_apl,
    (score_apl - avg(score_apl) over ())
    / nullif(stddev(score_apl) over (), 0) as score_apl_std,
    ntile(5) over (order by score_apl)     as quintile_apl_nat
    from scoreapl
)
select * from final