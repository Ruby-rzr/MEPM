# État du projet MEPM

Document de reprise. Se lit en trois minutes. Dernière mise à jour : fin de la
phase 6, branche `refonte`.

## Ce qu'était le MEPM à l'arrivée

Un modèle de pression d'extrusion en Direct Ink Writing, écrit en MATLAB par
J.-F. Chauvette et D. Brzeski, porté en Python par R. Plante. Il fonctionnait
en millimètres mélangés à du SI, devinait la loi rhéologique par une cascade de
`if` sur les paramètres nuls, et sa branche conique portait une erreur de
priorité d'opérateurs qui surestimait la pression de 10 à 37 %. La base de
matériaux faisait planter 12 feuilles sur 19. Aucun test, aucune référence.
Les barres d'erreur tracées étaient celles d'une autre grandeur.

## Ce que le harnais garantit, et ce qu'il ne garantit pas

    python3 -m pytest tests -q          # 396 tests, environ 3 secondes

**Il garantit** que toute sortie du modèle est identique **bit à bit** à la
référence active, sur 262 cas couvrant les 7 lois rhéologiques, les deux
géométries, les deux modes et 19 matériaux. Il garantit aussi les solutions
analytiques connues, Hagen-Poiseuille, la loi de puissance en cylindre, les
exposants d'échelle, la continuité conique.

**Il ne garantit pas qu'un chemin non couvert fonctionne.** Un oracle ne valide
que le chemin qu'il emprunte lui-même. En phase 4, la suite est restée **verte**
alors que `main.py` était cassé : elle passe par `tests/reference_io.execute`,
qui fait sa propre conversion d'unités, et non par `main.py`. Le code livré
rendait des NaN sur son point d'entrée réel sans que rien ne le signale.
`tests/test_frontiere_saisie.py` couvre désormais ce chemin. **Tout nouveau
chemin de production doit recevoir le même traitement.**

Deux règles issues de cet incident sont dans CLAUDE.md, dont : jamais de
`git checkout --` sur un fichier portant du travail non commité.

## Les phases

| Phase | Ce qu'elle a produit | Référence |
|---|---|---|
| 0 | `.gitignore`, retrait des `.pyc` versionnés et d'un verrou Office. État initial au SHA `2be69a2` | aucune |
| 1 | Gel de 262 cas de sortie. Extraction de la boucle de calcul de `main.py` dans `compute_pressures`, seule modification autorisée | `reference_v1_phase1` |
| 2 | Suite de non-régression, comparaison bit à bit, script de comparaison entre versions, versionnement des références | idem |
| 3 | Tests analytiques T1 à T6. T5 révèle le défaut #8 en `xfail(strict)` | idem |
| 4 | SI strict à l'intérieur, conversion aux frontières. Budget de 32 ULP, **réservé à cette phase**, 9 ULP observés | `reference_v2_phase4` |
| 5 | Six corrections de défauts, une par commit, chacune avec son tableau d'écart | `v3` à `v8`, voir ci-dessous |
| 6 | Lisibilité, retrait du code mort. **Empreinte identique bit à bit à la v8** | `reference_v9_phase6` |

Détail de la phase 5, dans l'ordre des commits :

| Référence | Défaut corrigé |
|---|---|
| `reference_v3_defaut9` | #9, déballage permuté des sorties de `generateP` |
| `reference_v4_defaut20` | #20, propagation d'erreur inhomogène |
| `reference_v5_defaut8` | **#8, priorité d'opérateurs, le plus grave** |
| `reference_v6_defauts10_19` | #10 et #19, lecture de la base et `rho = 0` |
| `reference_v7_defauts14_15` | #14 et #15, propagation d'erreur |
| `reference_v8_choix_explicites` | modèle et mode explicites, avertissement à l'exécution |

Référence active : `reference_v9_phase6`, désignée par `VERSION_ACTIVE` dans
`tests/reference_io.py`. Le registre complet des 22 défauts et de leur statut
est dans `notes/registre_defauts.md`.

## Les trois décisions structurantes

**1. Le `10**6` n'est pas résolu, la branche empirique est déclarée non
publiable.** Ce facteur est solidaire des valeurs `R` et `mP` ajustées sur des
mesures, et sa provenance est perdue : script d'ajustement absent du dépôt,
auteur du portage interrogé sans résultat. Il est nommé
`FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE`, isolé derrière un contrat d'unités,
figé. Le mode empirique imprime un avertissement à l'exécution et **ne doit
alimenter aucune figure d'article**. Raison : un paramètre orphelin ne se
répare pas, il se remplace. Remplacement prévu en phase 8.

**2. Les valeurs `mP` et `R` de la colonne C de `materials.xls` sont traitées
comme non lues.** `EC3515-0%` et `EC3515-8%` passent donc par la branche
analytique. Raison : un paramètre ajusté de provenance inconnue n'est pas
défendable devant un relecteur, alors qu'une prédiction sans aucun paramètre
ajusté l'est, qu'elle tombe juste ou non. Trois feuilles portent en outre des
valeurs identiques à seize chiffres pour des rhéologies sans rapport, donc au
moins deux sont un copier-coller. Tout est consigné dans
`notes/colonne_C_materials_xls.md`.

**3. `materials.xls` est gelé comme ancre d'intégrité.** Son sha256 est
vérifié par la suite. Le modifier invaliderait la référence active et rendrait
les huit précédentes irreproductibles. La base de travail est désormais
`materiaux.xlsx`, à en-têtes nommés, avec champs `modele`, `mode`,
`provenance` et une colonne d'incertitude par paramètre.

