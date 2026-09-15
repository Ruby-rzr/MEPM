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

### Le budget en ULP était réservé à la phase 4

La phase 4 a converti le modèle en SI strict. Cette conversion ne peut pas être
neutre au bit près : `0.45 * 1e-3` ne vaut pas le flottant `0.00045`, donc une
chaîne menée en mètres ne rend pas exactement le même flottant que la même
chaîne menée en millimètres, même quand les millimètres s'annulent
algébriquement. Un budget de **32 ULP par valeur** lui a donc été accordé, sous
le nom `BUDGET_ULP_PHASE_4` dans `tests/contrat_unites.py`, contre 18 ULP
mesurés au pire cas avant la conversion et 9 après.

**Ce budget valait pour la phase 4 et pour elle seule.** Depuis que
`reference_v2_phase4` a été produite et validée, elle est la nouvelle base
d'égalité BIT A BIT. Tout écart ultérieur, dans les phases 5, 6, 7 et 8,
redevient un échec, sauf décision explicite portant sur un défaut nommé.

Raison : si chaque phase apporte sa propre tolérance, la suite ne détecte plus
rien à la phase 8.

Règles de comparaison des flottants, sans tolérance :

- deux NaN sont égaux, quelle que soit leur charge utile,
- un NaN face à un nombre est un échec, dans les deux sens,
- tout le reste est comparé sur les 64 bits bruts, ce qui distingue `+0.0` de
  `-0.0` et `+inf` de `-inf`.

La suite vérifie aussi le sha256 de `materials.xls`. Si la base a changé, le
test d'intégrité échoue avec un message explicite et les cas qui lisent la base
sont ignorés plutôt que comparés à tort.

## Unités

Le modèle travaille en **SI strict** à l'intérieur : m, Pa, s, kg. Les
conversions ont lieu uniquement aux frontières :

| Frontière | Où | Quoi |
|---|---|---|
| saisie | `tools.unites.entrees_vers_si` | la géométrie et la vitesse sont saisies en mm et mm/s |
| affichage | `generateP`, `main.py` | retour aux mm et aux g/s pour la console et les tracés |
| ajustement empirique | `calculatePrequired` | `Q` en mm³/s, convention dans laquelle `R` et `mP` ont été ajustés |

`materials.xls` est déjà en SI et ne demande aucune conversion.

Le facteur `FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE` de `calculatePrequired` n'est
dérivé d'aucune équation physique. Il est solidaire des valeurs de `R` et de
`mP` et ne se modifie pas sans les réajuster. L'hypothèse MPa vers Pa est
cohérente en ordre de grandeur mais **non confirmée**, le script d'ajustement
étant absent du dépôt.

### Le piège de la table de facteurs

`tests/contrat_unites.py` attache un facteur de conversion à chaque champ
enregistré dans les références. Ces facteurs sont attachés à la **grandeur
réellement contenue**, qui ne correspond pas au nom du champ à cause du
défaut #9, le déballage permuté de `generateP` dans `compute_pressures`.

**La correction du défaut #9 et la mise à jour de cette table doivent se faire
dans le même commit.** `tests/test_contrat_unites.py` vérifie à l'exécution que
la correspondance déclarée est bien celle du code, et échoue si l'une bouge
sans l'autre, dans un sens comme dans l'autre.

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
| T5 | passe | continuité conique vers cylindrique, a échoué en xfail de la phase 3 à la phase 5, défaut #8 corrigé |
| T5bis | passe | le rapport conique sur cylindrique vaut 1 sur 27 combinaisons de De, L et v |
| T5ter | passe | continuité exacte pour n = 1, documente pourquoi le défaut #8 a pu survivre |
| T6 | passe | continuité du seuil quand tau_0 tend vers zéro, ne valide rien pour tau_0 supérieur à zéro |

Aucun test n'est actuellement en `xfail`. Les trois qui l'étaient ont été
retournés en même temps que la correction du défaut #8.

`tests/test_avertissements.py` fige de la même façon les `RuntimeWarning` émis
à l'exécution, qui documentent les défauts #11 et #12.

## Deux règles issues d'un incident

