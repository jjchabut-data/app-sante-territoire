-- int_isd_population_age_current.sql
select * from {{ ref('stg_isd_population_age_millesimes') }}
where annee = {{ var('annee_pop_selon_age') }}