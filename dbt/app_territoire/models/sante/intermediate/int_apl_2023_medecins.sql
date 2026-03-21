-- int_apl_2023_medecins.sql
with source as (
    select
        code_commune,
        apl_medecins,
        apl_med_65,
        apl_med_62,
        apl_med_60
    from {{ ref('stg_apl_medecins_2023') }}
),

with_quintiles as (
    select
        code_commune,

        apl_medecins,
        ntile(5) over (order by apl_medecins)   as quintile_medecins,
        case ntile(5) over (order by apl_medecins)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_medecins,

        apl_med_65,
        ntile(5) over (order by apl_med_65)     as quintile_med_65,
        case ntile(5) over (order by apl_med_65)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_65,

        apl_med_62,
        ntile(5) over (order by apl_med_62)     as quintile_med_62,
        case ntile(5) over (order by apl_med_62)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_62,

        apl_med_60,
        ntile(5) over (order by apl_med_60)     as quintile_med_60,
        case ntile(5) over (order by apl_med_60)
            when 1 then 'très faible'
            when 2 then 'faible'
            when 3 then 'moyen'
            when 4 then 'élevé'
            when 5 then 'très élevé'
        end                                      as quintile_label_med_60,

        (apl_medecins - avg(apl_medecins) over ()) 
        / nullif(stddev(apl_medecins) over (), 0) as apl_medecins_std,
        
        (apl_med_65 - avg(apl_med_65) over ()) 
        / nullif(stddev(apl_med_65) over (), 0) as apl_med_65_std,
        
        (apl_med_62 - avg(apl_med_62) over ()) 
        / nullif(stddev(apl_med_62) over (), 0) as apl_med_62_std,
        
        (apl_med_60 - avg(apl_med_60) over ()) 
        / nullif(stddev(apl_med_60) over (), 0) as apl_med_60_std

    from source
)

select * from with_quintiles