## Ce qui bloque la phase 7

**Il manque un jeu Herschel-Bulkley ajusté sur l'EC-3515, avec ses intervalles
de confiance.**

`Parrafin wax-40%`, seul matériau à seuil de la base, ne peut pas servir de cas
de validation : avec `n = 0.04` et `K = 2.85e6 Pa.s^n`, la loi de puissance
produit déjà une contrainte pariétale de 4 MPa qui écrase les 490 Pa du seuil.
La part du seuil vaut **0.013 à 0.015 %**. Négliger complètement le seuil
déplace la pression de moins d'un dix-millième : ce matériau ne testerait rien.

Il faut un jeu dont le nombre de Bingham est d'ordre 1 dans la plage de
vitesses utilisée.

Les colonnes `d_` de `materiaux.xlsx` sont volontairement **vides**. Les
anciennes valeurs, `dK = 0.1` sur `K = 6673` soit 1.5e-5 en relatif, et
`dn = 1e-4` sur `n = 0.3575` soit 2.8e-4, étaient inventées et absurdement
petites. **Ne pas brancher la nouvelle base sur le modèle avant d'avoir les
vrais intervalles de confiance.**

## La commande à lancer dès réception des paramètres

    python3 tools/nombre_de_bingham.py \
        --K <K> --n <n> --tau-y <tau_y> \
        --De 0.45 --Do 3.55 --L 17.25 \
        --vitesses 10 25 50 100 150 200 250 300

Le script est autonome, hors du chemin de calcul, et réécrit ses formules
exprès pour rester un contrôle indépendant.

**Lire uniquement la colonne PONDEREE.** C'est la part du seuil moyennée le
long de la buse et pondérée par la contribution locale à `Delta_P`, donc
exactement l'écart sur la pression prédite entre un traitement à seuil et un
traitement en loi de puissance pure. Les colonnes « en sortie » et « en
entrée » l'encadrent, elles ne décident pas : la chute de pression se concentre
côté sortie, où 78 % de `Delta_P` s'accumulent dans le dernier tiers du cône.

| Pondérée | Verdict | Ce qu'il faut faire |
|---|---|---|
| sous 1 % | seuil négligeable | **la phase 7 se réduit à l'extension conique**, le défaut #7 reste sans effet |
| 1 % à 10 % | seuil marginal | porter le seuil au modèle, sans urgence sur la solution exacte |
| au-delà de 10 % | seuil gouvernant | **phase 7 intégrale**, il faut la solution exacte de l'écoulement Herschel-Bulkley et ses équations de référence |

Les bornes sont des tolérances de modélisation assumées, réglables par
`--negligeable` et `--gouvernant`.

Rappel inscrit dans le script : la part pondérée est l'écart **démontré** dû à
l'omission du seuil. L'erreur due au bouchon central, celle que la correction
de Rabinowitsch manque, n'est pas calculée et est **supposée** du même ordre.

## Les nombres à confronter aux mesures

Pressions prédites, **mode analytique, aucun paramètre ajusté**, après
correction du défaut #8. Buse conique `De = 0.45 mm`, `Do = 3.55 mm`,
`L = 17.25 mm`, `alpha = 36`, `theta = 5.3 deg`, `P_amb = 101325 Pa`.

| v (mm/s) | EC3515-0% (kPa) | EC3515-8% (kPa) |
|---|---|---|
| 10 | 771.72 | 610.69 |
| 50 | 1 576.44 | 940.22 |
| 100 | 2 173.04 | 1 141.31 |
| 200 | 3 010.93 | 1 390.61 |
| 300 | 3 650.43 | 1 563.29 |

`EC3515-0%` : `n = 0.49`, `K = 3280 Pa.s^n`. `EC3515-8%` : `n = 0.31`,
`K = 4363 Pa.s^n`. Les deux à `rho = 973 kg/m^3`.

Ces valeurs incluent `P_amb`. Avant correction du défaut #8 elles valaient
respectivement 1 164.50 et 3 386.85 kPa à 10 et 100 mm/s pour `EC3515-0%`,
soit **de 10 à 37 % de plus**. Toute valeur antérieure à cette correction est
à écarter.

Elles sont reproductibles à tout moment :

    python3 -c "import json;r=json.load(open('tests/references/reference_v9_phase6.json'))['resultats'];print(r['B|EC3515-0%|conique']['sorties']['P_kPa'])"

## Ce qu'il reste à faire

**Phase 7, extension à seuil.** Réécrire la branche conique pour qu'elle
utilise la viscosité et le seuil, ce qui ferme les défauts #4, #7, #11 et #12.
Remplacer la correction de Weissenberg-Rabinowitsch d'une loi de puissance par
celle qui convient au modèle retenu. Ne pas commencer sans les équations de
référence : aucune relation ne doit être inventée.

**Phase 8, confrontation aux mesures.** Réajuster `R` et `mP` sur les pressions
mesurées, par un script versionné, en SI, ce qui fait disparaître le `10**6`
par construction et rend la provenance connue. Restaurer l'itération des
équations 4.7 et 4.8 pour résoudre le cas des buses non identiques, en
repartant des équations et non du code conservé dans
`notes/iteration_vitesse_reelle_phase_8.md`, qui porte un défaut connu. Produire
la comparaison prédiction contre mesure avec ses barres d'erreur.
