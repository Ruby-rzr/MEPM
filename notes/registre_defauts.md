# Registre des défauts du MEPM

État au terme de la phase 6. Trois statuts :

- **corrigé**, avec le commit et l'ampleur de l'écart,
- **ouvert et gelé**, connu, documenté, figé par un test, non corrigé,
- **reporté en phase 7**, dont la correction fait partie de la réécriture de la
  branche conique et du modèle à seuil.

| # | Défaut | Statut |
|---|---|---|
| 1 | Mode conique empirique : `P` ne dépend ni de `K`, ni de `n`, ni de l'angle, ni de `L`. C'est un ajustement à deux paramètres déguisé en modèle | **encadré**, phase 5. Le mode est explicite, il imprime un avertissement à l'exécution, et CLAUDE.md le déclare NON PUBLIABLE. Il n'est corrigé par aucune réécriture : il sera remplacé en phase 8 par un réajustement de provenance connue |
| 2 | `R_eq` n'a pas les mêmes dimensions selon `Noz_type` : `Pa.s/m^3` en cylindrique, `Pa/(m^3/s)^n` en conique | **ouvert et gelé**. Intrinsèque aux deux formulations, documenté dans `calculateReq`. C'est la raison pour laquelle `dRi` n'a pas de facteur de conversion unique |
| 3 | Le `* 10**6` et le mélange mm et SI | **corrigé**, phase 4. SI strict à l'intérieur, conversion aux frontières. Le facteur est nommé `FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE`, isolé derrière un contrat d'unités explicite, sa valeur est inchangée et sa provenance déclarée perdue |
| 4 | `moyenne()` en conique : la mise en parallèle disparaît, faux dès que les buses varient | **reporté en phase 7** pour la partie conique, et **phase 8** pour la résolution du réseau, qui passe par l'itération des équations 4.7 et 4.8 de Chauvette 2023 |
| 5 | `Tapered Nozzle/calculateRes.py` vide, formule conique alternative commentée, vitesses de débogage à 3920 mm/s dans `main.py` | **corrigé**, phase 6, pour le dossier mort et le code commenté. Les vitesses 3920 à 3960 sont **délibérément conservées** dans la grille de référence, pour reproduire des nombres susceptibles d'avoir été utilisés ailleurs |
| 6 | Chemin absolu Windows codé en dur | **corrigé**, phase 6 |
| 7 | Les branches à seuil appliquent la correction de Weissenberg-Rabinowitsch d'une loi de puissance. Exact pour aucune d'entre elles | **reporté en phase 7**. La chaîne donne `Delta_P = 4 L (tau_0 + K gamma_w^n)/D`, où le bilan de forces et la loi de comportement sont exacts, mais où `gamma_w` est tiré de `Q` par une correction qui ignore le bouchon central |
| 8 | Priorité d'opérateurs dans la formule conique analytique, facteur parasite `(3n+1)^(1-n)` | **corrigé**, phase 5. Écart de -10 à -37 % sur la pression conique. EC3515-0% à 100 mm/s : 3 386.85 kPa devient 2 173.04 kPa |
| 9 | Déballage permuté des sorties de `generateP` dans `compute_pressures` | **corrigé**, phase 5. Aucune pression ne bouge, trois grandeurs d'incertitude reprennent leur place. Verrou permanent dans `tests/test_contrat_unites.py` |
| 10 | `readMaterial` lève une `IndexError` sur 12 feuilles sur 19 | **corrigé**, phase 5. 24 cas passent d'exception à résultat |
| 11 | En conique, `eta` n'intervient pas dans `P`. Pour `K = 0`, la résistance vaut zéro et `P` se réduit à `P_amb` | **reporté en phase 7** |
| 12 | `calculateReqError` applique la propagation cylindrique quelle que soit la géométrie | **reporté en phase 7** |
| 13 | `Re` est calculé sur les trois lignes de `D`, donc aussi sur l'erreur de mesure et sur le diamètre d'entrée, et le critère de laminarité porte sur les trois | **ouvert et gelé**, figé par `tests/test_reynolds.py`. Sans conséquence numérique aujourd'hui, les Reynolds valant 1e-4 ou moins |
| 14 | `calculateVisco` écrase son argument `dSR` par une constante | **corrigé**, phase 5. La valeur propagée vaut environ 4 s⁻¹ contre 1e-4 imposé |
| 15 | `deta` des branches à seuil : carrés manquants, mauvais exposant, signes qui se compensent. Rendait `NaN` dès que `SR < 1` | **corrigé**, phase 5 |
| 16 | `P_amb` ajouté dans deux branches sur trois. Mélange de pression absolue et de pression relative | **ouvert et gelé**, documenté dans `calculatePrequired`. La branche empirique n'ajoute pas l'ambiante, c'est le comportement d'origine, conservé tel quel |
| 17 | `generateVreal.py` non importable, et applique deux fois de plus la correction de Rabinowitsch sur des fonctions qui l'appliquent déjà | **corrigé**, phase 6. Fichier retiré comme code mort, son algorithme consigné dans `notes/iteration_vitesse_reelle_phase_8.md` pour la phase 8 |
| 18 | Valeurs numériques en dur dans le code de calcul | **corrigé**, phase 5. Incertitudes nommées puis déplacées vers la base, seuils de Reynolds nommés, facteur empirique nommé |
| 19 | `rho = 0` fait lever une `ValueError` sur l'ambiguïté d'un tableau | **corrigé**, phase 5 |
| 20 | `calculateReqError` additionne sous une même racine trois termes de dimensions différentes | **corrigé**, phase 5. Propagation dérivée de la définition de `Ri`, homogène par construction |
| 21 | La branche de Carreau n'a **aucun terme en `dn`**. La dérivée `d eta/d n` est absente de la somme en quadrature | **ouvert et gelé**. Arbitrage : branche non utilisée par les matériaux de l'étude, et rendue inopérante en conique par le défaut #11. **À traiter si quelqu'un branche un matériau de Carreau** |
| 22 | Branche de Carreau, terme `deta5` : `ratio` apparaît à la puissance 1 là où la dérivation donne `ratio^((n-1)/a)` | **ouvert et gelé**, même arbitrage que #21. Sans effet numérique tant que `da` vaut zéro, ce qui est le cas aujourd'hui. **À traiter si quelqu'un branche un matériau de Carreau** |
| 23 | Les paramètres rhéologiques de `EC3515-0%` et `EC3515-8%` se croisent à 4.88 1/s, et la formulation chargée devient MOINS visqueuse au-delà | **observation, non tranchée**. Ce n'est pas un défaut du code, c'est une anomalie des DONNÉES. Voir la section détaillée ci-dessous |
| 24 | À pression imposée, l'erreur du défaut #8 sur le débit vaut `(3n+1)^((1-n)/n)`, soit un facteur 2.56 à `n = 0.49` et 4.32 à `n = 0.31`, contre 1.59 et 1.57 sur la pression | **observation**, conséquence chiffrée du défaut #8 déjà corrigé. Voir la section détaillée ci-dessous |

