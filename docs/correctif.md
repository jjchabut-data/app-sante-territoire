Page diagnostic:

1 - Renommer les tab1, tab5, tab2, tab3, tab4 car leurs noms ne permettent plus l'ordre des onglets

2 - Le code commence à être long. Modulariser chaque tab en créant un fichier dans libapp pour chaque tab du  même nom que le nouveau nom technique des tabs.
Si nécessaire utliser libapp.utils pour les fonctions communes.

3 - Pour l'ancien tab5 (👥 Contexte socio-éco (IRIS))

Les iris contiennent des communes non découpées de type Z et des quartiers urbains type H. load_fdep() les charges tous

Code actuel:
        df_fdep  = load_fdep()
        codes    = communes['code_insee'].tolist()
        iris_sel = load_geom_iris(tuple(sorted(codes)))

Par contre la carte n'affiche que les contours Habitat (type H) pour la selection de communes

load_geom_iris charge  ref_iris_habitat_geom_simplified.parquet qui ne contient que les type H

La geometrie des communes est déjà chargée via load_geom_communes()

il faudrait donc colorier les contours iris et les communes non incluses dans les type H. 
Les infos bulles pour l'ensemble des contours est la même.


