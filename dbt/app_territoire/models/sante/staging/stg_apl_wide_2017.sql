with source as (
    select * from {{ source('raw', 'apls_wide_2017') }}
),

unpivoted as (
    select
        `Code commune`          as code_commune,
        `Libellé de la commune` as nom_commune,
        2017                    as annee,
        profession,
        apl,
        population_std
    from source
    unpivot (
        (apl, population_std) for profession in (
            (`APL aux médecins généralistes`,
             `Population standardisée par la consommation de soins chez un médecin généraliste`)
             as 'medecin',
            (`APL aux infirmiers`,
             `Population standardisée par la consommation de soins infirmiers`)
             as 'infirmier',
            (`APL aux masseurs-kinésithérapeutes`,
             `Population standardisée par la consommation de soins de masso-kinésithérapie`)
             as 'kine',
            (`APL aux sages-femmes`,
             `Population standardisée par la consommation de soins chez une sage-femme`)
             as 'sage_femme'
        )
    )
)

select * from unpivoted