## Récapitulatif

| Statut | Nombre | Numéros |
|---|---|---|
| corrigé | 12 | 3, 5, 6, 8, 9, 10, 14, 15, 17, 18, 19, 20 |
| encadré, non corrigeable en l'état | 1 | 1 |
| ouvert et gelé | 5 | 2, 13, 16, 21, 22 |
| reporté en phase 7 | 4 | 4, 7, 11, 12 |
| observation sur les données, non tranchée | 1 | 23 |
| observation, conséquence d'un défaut corrigé | 1 | 24 |

Le défaut 20 est le seul qui n'était pas dans le diagnostic initial de sept
points : il a été trouvé en phase 4, en cherchant le facteur de conversion des
grandeurs d'incertitude. Les défauts 19, 21 et 22 ont été trouvés de la même
façon, en passant.


## Observation #23 : croisement rhéologique entre EC3515-0% et EC3515-8%

**Observation, pas conclusion.** Elle porte sur les DONNÉES de la base, pas sur
le code.

### Le constat

| Feuille | n | K [Pa.s^n] |
|---|---|---|
| `EC3515-0%` | 0.49 | 3280 |
| `EC3515-8%` | 0.31 | 4363 |

Les deux contraintes pariétales `K gamma^n` se croisent à **4.8797 1/s**, où
elles valent toutes deux 7 131 Pa, soit une viscosité apparente de 1 462 Pa.s.
Au-delà, **la formulation chargée est la moins visqueuse** :

