import streamlit as st


def render():
    st.markdown("## Méthodologie — Diagnostic territorial")
    st.markdown("""
### APL — Accessibilité Potentielle Localisée

L'**APL** mesure l'offre de soins accessible à la population d'une commune,
en tenant compte de la proximité géographique et de l'activité des professionnels.

---

### Score APL composite

```
Score APL = 0,35 × APL_médecins_std
          + 0,25 × APL_infirmiers_std
          + 0,20 × APL_kinés_std
          + 0,15 × APL_dentistes_std
          + 0,05 × APL_sages-femmes_std
```

| Score APL composite | Niveau   |
|---------------------|----------|
| < −0,5              | Critique |
| −0,5 à 0            | Faible   |
| 0 à 0,5             | Moyen    |
| > 0,5               | Bon      |

---

### Thématiques cartographiques

- **Score APL / APL par profession / Score socio-sanitaire** : dégradé Viridis (violet → jaune)
- **Cluster** : couleurs discrètes K-Means k=5
- **TextLayer** : noms de département (blanc cassé, halo noir)

---

### Types de territoire

| Type         | Méthode de sélection des communes                         |
|--------------|-----------------------------------------------------------|
| Commune      | Toutes les communes dans un rayon R autour du centre      |
| Département  | Communes du département (code INSEE)                      |
| EPCI         | Communes du groupement intercommunal (SIREN)              |
| Région       | Communes des départements de la région                    |
| Zone d'emploi | Communes de la zone d'emploi INSEE 2020                  |

**Références :** DREES/IRDES — [Méthodologie APL 2020](https://drees.solidarites-sante.gouv.fr/sources-outils-et-enquetes/lindicateur-daccessibilite-potentielle-localisee-apl)
""")