Le commit de phase 4 a été poussé incomplet. Un `git checkout -- main.py`, lancé
pour défaire une mutation temporaire, a aussi annulé des modifications non
commitées du même fichier. Le code livré passait alors des millimètres à une
fonction devenue SI, et rendait des NaN sur son chemin d'entrée réel. **La suite
est restée verte**, parce qu'elle emprunte `tests/reference_io.execute` et non
`main.py`.

1. **Jamais de `git checkout --` sur un fichier portant du travail non commité.**
   Utiliser `git stash`, ou une copie temporaire du fichier, et restaurer
   explicitement.

2. **Un oracle valide le chemin qu'il emprunte lui-même.** Toute grandeur
   destinée à une figure d'article doit être produite par un test qui parcourt
   le chemin de production de bout en bout, pas seulement le chemin du harnais
   de test. C'est l'objet de `tests/test_frontiere_saisie.py`, à étendre à
   chaque nouveau chemin de production.

## Modèle rhéologique et mode de calcul

Les deux sont des **champs explicites**, plus jamais devinés.

| Champ | Valeurs | Où |
|---|---|---|
| `modele` | `sisko`, `newtonien`, `loi_de_puissance`, `carreau`, `bingham`, `herschel_bulkley`, `herschel_bulkley_etendu` | `Velocity_driven/modeles.py` |
| `mode` | `analytique`, `empirique` | idem |

La cascade de `if` qui devinait la loi d'après les paramètres nuls survit dans
`deduire_modele_historique`, isolée et réservée à la lecture de l'ancienne base
`materials.xls`. C'est le seul endroit du dépôt où quelque chose est encore
deviné, et il n'a pas vocation à en sortir.

Les deux interrupteurs indépendants `if R != 0` et `if mP != 0` donnaient
quatre combinaisons, dont deux sans aucun sens et silencieuses. Elles lèvent
désormais une erreur : un matériau dont un seul des deux paramètres ajustés est
renseigné est une donnée incomplète, pas un troisième mode de calcul.

### La branche empirique n'est pas publiable

`FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE`, dans `calculatePrequired`, vaut `10**6`
et n'est dérivé d'aucune équation physique. Il est imposé par la convention
d'unités dans laquelle `R` et `mP` ont été ajustés, et il est solidaire de
leurs valeurs. Sa provenance est **perdue** : le script d'ajustement est absent
du dépôt et l'auteur du portage, interrogé, ne la connaît pas.

**Le mode empirique est NON PUBLIABLE en l'état et ne doit alimenter aucune
figure destinée à un article.** Il reste fonctionnel pour la compatibilité avec
les résultats antérieurs, rien de plus. Le mode imprime un avertissement à
l'exécution, conformément à la règle 3.

Le remplacement est prévu en phase 8 : réajustement de `R` et `mP` sur des
pressions mesurées, par un script versionné, en SI. La provenance redevient
alors connue et le facteur disparaît par construction. Un paramètre orphelin ne
se répare pas, il se remplace.

## Les deux bases de matériaux

| Fichier | Rôle | Lu par |
|---|---|---|
| `materials.xls` | **artefact gelé**, ne jamais modifier | `tools/readMaterial.py`, uniquement pour reproduire les références historiques |
| `materiaux.xlsx` | base de travail | `tools/lireMateriaux.py` |

Le sha256 de `materials.xls` est l'ancre d'intégrité de toutes les références de
non-régression. Le modifier invaliderait la référence active et rendrait les
anciennes irreproductibles.

`materiaux.xlsx` corrige les défauts de forme de l'ancienne :

- en-têtes **nommés**, un matériau par ligne, plus de lecture positionnelle
  ni de feuille par matériau. La lecture positionnelle était la cause directe
  du défaut #10,
- un champ `modele` explicite,
- un champ `mode` explicite,
- une colonne `d_<paramètre>` par paramètre. Une incertitude est une propriété
  du matériau et de son ajustement, pas une constante du code. Elles sont
  vides aujourd'hui, donc nulles, faute de connaître les conditions de mesure,
- une colonne `provenance` par matériau et une `provenance_ajustement`.

Elle est produite par `tools/creer_base_materiaux.py`, versionné pour que la
provenance de chaque valeur soit lisible dans le code qui l'a écrite.

**Tous les matériaux y sont en mode analytique.** Les valeurs `mP` et `R`
présentes portent `provenance_ajustement = INCONNUE` et ne sont donc pas
utilisées.
