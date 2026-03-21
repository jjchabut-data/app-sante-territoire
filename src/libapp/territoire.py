"""territoire.py — Modèle de domaine central de l'application.

Un Territoire représente la zone géographique choisie par l'utilisateur
(commune, département, EPCI, région ou zone d'emploi), enrichie de toutes
les métriques APL calculées sur les communes qui le composent.

Utilisation typique
-------------------
    row = ref[ref['code'] == code_sel].iloc[0]
    terr = Territoire.depuis_ref(row, rayon_km=15).calculer(df_indic, ze_mapping)

    print(terr)
    # Commune Ayrens (15016) — rayon 15 km — 8 commune(s), 3 421 hab., APL global = 1.82

Compatibilité avec le code existant
------------------------------------
    st.session_state['resultats'] = terr.vers_resultats()

    # Les onglets tab_tableaux, tab_graphiques, tab_contexte ne voient aucune
    # différence : ils continuent de lire le dict 'resultats' tel quel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from libapp.config import (
    APL_COLS,
    APL_STD_COLS,
    TYPES_TERRITOIRE,
)
from libapp import utils


# ─── Classe principale ────────────────────────────────────────────────────────

@dataclass
class Territoire:
    """Territoire sélectionné avec ses indicateurs APL agrégés.

    Attributs d'identité (obligatoires à la construction)
    -------------------------------------------------------
    type_terr : str
        Code du type de territoire : 'comm' | 'dept' | 'epci' | 'reg' | 'ze'
    code : str
        Code INSEE / SIREN / identifiant administratif du territoire.
    nom : str
        Nom lisible du territoire.
    rayon_km : int
        Rayon d'extension en kilomètres autour d'une commune centre.
        Ignoré si type_terr != 'comm'. 0 = commune seule.

    Attributs calculés (remplis par .calculer())
    ---------------------------------------------
    communes : pd.DataFrame
        Toutes les communes composant le territoire, avec leurs indicateurs.
    centre : pd.Series
        Coordonnées (latitude, longitude) du centre du territoire.
        Correspond à la commune sélectionnée pour type_terr == 'comm',
        au centroïde administratif pour les autres types.
    apl_global : float
        Score APL composite (moyenne pondérée par population des APL_STD_COLS).
    apl_moyens : dict[str, float]
        Moyenne pondérée par population de chaque indicateur APL brut
        (clés = APL_COLS).
    apl_std_moyens : dict[str, float]
        Même chose pour les indicateurs APL standardisés (clés = APL_STD_COLS).
    population_totale : int
        Population totale du territoire (somme sur les communes).
    nb_communes : int
        Nombre de communes composant le territoire.
    """

    # ── Identité ──────────────────────────────────────────────────────────────
    type_terr: str
    code:      str
    nom:       str
    rayon_km:  int = 0

    # ── Données calculées ─────────────────────────────────────────────────────
    communes:          Optional[pd.DataFrame] = field(default=None, repr=False)
    centre:            Optional[pd.Series]    = field(default=None, repr=False)
    apl_global:        Optional[float]        = None
    apl_moyens:        dict                   = field(default_factory=dict)
    apl_std_moyens:    dict                   = field(default_factory=dict)
    population_totale: int                    = 0
    nb_communes:       int                    = 0

    # ── Propriétés ───────────────────────────────────────────────────────────

    @property
    def label(self) -> str:
        """Label d'affichage court : 'Commune Ayrens (15016)'."""
        return f"{TYPES_TERRITOIRE.get(self.type_terr, self.type_terr)} {self.nom} ({self.code})"

    @property
    def titre(self) -> str:
        """Titre long incluant le rayon si applicable : '… — rayon 15 km'."""
        t = self.label
        if self.est_commune and self.rayon_km:
            t += f" — rayon {self.rayon_km} km"
        return t

    @property
    def est_commune(self) -> bool:
        """Vrai si le territoire est de type commune."""
        return self.type_terr == "comm"

    @property
    def est_calcule(self) -> bool:
        """Vrai si .calculer() a déjà été appelé."""
        return self.communes is not None

    @property
    def niveau_apl(self) -> str:
        """Interprétation qualitative du score APL global.

        Reprend la même grille que utils.niveau_apl() appliquée ici
        au score standardisé (centré sur 0) :
            < -1.0  → Critique
            < -0.3  → Faible
            < +0.3  → Moyen
            ≥ +0.3  → Bon
        """
        v = self.apl_global
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "Inconnu"
        if v < -1.0:
            return "Critique"
        if v < -0.3:
            return "Faible"
        if v < 0.3:
            return "Moyen"
        return "Bon"

    # ── Constructeurs alternatifs ─────────────────────────────────────────────

    @classmethod
    def depuis_ref(
        cls,
        row: pd.Series,
        rayon_km: int = 0,
    ) -> "Territoire":
        """Construit un Territoire depuis une ligne du référentiel territoires.

        Parameters
        ----------
        row : pd.Series
            Ligne de ref_territoires avec les colonnes 'type', 'code', 'nom'.
        rayon_km : int
            Rayon d'extension (pertinent uniquement pour type_terr == 'comm').
        """
        return cls(
            type_terr=row["type"],
            code=str(row["code"]),
            nom=row["nom"],
            rayon_km=rayon_km,
        )

    # ── Calcul ───────────────────────────────────────────────────────────────

    def calculer(
        self,
        df_indic: pd.DataFrame,
    ) -> "Territoire":
        """Calcule les communes et tous les indicateurs APL agrégés."""
        self.communes, self.centre = utils.calculer_communes_territoire(
            df_indic,
            self.type_terr,
            self.code,
            self.rayon_km,
        )

        self.population_totale = int(self.communes["population"].sum())
        self.nb_communes       = len(self.communes)
        self.apl_moyens        = utils.calculer_apl_moyens(self.communes, APL_COLS)
        self.apl_std_moyens    = utils.calculer_apl_moyens(self.communes, APL_STD_COLS)
        self.apl_global        = utils.calculer_score_apl(self.communes)

        return self

    # ── Compatibilité avec le code existant ──────────────────────────────────

    def vers_resultats(self) -> dict:
        """Sérialise vers le dict ``resultats`` attendu par les onglets.

        Permet une migration progressive : tab_selection construit un
        Territoire, puis stocke ``terr.vers_resultats()`` dans session_state —
        les onglets tab_tableaux, tab_graphiques et tab_contexte continuent
        de fonctionner sans modification.

        Returns
        -------
        dict avec les clés :
            communes_terr, commune_centre, apl_global, apl_moyens,
            population_totale, nb_communes, rayon_km, territoire_label,
            type_terr, code_sel
        """
        return {
            "communes_terr":     self.communes,
            "commune_centre":    self.centre,
            "apl_global":        self.apl_global,
            "apl_moyens":        self.apl_moyens,
            "population_totale": self.population_totale,
            "nb_communes":       self.nb_communes,
            "rayon_km":          self.rayon_km if self.est_commune else None,
            "territoire_label":  self.label,
            "type_terr":         self.type_terr,
            "code_sel":          self.code,
        }

    # ── Représentation ───────────────────────────────────────────────────────

    def __str__(self) -> str:
        if not self.est_calcule:
            return f"{self.label} (non calculé)"
        apl_str = f"{self.apl_global:.2f}" if self.apl_global is not None else "n/a"
        return (
            f"{self.titre}"
            f" — {self.nb_communes} commune(s)"
            f", {self.population_totale:,} hab."
            f", APL global = {apl_str} ({self.niveau_apl})"
        )

    def __repr__(self) -> str:
        return (
            f"Territoire(type_terr={self.type_terr!r}, code={self.code!r},"
            f" nom={self.nom!r}, rayon_km={self.rayon_km},"
            f" calcule={self.est_calcule})"
        )
