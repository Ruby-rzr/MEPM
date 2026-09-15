#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contrat d'unites des champs enregistres dans les references.

Un facteur de conversion appartient a une GRANDEUR PHYSIQUE, pas a un nom de
champ. Ce module separe donc deux choses :

  FACTEUR_PAR_GRANDEUR
      ce que devient chaque grandeur quand on passe des millimetres au SI ;

  CORRESPONDANCE_COURANTE et CORRESPONDANCE_AVANT_DEFAUT_9
      quel champ contient quelle grandeur, selon la version du code qui a
      produit la reference.

#############################################################################
#  POURQUOI CETTE SEPARATION                                                #
#                                                                           #
#  Jusqu'a la correction du defaut #9, le deballage des sorties de generateP #
#  dans main.compute_pressures etait permute : le champ nomme 'dP'           #
#  contenait deta, 'dRi' contenait dP, et 'deta' contenait dRi.              #
#                                                                           #
#  Attacher les facteurs aux NOMS aurait rendu la table fausse en silence le #
#  jour de la correction : les valeurs auraient bouge et le comparateur les  #
#  aurait validees avec le mauvais facteur. En les attachant aux GRANDEURS   #
#  et en versionnant la correspondance, une reference ancienne reste         #
#  comparable apres la correction.                                          #
#                                                                           #
#  TOUTE MODIFICATION DU DEBALLAGE DANS main.compute_pressures DOIT METTRE   #
#  A JOUR CORRESPONDANCE_COURANTE DANS LE MEME COMMIT.                       #
#  tests/test_contrat_unites.py le verifie a l'execution et echoue si l'une  #
#  bouge sans l'autre, dans un sens comme dans l'autre.                      #
#############################################################################

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

# Ordre reel des sorties de Velocity_driven.generateP.generateP.
GRANDEURS_RENDUES_PAR_GENERATEP = ("P", "eta", "SR", "Q",
                                   "deta", "dP", "dRi", "dSR")

# Facteur non declarable : la grandeur n'a pas de facteur de conversion, sa
# formule n'etant pas dimensionnellement homogene. Voir defaut #20.
NON_DECLARABLE = None

# Ce que devient chaque grandeur quand la chaine passe des mm au SI.
FACTEUR_PAR_GRANDEUR = {
    "P": 1.0,              # Pa, invariant
    "P/1000": 1.0,         # kPa, invariant
    "eta": 1.0,            # Pa.s, invariant
    "SR": 1.0,             # 1/s, invariant
    "Q": 1e-9,             # mm^3/s vers m^3/s
    "deta": 1.0,           # Pa.s, invariant
    "deta/1000": 1.0,      # invariant
    "dP": NON_DECLARABLE,  # defaut #20
    "dP/1000": NON_DECLARABLE,
    "dRi": NON_DECLARABLE,  # defaut #20
    "dSR": 1.0,            # 1/s, invariant
}

UNITE_PAR_GRANDEUR_MM = {
    "P": "Pa", "P/1000": "kPa", "eta": "Pa.s", "SR": "1/s", "Q": "mm^3/s",
    "deta": "Pa.s", "deta/1000": "Pa.s/1000", "dP": "non homogene",
    "dP/1000": "non homogene", "dRi": "non homogene", "dSR": "1/s",
}
UNITE_PAR_GRANDEUR_SI = dict(UNITE_PAR_GRANDEUR_MM, Q="m^3/s")

# Correspondance en vigueur dans le code ACTUEL, defaut #9 corrige.
# 'position' est l'indice dans le tuple rendu par generateP, ou None pour un
# champ derive d'un autre.
CORRESPONDANCE_COURANTE = {
    "P":      dict(position=0, grandeur="P"),
    "P_kPa":  dict(position=None, grandeur="P/1000"),
    "eta":    dict(position=1, grandeur="eta"),
    "SR":     dict(position=2, grandeur="SR"),
    "Q":      dict(position=3, grandeur="Q"),
    "deta":   dict(position=4, grandeur="deta"),
    "dP":     dict(position=5, grandeur="dP"),
    "dP_kPa": dict(position=None, grandeur="dP/1000"),
    "dRi":    dict(position=6, grandeur="dRi"),
    "dSR":    dict(position=7, grandeur="dSR"),
}

