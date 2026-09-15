# Règles de travail sur le MEPM

## Piège critique : le facteur de Rabinowitsch

Le facteur `(3 + 1/n)/4` est appliqué DEUX FOIS dans la chaîne de calcul
cylindrique, volontairement :
  - une fois sur le taux de cisaillement, dans `calculateSR`
  - une fois sur la résistance hydraulique, dans `calculateReq`

Ce n'est PAS un doublon. La composition des deux redonne exactement la solution
analytique d'une loi de puissance en conduite cylindrique :

    Delta_P = 4 * L * K * gamma_point_vrai^n / D

C'est conforme aux équations 4.2 et 4.4 de la thèse de JF Chauvette (2023).
Supprimer l'une des deux occurrences ne provoque aucune erreur visible et fausse
tous les résultats d'un facteur dépendant de n.

Ne jamais toucher à l'un de ces deux facteurs sans exécuter le test analytique
« loi de puissance en cylindre » immédiatement après.

## Règles non négociables

1. Jamais de modification de la physique et de refactoring de forme dans le même
   commit. Un commit change soit le comportement numérique, soit la lisibilité,
   jamais les deux.
2. Tout commit qui change une valeur numérique de sortie doit le dire explicitement
   dans son message, avec l'ampleur de l'écart.
3. Aucun paramètre d'ajustement silencieux. Tout coefficient qui n'est pas dérivé
   d'une équation physique doit être nommé, documenté, et signalé à l'exécution.
4. Unités SI en interne. Conversion uniquement aux frontières. L'unité de chaque
   argument figure dans la docstring.
5. Aucune valeur numérique en dur dans le code de calcul. Tout vient de la base de
   matériaux ou de la configuration.
6. Ne jamais inventer une équation ni une référence bibliographique. Si une relation
   manque, tu le dis et tu t'arrêtes.
7. Ne jamais supprimer un test pour faire passer une suite au vert.
8. Le code d'origine est de David Brzeski, Jean-François Chauvette et Raphaël Plante.
   Les en-têtes d'auteurs existants sont conservés, les contributions nouvelles sont
   ajoutées, jamais substituées.

## Comment me répondre

- Si tu n'es pas sûr d'une hypothèse physique, tu demandes. Tu ne choisis pas à ma
  place et tu n'écris pas une formule « plausible ».
- Distingue toujours ce qui est démontré, ce qui est vérifié numériquement, et ce
  que tu supposes.
- Pas de préambule, pas de reformulation de ma demande.
- Pour toute comparaison ou état d'avancement, utilise un tableau.
- N'utilise jamais de tirets cadratins, utilise des virgules.

## Lancer la suite de non-régression

Une seule commande, depuis la racine du dépôt :

    python3 -m pytest tests -q

Elle rejoue la référence active et exige une égalité bit à bit sur toutes les
sorties. Durée attendue, de l'ordre de deux secondes. Si elle dépasse la
minute, quelque chose ne va pas et il faut le corriger avant d'aller plus loin.

Dépendances : numpy, pandas, xlrd, matplotlib, openpyxl, pytest.

## Références de non-régression

Une référence n'est jamais écrasée. Les versions vivent dans
`tests/references/` et la version rejouée par la suite est désignée par
`VERSION_ACTIVE` dans `tests/reference_io.py`.

| Action | Commande |
|---|---|
| Produire une nouvelle version | `python3 tests/generate_reference.py reference_v2_phase4` |
| Comparer deux versions | `python3 tests/compare_references.py reference_v1_phase1 reference_v2_phase4` |
| Tableau complet en CSV | ajouter `--csv ecarts.csv` |

Le générateur refuse d'écrire sur un fichier existant. Toute phase qui change
une valeur numérique de sortie produit une nouvelle version, bascule
`VERSION_ACTIVE`, et justifie chaque écart à l'aide du tableau comparatif, pas
du diff JSON.

Règles de comparaison des flottants, sans tolérance :

- deux NaN sont égaux, quelle que soit leur charge utile,
- un NaN face à un nombre est un échec, dans les deux sens,
- tout le reste est comparé sur les 64 bits bruts, ce qui distingue `+0.0` de
  `-0.0` et `+inf` de `-inf`.

La suite vérifie aussi le sha256 de `materials.xls`. Si la base a changé, le
test d'intégrité échoue avec un message explicite et les cas qui lisent la base
sont ignorés plutôt que comparés à tort.

## Tests analytiques et échecs attendus

`tests/test_analytique.py` confronte le modèle à des solutions analytiques
connues. Certains de ses tests échouent volontairement : ils documentent un
défaut identifié, ils ne signalent pas une régression.

Un test dont l'échec est attendu porte `@pytest.mark.xfail(strict=True)` avec
une raison qui nomme le défaut. La suite reste verte. Si le test se met à
passer, par exemple parce que le défaut a été corrigé, pytest le rapporte en
`XPASS(strict)`, donc en échec. Corriger un défaut oblige donc à retirer le
marqueur en connaissance de cause.

| Test | État | Ce qu'il garantit |
|---|---|---|
| T1 | passe | newtonien cylindrique égale Hagen-Poiseuille |
| T2 | passe | loi de puissance cylindrique égale `4LK gamma_w^n/D`, garde-fou du double facteur de Rabinowitsch |
| T3 | passe | exposants d'échelle sur L, K, Q et D |
| T4 | passe | annulation des alpha pour des buses identiques |
| T5 | **xfail** | continuité conique vers cylindrique, défaut #8 |
| T6 | passe | continuité du seuil quand tau_0 tend vers zéro, ne valide rien pour tau_0 supérieur à zéro |

`tests/test_avertissements.py` fige de la même façon les `RuntimeWarning` émis
à l'exécution, qui documentent les défauts #11 et #12.
