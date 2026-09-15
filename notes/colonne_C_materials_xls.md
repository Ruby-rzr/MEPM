# Les valeurs mP et R de la colonne C de materials.xls

État : **consigné, non utilisé.** Ces valeurs ne sont lues par aucun code du
dépôt. `readMaterial` lit la colonne B, où `mP` et `R` valent zéro pour toutes
les feuilles concernées, ce qui envoie ces matériaux sur la branche analytique.

## Ce que contient la colonne C

| Feuille | mP | R |
|---|---|---|
| `EC3515-0%` | 0.4728957491325613 | 1.3344569767816075 |
| `EC3515-8%` | 0.3828177864281889 | 0.29637175877940436 |
| `Wax-Bruneaux` | 0.3828177864281889 | 0.29637175877940436 |
| `Wax-JFC` | 0.3828177864281889 | 0.29637175877940436 |

## Trois feuilles portent les mêmes valeurs

`EC3515-8%`, `Wax-Bruneaux` et `Wax-JFC` portent des valeurs identiques à seize
chiffres, pour trois matériaux sans rapport :

| Feuille | n | K [Pa.s^n] |
|---|---|---|
| `Wax-Bruneaux` | 0.436 | 875 |
| `Wax-JFC` | 0.468 | 604 |
| `EC3515-8%` | 0.310 | 4363 |

Un ajustement ne peut pas donner le même résultat pour ces trois-là. Au moins
deux des trois sont un copier-coller. Ces valeurs sont écartées.

## EC3515-0%, le seul jeu possiblement propre

Comparé au modèle **corrigé**, c'est à dire après correction du défaut #8, cet
ajustement vaut 2.15 à 2.27 fois la prédiction analytique, et son exposant en
débit vaut 0.473 contre 0.457 pour le modèle, sur un matériau à n = 0.49.

Même loi d'échelle, facteur multiplicatif à peu près constant.

**HYPOTHÈSE NON VÉRIFIÉE.** Si cet ajustement provient de vraies mesures,
l'écart est compatible avec une contribution d'entrée et élongationnelle,
ignorée par l'approximation de lubrification sur laquelle repose la formule
conique analytique. Ce n'est pas démontré : la provenance de ces valeurs est
perdue, le script d'ajustement est absent du dépôt, et l'auteur du portage
interrogé ne la connaît pas non plus.

## Décision

Ces valeurs restent inutilisées. Un paramètre ajusté dont la provenance est
inconnue n'est pas défendable devant un relecteur, alors qu'une prédiction sans
aucun paramètre ajusté l'est, qu'elle tombe juste ou non.

Le remplacement est prévu en phase 8 : réajustement de `R` et `mP` sur des
pressions mesurées, par un script versionné, en SI. La provenance redevient
alors connue et le facteur `FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE` disparaît par
construction. Un paramètre orphelin ne se répare pas, il se remplace.
