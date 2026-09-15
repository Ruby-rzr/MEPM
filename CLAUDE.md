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
