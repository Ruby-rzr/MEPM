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

## Récapitulatif

| Statut | Nombre | Numéros |
|---|---|---|
| corrigé | 11 | 3, 5, 6, 8, 9, 10, 14, 15, 17, 18, 19, 20 |
| encadré, non corrigeable en l'état | 1 | 1 |
| ouvert et gelé | 5 | 2, 13, 16, 21, 22 |
| reporté en phase 7 | 4 | 4, 7, 11, 12 |

Le défaut 20 est le seul qui n'était pas dans le diagnostic initial de sept
points : il a été trouvé en phase 4, en cherchant le facteur de conversion des
grandeurs d'incertitude. Les défauts 19, 21 et 22 ont été trouvés de la même
façon, en passant.