| gamma (1/s) | tau 0% (Pa) | tau 8% (Pa) | rapport 0% / 8% |
|---|---|---|---|
| 0.5 | 2 335 | 3 519 | 0.664 |
| 4.88 | 7 131 | 7 131 | 1.000 |
| 100 | 31 324 | 18 188 | 1.722 |
| 1 000 | 96 800 | 37 135 | **2.607** |
| 10 000 | 299 140 | 75 820 | 3.945 |

C'est ce qui explique que `EC3515-8%` demande **moins** de pression que
`EC3515-0%` dans la référence.

### Où se situe l'écoulement réel

Cisaillement pariétal corrigé, buse conique `De = 0.45 mm`, `Do = 3.55 mm` :

| v (mm/s) | sortie, 0% | sortie, 8% | entrée, 0% | entrée, 8% |
|---|---|---|---|---|
| 10 | 224.0 | 276.7 | 0.456 | 0.564 |
| 100 | 2 240 | 2 767 | 4.563 | 5.636 |
| 300 | 6 721 | 8 301 | 13.69 | 16.91 |

**À la sortie de buse, tout l'écoulement est au-dessus du croisement**, de 10^2
à 10^4 1/s. **À l'entrée, non** : le cisaillement y vaut 0.46 à 17 1/s et
traverse le croisement à 4.88 1/s. Cette section pèse peu dans `Delta_P`, 22 %
environ, mais la plage de cisaillement réellement parcourue dans la buse
s'étend donc sur **quatre ordres de grandeur**, de 0.46 à 8 300 1/s.

### Trois lectures possibles, aucune tranchée

1. **Ajustements sur des fenêtres de cisaillement différentes, puis
   extrapolés.** Deux ajustements en loi de puissance réalisés sur des
   intervalles disjoints se croisent presque toujours hors de leurs intervalles
   respectifs. C'est l'explication la plus économique, et elle est invérifiable
   en l'état : aucune feuille ne porte sa plage de validité.
2. **Croisement rhéologique réel.** Une charge peut abaisser la viscosité à
   haut cisaillement, par exemple par glissement à la paroi ou par
   structuration. Ce serait un résultat en soi, à documenter comme tel.
3. **Paramètres erronés sur une feuille déjà contaminée.** `EC3515-8%` porte en
   colonne C des valeurs `mP` et `R` identiques à seize chiffres à celles de
   `Wax-Bruneaux` et `Wax-JFC`, donc au moins un copier-coller avéré sur cette
   feuille. Voir `notes/colonne_C_materials_xls.md`.

### Conséquence à inscrire dans le modèle

**Tout ajustement rhéologique entrant dans la base doit porter sa plage de
cisaillement de validité**, et le code doit **avertir à l'exécution quand le
cisaillement pariétal calculé sort de cette plage**.

À faire en phase 7 :

- ajouter les colonnes `gamma_min` et `gamma_max` à `materiaux.xlsx`, et les
  renseigner pour tout nouveau matériau,
