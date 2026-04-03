"""territoire.py — Classe Territoire, modèle de domaine central.

Encapsule toute la logique d'agrégation territoriale.

Types supportés
---------------
    commune | epci | departement | region | dynamique

Utilisation typique
-------------------
    # Construction + calcul (chaînable)
    terr = Territoire(type='commune', code='15014', rayon=15).calculer(df_indic)

    # Depuis le référentiel (compat avec code existant)
    terr = Territoire.depuis_ref(row, rayon=15).calculer(df_indic)

    # Export
    summary    = terr.to_summary()     # pour LLM / API /summary
    indicators = terr.to_indicators()  # pour Streamlit / API /indicators
    prompt     = terr.to_prompt()      # texte brut pour LLM

    # Compat Streamlit existant
    st.session_state['resultats'] = terr.vers_resultats()
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from libapp import utils
from libapp.config import (
    APL_COLS, APL_STD_COLS, QUINTILE_LABELS,
    APL_SEUILS, TENDANCE_NATIONALE, MARGE,
    SEUIL_DEGRADATION, SEUIL_AMELIORATION, SEUIL_POP_HAUSSE,
)

# ─── Constantes ───────────────────────────────────────────────────────────────

PROFESSIONS: dict[str, str] = {
    "medecin":    "apl_medecins",
    "dentiste":   "apl_dentistes",
    "infirmier":  "apl_infirmiers",
    "kine":       "apl_kines",
    "sage_femme": "apl_sagefemmes",
}

# Colonne quintile dans le df pour chaque profession
_QUINTILE_COLS: dict[str, str] = {
    "medecin":    "quintile_medecins",
    "dentiste":   "quintile_dentistes",
    "infirmier":  "quintile_infirmiers",
    "kine":       "quintile_kines",
    "sage_femme": "quintile_sagefemmes",
}

# Colonnes APL historique → colonnes pop_std associées
_PROFS_HIST: dict[str, str] = {
    "apl_medecins":   "pop_std_med",
    "apl_infirmiers": "pop_std_infirmier",
    "apl_kines":      "pop_std_kine",
    "apl_sagefemmes": "pop_std_sagefemme",
}

# Mapping type spec → type interne utils.py
_TYPE_TO_INTERNAL: dict[str, str] = {
    "commune":     "comm",
    "epci":        "epci",
    "departement": "dept",
    "region":      "reg",
    "dynamique":   None,   # pas encore supporté dans utils
}

_INTERNAL_TO_TYPE: dict[str, str] = {v: k for k, v in _TYPE_TO_INTERNAL.items() if v}

_TYPE_LABELS: dict[str, str] = {
    "commune":     "Commune",
    "epci":        "EPCI",
    "departement": "Département",
    "region":      "Région",
    "dynamique":   "Territoire",
}


# ─── Classe principale ────────────────────────────────────────────────────────

class Territoire:
    """Territoire sélectionné avec ses indicateurs APL agrégés.

    Paramètres
    ----------
    type : str
        ``commune`` | ``epci`` | ``departement`` | ``region`` | ``dynamique``
    code : str | None
        Code INSEE / SIREN. None uniquement pour type ``dynamique``.
    rayon : int
        Rayon km autour du centroïde — uniquement pour ``commune``.
        0 = commune seule.
    df : pd.DataFrame | None
        DataFrame indicateurs (mart_sante_comm_indic). Si fourni, les communes
        sont chargées dès la construction.
    nom : str | None
        Forcer le nom affiché (sinon déduit des données).
    """

    def __init__(
        self,
        type: str,
        code: str | None,
        rayon: int = 0,
        df: pd.DataFrame | None = None,
        nom: str | None = None,
    ) -> None:
        if type not in _TYPE_TO_INTERNAL:
            raise ValueError(
                f"Type inconnu: {type!r}. "
                f"Valeurs autorisées: {list(_TYPE_TO_INTERNAL)}"
            )
        self.type = type
        self.code = code
        self.rayon = rayon if type == "commune" else 0
        self._nom_force = nom
        self._df = df
        self._communes: pd.DataFrame | None = None
        self._centre: pd.Series | None = None

        if df is not None:
            self._communes, self._centre = self._load_communes()

    # ── Chargement communes ────────────────────────────────────────────────

    def _load_communes(self) -> tuple[pd.DataFrame, pd.Series | None]:
        """Sélectionne les communes composant le territoire."""
        type_interne = _TYPE_TO_INTERNAL.get(self.type)
        if type_interne is None:
            raise NotImplementedError(
                "Le type 'dynamique' n'est pas encore supporté dans _load_communes."
            )
        return utils.calculer_communes_territoire(
            self._df, type_interne, self.code, self.rayon
        )

    # ── Constructeurs alternatifs ──────────────────────────────────────────

    def calculer(self, df: pd.DataFrame) -> "Territoire":
        """Charge les communes depuis ``df``. Retourne ``self`` pour chaînage.

        Example
        -------
            terr = Territoire('commune', '15014', rayon=15).calculer(df_indic)
        """
        self._df = df
        self._communes, self._centre = self._load_communes()
        return self

    @classmethod
    def depuis_ref(cls, row: pd.Series, rayon: int = 0) -> "Territoire":
        """Construit depuis une ligne du référentiel ``ref_app_territoires``.

        Accepte les types courts (``comm``, ``dept``, ``reg``) et longs
        (``commune``, ``departement``, ``region``).
        """
        type_code = str(row["type"])
        # Normalise vers le format spec
        type_spec = _INTERNAL_TO_TYPE.get(type_code, type_code)
        t = cls(type=type_spec, code=str(row["code"]), rayon=rayon)
        t._nom_force = row.get("nom")
        return t

    # ── Propriétés d'identité ─────────────────────────────────────────────

    @property
    def _communes_loaded(self) -> pd.DataFrame:
        if self._communes is None:
            raise RuntimeError(
                "Appelez .calculer(df) avant d'accéder aux indicateurs du territoire."
            )
        return self._communes

    @property
    def nom(self) -> str:
        if self._nom_force:
            return self._nom_force
        if self._centre is not None and "nom_commune" in self._centre.index:
            return str(self._centre["nom_commune"])
        return self.code or ""

    @property
    def population(self) -> int:
        return int(self._communes_loaded["population"].sum())

    @property
    def nb_communes(self) -> int:
        return len(self._communes_loaded)

    @property
    def codes_communes(self) -> list[str]:
        return self._communes_loaded["code_insee"].tolist()

    @property
    def codes_epci(self) -> list[str]:
        col = "codes_siren_epci"
        if col not in self._communes_loaded.columns:
            return []
        return self._communes_loaded[col].dropna().unique().tolist()

    @property
    def codes_departements(self) -> list[str]:
        col = "code_dept"
        if col not in self._communes_loaded.columns:
            return []
        return self._communes_loaded[col].dropna().unique().tolist()

    @property
    def codes_regions(self) -> list[str]:
        col = "code_region"
        if col not in self._communes_loaded.columns:
            return []
        return self._communes_loaded[col].dropna().unique().tolist()

    @property
    def centroide_lat(self) -> float:
        if self._centre is None:
            return float("nan")
        return float(self._centre.get("latitude", float("nan")))

    @property
    def centroide_lon(self) -> float:
        if self._centre is None:
            return float("nan")
        return float(self._centre.get("longitude", float("nan")))

    # ── Indicateurs APL ───────────────────────────────────────────────────

    def indice_position(self, profession: str) -> float:
        """Moyenne pondérée par population du quintile national (1–5).

        Parameters
        ----------
        profession : str
            Clé dans PROFESSIONS : ``medecin``, ``dentiste``, ``infirmier``,
            ``kine``, ``sage_femme``.
        """
        col = _QUINTILE_COLS.get(profession)
        if col is None or col not in self._communes_loaded.columns:
            return float("nan")
        df = self._communes_loaded
        valides = df[col].notna()
        if valides.sum() == 0:
            return float("nan")
        poids = df.loc[valides, "population"]
        vals  = df.loc[valides, col]
        return float(np.average(vals, weights=poids))

    def repartition_quintiles(self, theme: str) -> dict[int, int]:
        """Nombre de communes par quintile (clés 1–5) pour une thématique.

        Parameters
        ----------
        theme : str
            Clé thématique : ``score_apl``, ``apl_medecins``, ``apl_dentistes``,
            ``apl_infirmiers``, ``apl_kines``, ``apl_sagefemmes``.
            Utilise ``_THEME_TO_QUINTILE`` pour résoudre la colonne quintile.
        """
        from libapp.config import _THEME_TO_QUINTILE
        col = _THEME_TO_QUINTILE.get(theme)
        if col is None or col not in self._communes_loaded.columns:
            return {}
        return {
            int(k): int(v)
            for k, v in (
                self._communes_loaded[col]
                .value_counts()
                .sort_index()
                .items()
            )
        }

    def score_apl(self) -> float:
        """Score APL synthétique : moyenne pondérée par population de la colonne
        ``score_apl`` du parquet (moyenne pondérée des apl_std par commune).

        Distinct de ``indice_position()`` qui utilise les quintiles.
        """
        return self._moyenne_ponderee("score_apl")

    def score_apl_label(self) -> str:
        """Interprétation qualitative du score APL (z-score centré sur 0)."""
        return _score_apl_label(self.score_apl())

    def perenite_offre(self) -> dict:
        """Indicateurs de pérennité de l'offre médicale.

        Calcule le taux de pérennité (apl_med_60 / apl_medecins) pondéré par
        population, puis assigne un badge via les quintiles nationaux.

        Retourne un dict avec 'taux', 'badge' (et 'quintile' si disponible).
        """
        df = self._communes_loaded
        # Utilise la colonne pré-calculée si disponible (parquet re-exporté)
        if "quintile_perenite_offre" in df.columns:
            indice = self._moyenne_ponderee("quintile_perenite_offre")
            taux   = self._moyenne_ponderee("taux_perenite_offre") \
                     if "taux_perenite_offre" in df.columns else float("nan")
            badge  = _badge_perenite_from_quintile(indice)
            return {"taux": round(taux, 3), "badge": badge, "quintile": round(indice, 2)}

        # Fallback : calcul à la volée depuis apl_med_60 / apl_medecins
        if "apl_med_60" not in df.columns or "apl_medecins" not in df.columns:
            return {}
        valides = df["apl_medecins"].notna() & (df["apl_medecins"] > 0) & df["apl_med_60"].notna()
        if valides.sum() == 0:
            return {}
        poids  = df.loc[valides, "population"]
        taux_c = df.loc[valides, "apl_med_60"] / df.loc[valides, "apl_medecins"]
        taux   = float(np.average(taux_c, weights=poids))
        badge  = _badge_perenite_from_taux(taux)
        return {"taux": round(taux, 3), "badge": badge}

    def badge_perenite(self) -> str:
        """Badge qualitatif de pérennité : Offre résiliente | modérément exposée | fragile."""
        return self.perenite_offre().get("badge", "Inconnu")

    def heterogeneite(self) -> dict:
        """Indicateurs d'hétérogénéité interne du territoire.

        Calculés sur ``quintile_apl_nat`` et ``score_apl``, pondérés par population.
        """
        return calcul_heterogeneite(self._communes_loaded)

    def niveau_offre(self) -> str:
        """Badge de niveau global : Bien pourvu | Sous-doté | Plutôt bien pourvu | Plutôt sous-doté | Mixte."""
        return _niveau_offre(self.heterogeneite())

    def profil_heterogeneite(self) -> str:
        """Badge de distribution spatiale : Polarisé | Homogène | Intermédiaire."""
        return _heterogeneite_spatiale(self.heterogeneite())

    # ── Contexte ──────────────────────────────────────────────────────────

    def densite_dominante(self) -> str:
        """Libellé de densité dominant (pondéré par population)."""
        col = "libelle_densite_7"
        if col not in self._communes_loaded.columns:
            return ""
        s = self._communes_loaded.groupby(col)["population"].sum()
        return str(s.idxmax()) if not s.empty else ""

    def urbanite_score_moyen(self) -> float:
        """Score d'urbanité moyen pondéré par population."""
        return self._moyenne_ponderee("urbanite_score")

    def tps_acces_urgences_moyen(self) -> float:
        """Temps d'accès aux urgences moyen (tps_su_smur), pondéré par population."""
        return self._moyenne_ponderee("tps_su_smur")

    def _moyenne_ponderee(self, col: str) -> float:
        """Moyenne pondérée par population d'une colonne numérique."""
        df = self._communes_loaded
        if col not in df.columns:
            return float("nan")
        valides = df[col].notna()
        if valides.sum() == 0:
            return float("nan")
        poids = df.loc[valides, "population"]
        vals  = df.loc[valides, col]
        return float(np.average(vals, weights=poids))

    # ── Historique & Tendance ─────────────────────────────────────────────

    def historique(self, df_historique: pd.DataFrame) -> pd.DataFrame:
        """Agrège df_historique filtré sur le territoire courant.

        Pondération par pop_std par profession.

        Retourne un DataFrame (annee | apl_medecins | apl_infirmiers | apl_kines | apl_sagefemmes).
        """
        codes = self.codes_communes
        df = df_historique[df_historique["code_commune"].isin(codes)]
        if df.empty:
            return pd.DataFrame(columns=["annee"] + list(_PROFS_HIST))

        rows = []
        for annee, g in df.groupby("annee"):
            row: dict = {"annee": int(annee)}
            for apl_col, pop_col in _PROFS_HIST.items():
                valides = g[apl_col].notna() & g[pop_col].notna()
                if valides.sum() == 0:
                    row[apl_col] = float("nan")
                else:
                    row[apl_col] = float(
                        np.average(g.loc[valides, apl_col], weights=g.loc[valides, pop_col])
                    )
            if "population" in g.columns:
                row["population"] = int(g["population"].sum())
            rows.append(row)
        return pd.DataFrame(rows).sort_values("annee").reset_index(drop=True)

    def tendance(self, df_historique: pd.DataFrame) -> dict:
        """Calcule la tendance APL 2017→2023 agrégée pour le territoire.

        Retourne un dict par profession + clé 'synthese'.
        """
        hist = self.historique(df_historique)
        if hist.empty or len(hist) < 2:
            return {}

        annees     = sorted(hist["annee"].tolist())
        annee_deb  = annees[0]
        annee_fin  = annees[-1]
        idx        = hist.set_index("annee")
        v_deb      = idx.loc[annee_deb]
        v_fin      = idx.loc[annee_fin]

        result: dict = {}
        for prof in ["medecins", "infirmiers", "kines", "sagefemmes"]:
            col  = f"apl_{prof}"
            a0   = v_deb.get(col, float("nan"))
            a1   = v_fin.get(col, float("nan"))

            if np.isnan(a0) or np.isnan(a1):
                result[prof] = {"variation_brute": None, "variation_pct": None, "tendance": "Inconnu"}
                continue

            var_brute = a1 - a0
            var_pct   = (a1 - a0) / a0 if a0 != 0 else float("nan")

            if   np.isnan(var_pct):                     tend = "Inconnu"
            elif var_pct > TENDANCE_NATIONALE + MARGE:  tend = "amélioration"
            elif var_pct < TENDANCE_NATIONALE - MARGE:  tend = "dégradation"
            else:                                        tend = "stable"

            prof_res: dict = {
                "variation_brute": round(float(var_brute), 3),
                "variation_pct":   round(float(var_pct), 3) if not np.isnan(var_pct) else None,
                "tendance":        tend,
            }

            if prof == "medecins":
                seuil  = APL_SEUILS.get("apl_medecins", 2.5)
                codes  = self.codes_communes
                df_c   = df_historique[df_historique["code_commune"].isin(codes)]
                df_fin = df_c[df_c["annee"] == annee_fin][["code_commune", "apl_medecins"]].rename(
                    columns={"apl_medecins": "apl_fin"})
                df_deb = df_c[df_c["annee"] == annee_deb][["code_commune", "apl_medecins"]].rename(
                    columns={"apl_medecins": "apl_deb"})
                df_al  = df_fin.merge(df_deb, on="code_commune", how="inner")
                df_al  = df_al.merge(
                    self._communes_loaded[["code_insee", "population"]].rename(
                        columns={"code_insee": "code_commune"}),
                    on="code_commune", how="left"
                )
                df_al  = df_al[df_al["apl_fin"].notna() & df_al["apl_deb"].notna()]
                df_al["var_pct_c"] = (
                    (df_al["apl_fin"] - df_al["apl_deb"])
                    / df_al["apl_deb"].replace(0, float("nan"))
                )
                mask        = (df_al["apl_fin"] > seuil) & (df_al["var_pct_c"] < TENDANCE_NATIONALE - MARGE)
                pop_alerte  = float(df_al.loc[mask, "population"].fillna(0).sum())
                pop_total   = float(df_al["population"].fillna(0).sum())
                prof_res["nb_communes_alerte"] = int(mask.sum())
                prof_res["part_pop_alerte"]    = round(pop_alerte / pop_total, 3) if pop_total > 0 else 0.0

            result[prof] = prof_res

        # Variations par profession (dict sans les None)
        variations = {
            p: result[p]["variation_pct"]
            for p in ["medecins", "infirmiers", "kines", "sagefemmes"]
            if result.get(p, {}).get("variation_pct") is not None
        }

        # Population : variation brute
        var_pop_pct   = None
        var_pop_brute = None
        if "population" in idx.columns:
            try:
                pop_deb = float(v_deb.get("population"))
                pop_fin = float(v_fin.get("population"))
            except (TypeError, ValueError):
                pop_deb = pop_fin = float("nan")
            if not np.isnan(pop_deb) and pop_deb != 0 and not np.isnan(pop_fin):
                var_pop_brute = pop_fin - pop_deb
                var_pop_pct   = var_pop_brute / pop_deb

        # ── Synthèse — 5 règles prioritaires ─────────────────────────────────
        if not variations:
            synthese = "Inconnu"

        # Règle 1 : pop en hausse + ≥2 professions qui baissent → dégradation certaine
        elif (var_pop_pct is not None
              and var_pop_pct > SEUIL_POP_HAUSSE
              and sum(1 for vp in variations.values() if vp < 0) >= 2):
            synthese = "dégradation"

        # Règle 2 : ≥2 professions sous le seuil de dégradation
        elif sum(1 for vp in variations.values() if vp < SEUIL_DEGRADATION) >= 2:
            synthese = "dégradation"

        # Règle 3 : ≥3 professions au-dessus du seuil d'amélioration + pop pas en forte hausse
        elif (sum(1 for vp in variations.values() if vp > SEUIL_AMELIORATION) >= 3
              and (var_pop_pct is None or var_pop_pct <= SEUIL_POP_HAUSSE)):
            synthese = "amélioration"

        # Règle 4 : toutes les variations dans la bande [-11%, +5%]
        elif all(SEUIL_DEGRADATION <= vp <= 0.05 for vp in variations.values()):
            synthese = "stable"

        # Règle 5 : profil contradictoire
        else:
            synthese = "situation mixte"

        result["synthese"] = synthese

        if var_pop_pct is not None:
            result["population"] = {
                "variation_brute": int(var_pop_brute),
                "variation_pct":   round(float(var_pop_pct), 3),
            }

        return result

    def to_historique(self, df_historique: pd.DataFrame) -> dict:
        """Sérialisation JSON de historique() pour l'API."""
        hist = self.historique(df_historique)
        series = [
            {
                "annee":          int(row["annee"]),
                "apl_medecins":   _safe_float(row.get("apl_medecins")),
                "apl_infirmiers": _safe_float(row.get("apl_infirmiers")),
                "apl_kines":      _safe_float(row.get("apl_kines")),
                "apl_sagefemmes": _safe_float(row.get("apl_sagefemmes")),
                "population":     int(row["population"]) if not pd.isna(row.get("population")) else None,
            }
            for _, row in hist.iterrows()
        ]
        return {
            "territoire": {"type": self.type, "code": self.code, "nom": self.nom},
            "series": series,
        }

    # ── Export ────────────────────────────────────────────────────────────

    @staticmethod
    def _clean(obj):
        """Remplace récursivement NaN/inf par None pour la sérialisation JSON."""
        if isinstance(obj, float):
            return None if (obj != obj or obj == float('inf') or obj == float('-inf')) else obj
        if isinstance(obj, dict):
            return {k: Territoire._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [Territoire._clean(v) for v in obj]
        return obj

    def to_summary(self, df_historique: pd.DataFrame | None = None) -> dict:
        """Synthèse pour l'endpoint /summary et le LLM."""
        indices = {p: round(self.indice_position(p), 2) for p in PROFESSIONS}
        result = {
            "type":               self.type,
            "code":               self.code,
            "nom":                self.nom,
            "population":         self.population,
            "nb_communes":        self.nb_communes,
            "score_apl":          round(self.score_apl(), 2),
            "score_apl_label":    self.score_apl_label(),
            "indice_position":    indices,
            "indice_position_labels": _labels_from_indices(indices),
            "densite_dominante":  self.densite_dominante(),
            "urbanite_score":     round(self.urbanite_score_moyen(), 2),
            "centroide_lat":      self.centroide_lat,
            "centroide_lon":      self.centroide_lon,
            "codes_departements": self.codes_departements,
            "codes_regions":      self.codes_regions,
            "profil_heterogeneite": self.profil_heterogeneite(),
            "niveau_offre":         self.niveau_offre(),
            "heterogeneite":        self.heterogeneite(),
            "perenite_offre":       self.perenite_offre(),
        }
        if df_historique is not None:
            t = self.tendance(df_historique)
            for prof in ("medecins", "infirmiers", "kines", "sagefemmes"):
                p = t.get(prof, {})
                result[f"tendance_{prof}"] = {
                    "variation_pct": p.get("variation_pct"),
                    "tendance":      p.get("tendance"),
                }
            pop = t.get("population", {})
            if pop:
                result["tendance_population"] = {"variation_pct": pop.get("variation_pct")}
            result["tendance_synthese"] = t.get("synthese")
        return self._clean(result)

    def to_indicators(self, df_historique: pd.DataFrame | None = None) -> dict:
        """Tous les indicateurs numériques pour l'endpoint /indicators et Streamlit."""
        apl_moyens     = utils.calculer_apl_moyens(self._communes_loaded, APL_COLS)
        apl_std_moyens = utils.calculer_apl_moyens(self._communes_loaded, APL_STD_COLS)

        # 1. cv_apl négatif → null
        het = self.heterogeneite()
        if het and isinstance(het.get("cv_apl"), (int, float)) and het["cv_apl"] < 0:
            het = {**het, "cv_apl": None}

        result = {
            **self.to_summary(),
            "repartition_quintiles": {
                theme: self.repartition_quintiles(theme)
                for theme in ("score_apl", "apl_medecins", "apl_dentistes",
                              "apl_infirmiers", "apl_kines", "apl_sagefemmes")
            },
            "apl_moyens":            apl_moyens,
            "apl_std_moyens":        apl_std_moyens,
            "tps_acces_urgences":    round(self.tps_acces_urgences_moyen(), 1),
            "codes_communes":        self.codes_communes,
            "codes_epci":            self.codes_epci,
            "heterogeneite":         het,
        }

        # 2. Contexte pérennité : offre fragile sur territoire déjà sous-doté
        per = self.perenite_offre()
        taux_per = per.get("taux")
        indice_med = self.indice_position("medecin")
        if (taux_per is not None and not np.isnan(taux_per) and taux_per < 0.80
                and not np.isnan(indice_med) and indice_med <= 2):
            result["perenite_contexte"] = "Offre fragile sur territoire déjà sous-doté"

        # 3. Tendances historiques
        if df_historique is not None:
            t = self.tendance(df_historique)
            for prof in ("medecins", "infirmiers", "kines", "sagefemmes"):
                p = t.get(prof, {})
                result[f"tendance_{prof}"] = {
                    "variation_pct": p.get("variation_pct"),
                    "tendance":      p.get("tendance"),
                }
            pop = t.get("population", {})
            if pop:
                result["tendance_population"] = {"variation_pct": pop.get("variation_pct")}
            result["tendance_synthese"] = t.get("synthese")
            result["historique"]        = self.to_historique(df_historique).get("series", [])
        return result

    def to_prompt(self, df_historique: pd.DataFrame | None = None) -> str:
        """Texte structuré pour le LLM (contexte d'analyse)."""
        score = self.score_apl()
        score_str = f"{score:.2f}" if not np.isnan(score) else "n/a"

        lignes_prof = []
        for profession in PROFESSIONS:
            ip = self.indice_position(profession)
            if not np.isnan(ip):
                label = QUINTILE_LABELS.get(max(1, min(5, round(ip))), "Inconnu")
                lignes_prof.append(f"  - {profession}: indice {ip:.2f} ({label})")
            else:
                lignes_prof.append(f"  - {profession}: données indisponibles")

        h = self.heterogeneite()
        if h:
            nb_q1    = h.get('nb_communes_q1', 0)
            nb_q5    = h.get('nb_communes_q5', 0)
            nb_total = h.get('nb_communes_total', 1)
            pct_comm_q1 = nb_q1 / nb_total * 100 if nb_total else 0
            pct_comm_q5 = nb_q5 / nb_total * 100 if nb_total else 0
            het_str = (
                f"distribution {self.profil_heterogeneite()}, niveau {self.niveau_offre()}, "
                f"{nb_q1} communes en Q1 ({pct_comm_q1:.0f}% des communes) "
                f"mais {h.get('part_pop_q1', 0)*100:.0f}% de la population ; "
                f"{nb_q5} communes en Q5 ({pct_comm_q5:.0f}% des communes) "
                f"mais {h.get('part_pop_q5', 0)*100:.0f}% de la population ; "
                f"CV={h.get('cv_apl', float('nan')):.2f}"
            )
        else:
            het_str = "données indisponibles"
        p = self.perenite_offre()
        if p:
            taux_pct = f"{p['taux']*100:.1f}%" if not np.isnan(p.get("taux", float("nan"))) else "n/a"
            per_str = f"{p['badge']} — taux pérennité {taux_pct}"
            q_apl = self._moyenne_ponderee("quintile_apl_nat")
            note = note_croisee_perenite(p.get("taux"), q_apl)
            if note:
                per_str += f" — ⚠️ {note}"
        else:
            per_str = "données indisponibles"
        hist_para = ""
        if df_historique is not None:
            hist = self.historique(df_historique)
            if not hist.empty and len(hist) >= 2:
                annees   = sorted(hist["annee"].tolist())
                t        = self.tendance(df_historique)
                synthese = t.get("synthese", "Inconnu")

                prof_labels = {
                    "medecins":   "Médecins",
                    "infirmiers": "Infirmiers",
                    "kines":      "Kinés",
                    "sagefemmes": "Sages-femmes",
                }
                lignes_tend = []
                for prof, label in prof_labels.items():
                    p       = t.get(prof, {})
                    var_pct = p.get("variation_pct")
                    tendance = p.get("tendance", "Inconnu")
                    if var_pct is not None:
                        lignes_tend.append(f"  - {label} : {var_pct*100:+.1f}% ({tendance})")
                    else:
                        lignes_tend.append(f"  - {label} : données indisponibles")

                hist_para = (
                    f"\nEntre {annees[0]} et {annees[-1]}, l'accès aux soins a évolué"
                    f" de manière {synthese}.\n"
                    + "\n".join(lignes_tend)
                )

                pop_data    = t.get("population", {})
                var_pop_pct = pop_data.get("variation_pct")
                if var_pop_pct is not None:
                    direction = "augmenté" if var_pop_pct > 0 else "diminué"
                    hist_para += (
                        f"\nLa population a {direction} de {abs(var_pop_pct)*100:.1f}%"
                        f" sur la même période."
                    )
                    if var_pop_pct > SEUIL_POP_HAUSSE and synthese in ("dégradation", "situation mixte"):
                        hist_para += (
                            "\nLa croissance démographique n'a pas été compensée"
                            " par l'offre de soins."
                        )

        return (
            f"Territoire : {self.nom} ({self.type})\n"
            f"Population : {self.population:,} habitants, {self.nb_communes} communes\n"
            f"Score APL global : {score_str} — {self.score_apl_label()}\n"
            f"Densité dominante : {self.densite_dominante()}\n"
            f"Départements : {', '.join(self.codes_departements) or 'n/a'}\n"
            f"Hétérogénéité interne : {het_str}\n"
            f"Pérennité de l'offre médicale : {per_str}\n"
            f"Indicateurs par profession :\n"
            + "\n".join(lignes_prof)
            + hist_para
        )

    # ── Compatibilité Streamlit existant ──────────────────────────────────

    def vers_resultats(self) -> dict:
        """Sérialise vers le dict ``resultats`` attendu par les onglets Streamlit."""
        indices      = {p: self.indice_position(p) for p in PROFESSIONS}
        type_interne = _TYPE_TO_INTERNAL.get(self.type, self.type)

        return {
            "communes_terr":          self._communes_loaded,
            "commune_centre":         self._centre,
            "apl_global":             utils.calculer_score_apl(self._communes_loaded),
            "apl_moyens":             utils.calculer_apl_moyens(self._communes_loaded, APL_COLS),
            "indice_position":        indices,
            "indice_position_labels": _labels_from_indices(indices),
            "population_totale":      self.population,
            "nb_communes":            self.nb_communes,
            "rayon_km":               self.rayon if self.type == "commune" else None,
            "territoire_label":       self._label,
            "type_terr":              type_interne,
            "code_sel":               self.code,
        }

    @property
    def _label(self) -> str:
        type_label = _TYPE_LABELS.get(self.type, self.type)
        return f"{type_label} {self.nom} ({self.code})"

    # ── Représentation ────────────────────────────────────────────────────

    def __str__(self) -> str:
        if self._communes is None:
            return f"{self._label} (non calculé)"
        score = self.score_apl()
        score_str = f"{score:.2f}" if not np.isnan(score) else "n/a"
        rayon_str = f" — rayon {self.rayon} km" if self.type == "commune" and self.rayon else ""
        return (
            f"{self._label}{rayon_str}"
            f" — {self.nb_communes} {'commune' if self.nb_communes == 1 else 'communes'}"
            f", {self.population:,} hab."
            f", APL = {score_str} ({self.score_apl_label()})"
        )

    def __repr__(self) -> str:
        return (
            f"Territoire(type={self.type!r}, code={self.code!r},"
            f" rayon={self.rayon}, calcule={self._communes is not None})"
        )


# ─── Utilitaires ─────────────────────────────────────────────────────────────

def _safe_float(v) -> float | None:
    """Convertit une valeur en float arrondi, None si NaN/invalide."""
    if v is None:
        return None
    try:
        f = float(v)
        return round(f, 3) if not np.isnan(f) else None
    except (TypeError, ValueError):
        return None


def _labels_from_indices(indices: dict) -> dict:
    """Convertit un dict d'indices (float 1-5) en labels QUINTILE_LABELS."""
    result = {}
    for prof, v in indices.items():
        try:
            result[prof] = QUINTILE_LABELS[max(1, min(5, round(float(v))))]
        except (TypeError, ValueError):
            result[prof] = "N/A"
    return result


def calcul_heterogeneite(df: pd.DataFrame) -> dict:
    """Calcule les indicateurs d'hétérogénéité depuis un DataFrame de communes.

    Colonnes requises : ``quintile_apl_nat``, ``score_apl``, ``population``.
    """
    pop_total = df["population"].sum()
    if pop_total == 0:
        return {}

    q_col  = "quintile_apl_nat"
    apl_col = "score_apl"
    if q_col not in df.columns or apl_col not in df.columns:
        return {}

    q = df[q_col]
    part_pop_q1 = float(df[q == 1]["population"].sum() / pop_total)
    part_pop_q5 = float(df[q == 5]["population"].sum() / pop_total)

    pop_q1q2 = df[q.isin([1, 2])]["population"].sum()
    pop_q4q5 = df[q.isin([4, 5])]["population"].sum()
    ratio_polarisation = float(pop_q1q2 / pop_q4q5) if pop_q4q5 > 0 else None

    valides = df[apl_col].notna()
    if valides.sum() > 0:
        w = df.loc[valides, "population"]
        v = df.loc[valides, apl_col]
        mean_apl = float(np.average(v, weights=w))
        ecart_type_apl = float(np.sqrt(np.average((v - mean_apl) ** 2, weights=w)))
        cv_apl = ecart_type_apl / mean_apl if mean_apl != 0 else None
    else:
        ecart_type_apl = cv_apl = None

    nb_total = int(q.notna().sum())
    part_pop_q1q2 = float(pop_q1q2 / pop_total)
    part_pop_q4q5 = float(pop_q4q5 / pop_total)
    return {
        "part_pop_q1":        round(part_pop_q1, 3),
        "part_pop_q5":        round(part_pop_q5, 3),
        "part_pop_q1q2":      round(part_pop_q1q2, 3),
        "part_pop_q4q5":      round(part_pop_q4q5, 3),
        "nb_communes_q1":     int((q == 1).sum()),
        "nb_communes_q5":     int((q == 5).sum()),
        "nb_communes_total":  nb_total,
        "ratio_polarisation": round(ratio_polarisation, 2) if ratio_polarisation is not None else None,
        "ecart_type_apl":     round(ecart_type_apl, 3) if ecart_type_apl is not None else None,
        "cv_apl":             round(cv_apl, 3) if cv_apl is not None else None,
    }


def _niveau_offre(h: dict) -> str:
    """Badge de niveau global d'offre, pondéré par population.

    Répond à : "Le territoire est-il globalement bien ou mal servi ?"

    Règles (par ordre de priorité) :
    1. Bien pourvu          — Q4+Q5 ≥ 60% de la population
    2. Sous-doté            — Q1+Q2 ≥ 60% de la population
    3. Plutôt bien pourvu   — Q4+Q5 ≥ 45%
    4. Plutôt sous-doté     — Q1+Q2 ≥ 45%
    5. Mixte                — sinon
    """
    q1q2 = h.get("part_pop_q1q2")
    q4q5 = h.get("part_pop_q4q5")
    if q1q2 is None or q4q5 is None:
        q1q2 = h.get("part_pop_q1", 0) or 0
        q4q5 = h.get("part_pop_q5", 0) or 0
        if q1q2 is None or q4q5 is None:
            return "Inconnu"
    if q4q5 >= 0.60:
        return "Bien pourvu"
    if q1q2 >= 0.60:
        return "Sous-doté"
    if q4q5 >= 0.45:
        return "Plutôt bien pourvu"
    if q1q2 >= 0.45:
        return "Plutôt sous-doté"
    return "Mixte"


def _heterogeneite_spatiale(h: dict) -> str:
    """Badge de distribution spatiale de l'offre, pondéré par population.

    Répond à : "La population est-elle concentrée sur un extrême, dispersée entre les deux, ou étalée ?"

    Utilise les quintiles individuels Q1 et Q5 (pas Q1+Q2 / Q4+Q5) pour détecter
    la concentration sur le quintile le plus extrême.

    Règles (par ordre de priorité) :
    1. Concentré Q5   — part_pop_q5 ≥ 50% : masse écrasante au meilleur quintile
    2. Concentré Q1   — part_pop_q1 ≥ 50% : masse écrasante au pire quintile
    3. Polarisé       — part_pop_q1 ≥ 20% ET part_pop_q5 ≥ 20% : coexistence réelle des extrêmes
    4. Homogène       — part_pop_q1 < 15% ET part_pop_q5 < 35% : pas de domination des extrêmes
    5. Intermédiaire  — sinon
    """
    q1 = h.get("part_pop_q1")
    q5 = h.get("part_pop_q5")
    if q1 is None or q5 is None:
        return "Inconnu"
    if q5 >= 0.50:
        return "Concentré Q5"
    if q1 >= 0.50:
        return "Concentré Q1"
    if q1 >= 0.20 and q5 >= 0.20:
        return "Polarisé"
    if q1 < 0.15 and q5 < 0.35:
        return "Homogène"
    return "Intermédiaire"


def _profil_heterogeneite(h: dict) -> str:
    """Compat : retourne '<heterogeneite_spatiale> / <niveau_offre>'."""
    return f"{_heterogeneite_spatiale(h)} / {_niveau_offre(h)}"


# Seuils des quintiles nationaux de taux_perenite_offre (apl_med_60 / apl_medecins)
# Calculés sur mart_sante_comm_indic national (34 922 communes)
_PERENITE_Q_THRESHOLDS = (0.574, 0.682, 0.760, 0.841)  # Q1/Q2, Q2/Q3, Q3/Q4, Q4/Q5


def _badge_perenite_from_taux(taux: float) -> str:
    if np.isnan(taux):
        return "Inconnu"
    q2, q3 = _PERENITE_Q_THRESHOLDS[1], _PERENITE_Q_THRESHOLDS[2]
    if taux >= q3:
        return "Offre résiliente"
    if taux >= q2:
        return "Offre modérément exposée"
    return "Offre fragile"


def _badge_perenite_from_quintile(indice: float) -> str:
    """Badge depuis l'indice moyen de quintile (1–5)."""
    if np.isnan(indice):
        return "Inconnu"
    if indice >= 3.5:
        return "Offre résiliente"
    if indice >= 2.5:
        return "Offre modérément exposée"
    return "Offre fragile"


def note_croisee_perenite(taux: float, quintile_apl_moyen: float) -> str | None:
    """Retourne un message contextuel si taux de pérennité et niveau APL sont contradictoires.

    - taux : taux de pérennité (0–1)
    - quintile_apl_moyen : quintile APL moyen pondéré (1–5)
    Retourne None si pas de contradiction notable.
    """
    if taux is None or quintile_apl_moyen is None:
        return None
    try:
        taux = float(taux)
        q = float(quintile_apl_moyen)
    except (TypeError, ValueError):
        return None
    if np.isnan(taux) or np.isnan(q):
        return None
    if taux < 0.80 and q >= 4.5:
        return (
            "Malgré un taux de pérennité fragile, le niveau d'offre actuel est très élevé — "
            "le territoire resterait probablement bien pourvu même en cas de départs significatifs."
        )
    if taux >= 0.80 and q <= 2.0:
        return (
            "Malgré une offre stable en termes de pérennité, le niveau d'accès aux médecins reste faible — "
            "la résilience de l'offre ne compense pas la sous-dotation structurelle du territoire."
        )
    return None


def _score_apl_label(score: float) -> str:
    """Interprétation qualitative du score APL (z-score centré sur 0).

    Seuils alignés avec _niveau_apl() de widgets.py.
    """
    if np.isnan(score):  return "Inconnu"
    if score >= 0.5:     return "Bonne accessibilité aux soins"
    if score >= 0:       return "Accessibilité correcte mais fragile"
    if score >= -0.5:    return "Accessibilité à améliorer"
    return               "Accessibilité aux soins insuffisante"
