-- referentiel/intermediate/int_densite_communes_current.sql
with source as (
    select * from {{ ref('stg_densite_communes_' ~ var('version_densite')) }}
),

with_score as (
    select
        code_commune,
        code_densite,
        libelle_densite,
        code_densite_7,
        libelle_densite_7,
        code_densite_aav,
        libelle_densite_aav,
        population,
        pct_cat1,
        pct_cat2,
        pct_cat3,
        case code_densite_7
            when '1' then  1.0
            when '2' then  0.8
            when '3' then  0.4
            when '4' then  0.0
            when '5' then -0.3
            when '6' then -0.7
            when '7' then -1.0
end as urbanite_score
    from source
)

select * from with_score