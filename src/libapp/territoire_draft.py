class Indicateur:
    def __init__(
        self,
        nom,
        valeur,
        sens="positif",  # "positif" = + = favorable
        unite=None,
        description=None,
        source=None
    ):
        self.nom = nom
        self.valeur = valeur
        self.sens = sens
        self.unite = unite
        self.description = description
        self.source = source

    def interpretation(self):
        """Retourne une interprétation simple"""
        if self.valeur is None:
            return "non disponible"

        if self.sens == "positif":
            return "favorable" if self.valeur > 0 else "défavorable"
        else:
            return "défavorable" if self.valeur > 0 else "favorable"

class Territoire:
    def __init__(self, nom, type_territoire, code):
        self.nom = nom
        self.type = type_territoire
        self.code = code

        self.population = None

        self.departement = None
        self.region = None
        self.epcis = None
        self.longitude = None
        self.latitude = None

        self.indicateurs = {}

    def add_indicateur(self, domaine, indicateur: Indicateur):
        if domaine not in self.indicateurs:
            self.indicateurs[domaine] = {}

        self.indicateurs[domaine][indicateur.nom] = indicateur

    def get_indicateur(self, domaine, nom):
        return self.indicateurs.get(domaine, {}).get(nom)

    @property
    def offre_soins(self):
        ind = self.get_indicateur("sante", "offre_soins")
        return ind.valeur if ind else None

    def resume(self):
        result = {}

        for domaine, indicateurs in self.indicateurs.items():
            result[domaine] = {
                nom: ind.valeur for nom, ind in indicateurs.items()
            }

        return {
            "nom": self.nom,
            "type": self.type,
            "population": self.population,
            "indicateurs": result
        }

    def score_global(self):
        valeurs = []

        for indicateurs in self.indicateurs.values():
            for ind in indicateurs.values():
                if ind.valeur is not None:
                    valeurs.append(ind.valeur)

        if not valeurs:
            return None

        return sum(valeurs) / len(valeurs)

    def compare(self, autre):
        comparaison = {}

        for domaine, indicateurs in self.indicateurs.items():
            comparaison[domaine] = {}

            for nom, ind in indicateurs.items():
                autre_ind = autre.get_indicateur(domaine, nom)

                if autre_ind:
                    comparaison[domaine][nom] = {
                        "self": ind.valeur,
                        "autre": autre_ind.valeur,
                        "diff": ind.valeur - autre_ind.valeur
                    }

        return comparaison