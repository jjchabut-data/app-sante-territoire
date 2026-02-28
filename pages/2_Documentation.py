import streamlit as st
from utils import inject_css

inject_css()

st.title("📖 Documentation")

st.markdown("""
## Score APL — Méthodologie

Score composite d'accessibilité aux soins primaires calculé comme suit :

```
score_apl = 0.35 × APL_médecins_std
          + 0.25 × APL_infirmiers_std
          + 0.20 × APL_kines_std
          + 0.15 × APL_dentistes_std
          + 0.05 × APL_sages-femmes_std
```

### Standardisation

Score Z appliqué sur chaque APL pour comparabilité inter-professionnelle :

```
Score Z = (APL - moyenne France) / écart-type France
```

- `z > 0` → offre supérieure à la moyenne nationale
- Source : `StandardScaler` sklearn

### Pondération

Priorité aux médecins généralistes (35 %) puis aux infirmiers (25 %) selon l'impact
sur la population ([DREES](https://drees.solidarites-sante.gouv.fr)).

### Interprétation

| Score APL | Niveau        |
|-----------|---------------|
| < −0.5    | Critique      |
| −0.5 à 0  | Faible        |
| 0 à 0.5   | Moyen         |
| > 0.5     | Bon           |

Q1 + Q2 → priorités d'implantation (déserts médicaux)

---

**Référence :** DREES/IRDES — APL Méthodologie 2020
https://drees.solidarites-sante.gouv.fr/sources-outils-et-enquetes/lindicateur-daccessibilite-potentielle-localisee-apl
""")
