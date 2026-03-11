# Spécifications fonctionnelles — Territoire Santé (V1 clarifiée)

## 1. Domaine

Le domaine correspond au **champ thématique d’analyse**.

Dans la version actuelle :

Domaine : Santé

Extensions possibles à terme :

- Environnement
- Emploi
- Démographie

Le domaine constitue le **premier niveau d’organisation de l’analyse**.

Structure cible :

Domaine  
↓  
Axes d’analyse  
↓  
Indicateurs  

Dans la V1 :

- domaine = Santé
- la structure doit rester **générique** afin de permettre l’ajout futur d’autres domaines.

---

# 2. Axe d’analyse

L’axe d’analyse correspond à **la question analytique posée au territoire**.

Structure cible :

Axe d’analyse  
↓  
Indicateur principal  
↓  
Visualisations associées  

Axes prévus pour le domaine Santé :

- Offre de soins
- Besoins socio-sanitaires (non implémenté dans la V1)

Dans la version actuelle :

Axe actif :

Offre de soins

Les autres axes restent **préparés conceptuellement mais non activés dans l’interface**.

---

# 3. Territoire

Le territoire correspond à **l’unité géographique analysée**.

Types conservés dans la V1 :

- Commune
- EPCI
- Département
- Région
- Rayon autour d’une commune

Le territoire sélectionné détermine :

- le périmètre d’analyse
- l’agrégation des indicateurs
- l’affichage cartographique

Informations affichées dans l’entête :

- Nom du territoire
- Nombre de communes
- Population

Exemple :

Puy-de-Dôme  
463 communes  
664 385 habitants

---

# 4. Données d’entête

L’entête présente **le diagnostic synthétique du territoire selon l’axe actif**.

Structure :

Territoire  
↓  
Axe d’analyse  
↓  
Interprétation  
↓  
Indicateur principal  

Exemple :

Puy-de-Dôme (63)  
463 communes · 664 385 habitants  

Offre de soins  
Bonne accessibilité aux soins  

Score APL : 0.84

Principes :

- une seule **lecture principale**
- les scores restent **secondaires par rapport à l’interprétation**
- les indicateurs composites non stabilisés ne sont pas affichés.

---

# 5. Radar

Le radar permet de **décomposer l’indicateur principal de l’axe actif**.

Dans l’axe Offre de soins :

Variables utilisées :

- APL médecins
- APL dentistes
- APL infirmiers
- APL kinésithérapeutes
- APL sages-femmes

Objectifs :

- montrer la structure de l’offre de soins
- expliquer le score global APL

Règle :

Radar affiché uniquement pour l’axe Offre de soins (ce qui est l'axe unique pour le moment).

---

# 6. Carte

La carte représente **la distribution territoriale d’un indicateur sélectionné**.

Dans la version actuelle, la variable cartographiée est choisie via le sélecteur :

Thématique carte

Variables disponibles :

- Offre de soins (score APL)
- APL médecins
- APL dentistes
- APL infirmiers
- APL kinésithérapeutes
- APL sages-femmes
- Cluster territorial

Le sélecteur contrôle :

- la variable cartographiée
- la coloration
- les informations de l’infobulle

Infobulle :

- Nom de la commune
- Valeur de l’indicateur
- catégorie éventuelle

---

# 7. Clustering

Le clustering constitue **une analyse territoriale complémentaire**, et non un axe d’analyse.

Objectif :

Identifier des **typologies de territoires** selon leurs caractéristiques.

Utilisation :

- coloration cartographique possible
- page ou analyse dédiée

Le clustering ne pilote pas :

- l’entête
- le radar
- la structure principale de l’analyse.

---

# 8. Organisation de l’interface

## Sidebar

- Domaine
- Territoire
- Thématique carte

## Zone principale

- Entête diagnostic
- Radar (si axe Offre de soins)
- Carte
- Visualisations complémentaires

---

# 9. Indicateurs expérimentaux

Certains indicateurs restent présents dans le pipeline mais **non affichés dans l’interface**.

Exemple :

score composite de type IRDES

Raison :

- méthodologie à clarifier
- interprétation à stabiliser
- éviter les frictions cognitives.

Ces indicateurs pourront être réintroduits ultérieurement sous forme :

- d’indice synthétique
- ou d’analyse complémentaire.

---

# 10. Principe directeur

L’application doit permettre :

Diagnostic territorial rapide  
↓  
Compréhension des déterminants  
↓  
Exploration des disparités territoriales

La V1 se concentre volontairement sur **un périmètre analytique restreint (offre de soins)** afin de garantir :

- cohérence méthodologique
- lisibilité de l’interface
- robustesse des indicateurs.