- vérifier le cisaillement pariétal contre cette plage en chaque section de
  buse, et non seulement à la sortie, puisque l'entrée d'une buse conique peut
  être quatre décades plus bas,
- émettre un avertissement visible, sur le modèle de celui du mode empirique,
  quand l'écoulement sort de la plage d'ajustement. Une extrapolation
  silencieuse d'une loi de puissance sur quatre décades n'est pas défendable
  devant un relecteur.


## Observation #24 : l'erreur du défaut #8 est bien plus grande à pression imposée

**Observation, pas défaut.** Le défaut #8 est corrigé. Cette entrée chiffre sa
conséquence sur une grandeur que le code ne produit pas directement, le débit à
pression imposée, parce que c'est sous cette forme que le mémoire d'origine
présente la formulation conique.

### Les deux formes sont inverses l'une de l'autre

Le code implémente la chute de pression à débit imposé. L'annexe A du mémoire
donne le débit à pression imposée :

    Q = (n pi / (3n+1))
        [ 3 n Delta_P tan(theta)
          / (2 K (R_sortie^-3n - R_entree^-3n)) ]^(1/n)

L'aller-retour `Q` vers `Delta_P` par le code, puis `Delta_P` vers `Q` par
l'annexe A, **boucle à 3.1e-15 en relatif** sur 45 combinaisons, 5 valeurs de
`n` et 3 géométries. C'est la précision machine. Vérifié en permanence par
`tests/test_coherence_annexe_A.py`.

### Le facteur d'erreur est élevé à la puissance 1/n

Avant correction, la résistance valait `Ri_faux = Ri_juste (3n+1)^(1-n)`. À
**débit** imposé, `Delta_P` était donc surestimée de ce facteur. À **pression**
imposée, l'inversion élève l'erreur à la puissance `1/n` :

    Q_juste / Q_faux = (3n+1)^((1-n)/n)

| n | sur la pression, `(3n+1)^(1-n)` | sur le débit, `(3n+1)^((1-n)/n)` |
|---|---|---|
| 0.2429 | 1.5135 | **5.5075** |
| 0.3100 | 1.5741 | **4.3211** |
| 0.3575 | 1.5972 | **3.7051** |
| 0.4900 | 1.5859 | **2.5629** |
| 0.8000 | 1.2773 | 1.3579 |
| 1.0000 | 1.0000 | 1.0000 |

**Conséquence : toute figure produite en inversant le modèle avant la
correction du défaut #8 est affectée dans ces proportions**, et non dans celles
de 10 à 37 % relevées sur la pression. Un tracé de débit contre pression, ou
une vitesse d'impression déduite d'une pression appliquée, est faux d'un
facteur 2.6 à 5.5 selon l'indice d'écoulement du matériau.

### Piège annexe : l'angle du cône se déduit, il ne se déclare pas

La branche conique analytique **n'utilise pas** l'argument `theta` qu'on lui
passe : elle travaille avec `L`, `De` et `Do`, ce qui revient implicitement à

    tan(theta) = (Do - De) / (2 L)

Or `main.py` déclare `angle = 5.3` degrés alors que la géométrie livrée,
`De = 0.45 mm`, `Do = 3.55 mm`, `L = 17.25 mm`, impose **5.1345 degrés**.

Cette incohérence est **sans effet sur le modèle**, qui ignore l'argument. Elle
n'est pas sans effet sur quiconque inverserait le modèle avec la forme de
l'annexe A en prenant l'angle déclaré : le débit varie comme
`tan(theta)^(1/n)`, donc l'écart s'amplifie quand `n` diminue.

| n | erreur sur Q si l'on prend 5.3 degrés |
|---|---|
| 0.2429 | +14.03 % |
| 0.3100 | +10.84 % |
| 0.4900 | +6.73 % |
| 0.8000 | +4.07 % |
| 1.0000 | +3.24 % |

Figé par `test_l_angle_doit_etre_celui_de_la_geometrie`.
