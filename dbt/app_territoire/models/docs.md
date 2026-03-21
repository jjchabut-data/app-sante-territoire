{% docs code_commune %}
Code INSEE de la commune (5 caractères, string).
Clé primaire des tables communes.
{% enddocs %}

{% docs nom_commune %}
Nom officiel de la commune (COG INSEE 2026).
{% enddocs %}

{% docs population %}
Population municipale de la commune (recensement INSEE).
{% enddocs %}

{% docs code_epci %}
Code SIREN de l'EPCI d'appartenance.
Peut contenir plusieurs codes séparés par '/' si la commune appartient à plusieurs EPCI.
{% enddocs %}

{% docs code_departement %}
Code INSEE du département (2 caractères pour métropole, 3 pour DOM).
{% enddocs %}

{% docs code_region %}
Code INSEE de la région (2 caractères).
{% enddocs %}

{% docs lon %}
Longitude du centroïde (WGS84).
{% enddocs %}

{% docs lat %}
Latitude du centroïde (WGS84).
{% enddocs %}

{% docs quintile_apl %}
Quintile national APL (1 à 5).
Calculé sur toutes les communes de France pour l'année de référence.
1 = 20% les moins dotés / 5 = 20% les mieux dotés.
{% enddocs %}

{% docs quintile_label_apl %}
Label du quintile national APL.
Valeurs : 'très faible' | 'faible' | 'moyen' | 'élevé' | 'très élevé'.
{% enddocs %}

{% docs apl_std %}
Version standardisée (z-score) de l'APL correspondant.
Centré sur la moyenne nationale, réduit par l'écart-type national.
Valeur positive = mieux doté que la moyenne nationale.
Valeur négative = moins bien doté que la moyenne nationale.
{% enddocs %}