{% docs mart_apl_commune %}
Table finale APL par commune — millésime contrôlé par la variable dbt `annee_apl`.
Une ligne par commune avec les APL bruts, standardisés, quintiles et score synthétique
pour les 5 professions de santé.
Consommée par l'application Streamlit d'analyse territoriale.
{% enddocs %}

{% docs apl_medecins %}
APL aux médecins généralistes — nombre moyen de consultations accessibles par habitant par an.
Source : DREES / data.ameli.fr, millésime 2023.
{% enddocs %}

{% docs apl_med_65 %}
APL aux médecins généralistes de 65 ans et moins.
Indicateur de tension future sur l'offre de soins (départs en retraite).
{% enddocs %}

{% docs apl_med_62 %}
APL aux médecins généralistes de 62 ans et moins.
{% enddocs %}

{% docs apl_med_60 %}
APL aux médecins généralistes de 60 ans et moins.
{% enddocs %}

{% docs apl_dentistes %}
APL aux chirurgiens-dentistes — nombre moyen de consultations accessibles par habitant par an.
Source : DREES / data.ameli.fr, millésime 2023.
{% enddocs %}

{% docs apl_infirmiers %}
APL aux infirmiers — nombre moyen de consultations accessibles par habitant par an.
Source : DREES / data.ameli.fr, millésime 2023.
{% enddocs %}

{% docs apl_kines %}
APL aux masseurs-kinésithérapeutes — nombre moyen de consultations accessibles par habitant par an.
Source : DREES / data.ameli.fr, millésime 2023.
{% enddocs %}

{% docs apl_sagefemmes %}
APL aux sages-femmes — nombre moyen de consultations accessibles par habitant par an.
Source : DREES / data.ameli.fr, millésime 2023.
{% enddocs %}

{% docs score_apl %}
Score APL synthétique — moyenne pondérée des APL standardisés par profession.
Pondération : médecins 35% | infirmiers 25% | kinés 20% | dentistes 15% | sages-femmes 5%.
{% enddocs %}

{% docs score_apl_std %}
Version standardisée (z-score) du score APL synthétique.
Permet de comparer le niveau global d'accès aux soins entre communes.
{% enddocs %}