# Correspondance des references produites AVANT la correction du defaut #9,
# c'est a dire reference_v1_phase1 et reference_v2_phase4. Conservee pour que
# ces references restent comparables.
CORRESPONDANCE_AVANT_DEFAUT_9 = {
    "P":      dict(position=0, grandeur="P"),
    "P_kPa":  dict(position=None, grandeur="P/1000"),
    "eta":    dict(position=1, grandeur="eta"),
    "SR":     dict(position=2, grandeur="SR"),
    "Q":      dict(position=3, grandeur="Q"),
    "dP":     dict(position=4, grandeur="deta"),     # permute
    "dP_kPa": dict(position=None, grandeur="deta/1000"),
    "dRi":    dict(position=5, grandeur="dP"),       # permute
    "deta":   dict(position=6, grandeur="dRi"),      # permute
    "dSR":    dict(position=7, grandeur="dSR"),
}

# Nom sous lequel une reference declare sa correspondance dans ses
# metadonnees. Les references anterieures a la phase 5 n'en portent pas, et
# sont traitees comme CORRESPONDANCE_AVANT_DEFAUT_9.
CORRESPONDANCES_CONNUES = {
    "courante": CORRESPONDANCE_COURANTE,
    "avant_defaut_9": CORRESPONDANCE_AVANT_DEFAUT_9,
}
CORRESPONDANCE_PAR_DEFAUT = "avant_defaut_9"
CORRESPONDANCE_ACTUELLE = "courante"


def grandeur_du_champ(champ, nom_correspondance):
    """Grandeur reellement contenue par un champ, pour une correspondance."""
    return CORRESPONDANCES_CONNUES[nom_correspondance][champ]["grandeur"]


def facteur_du_champ(champ, nom_correspondance):
    """Facteur de conversion mm vers SI du contenu reel d'un champ."""
    return FACTEUR_PAR_GRANDEUR[grandeur_du_champ(champ, nom_correspondance)]


# Justification des NON_DECLARABLE.
#
# Avant la correction du defaut #20, calculateReqError additionnait sous une
# meme racine trois termes de dimensions differentes, et delta_Ri portait la
# dimension de Ri^2 fois une longueur. La propagation est desormais homogene
# par construction, delta_Ri = Ri * incertitude_relative.
#
# Ces deux grandeurs restent neanmoins non declarables, pour deux raisons
# distinctes et toutes deux anterieures :
#
#   dRi  suit la dimension de Ri, laquelle depend de la branche (defaut #2) :
#        Pa.s/m^3 en cylindrique, Pa/(m^3/s)^n en conique analytique,
#        indeterminee en conique empirique. Il n'existe donc pas un facteur
#        unique, et ce n'est pas un defaut de la propagation.
#
#   dP   vaut sqrt((delta_R_eq Q_eq)^2 + (R_eq somme dQ)^2). En cylindrique
#        les deux termes sont des Pa et le facteur vaut 1. En conique, le
#        produit R_eq Q_eq n'est pas une pression, la pression valant
#        R_eq Q_eq^n : la propagation cylindrique est appliquee a une
#        resistance d'une autre dimension. C'est le defaut #12, qui sera
#        ferme en phase 7 avec la reecriture de la branche conique.
#
# Sans consequence pratique depuis la phase 4 : toutes les comparaisons
# ulterieures se font entre references SI, ou tous les facteurs valent 1.

# Budget d'ecart accorde a la phase 4, et a elle seule. Voir CLAUDE.md.
BUDGET_ULP_PHASE_4 = 32
