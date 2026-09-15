#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Contrat d'unites des champs enregistres dans les references.

#############################################################################
#  AVERTISSEMENT, A LIRE AVANT DE CORRIGER LE DEFAUT #9                     #
#                                                                           #
#  Les noms de champs utilises ci-dessous sont AUJOURD'HUI FAUX. Le          #
#  deballage des sorties de generateP dans main.compute_pressures est        #
#  permute : le champ nomme 'dP' contient deta, le champ nomme 'dRi'         #
#  contient dP, le champ nomme 'deta' contient dRi. C'est le defaut #9.      #
#                                                                           #
#  La colonne 'facteur' de cette table est attachee a la GRANDEUR REELLE,    #
#  pas au nom. Le jour ou le defaut #9 sera corrige, le contenu des champs   #
#  se remettra en place et cette table deviendra fausse EN SILENCE : les     #
#  valeurs auront bouge et le comparateur les validerait avec le mauvais     #
#  facteur.                                                                 #
#                                                                           #
#  LA CORRECTION DU DEFAUT #9 ET LA MISE A JOUR DE CETTE TABLE DOIVENT SE    #
#  FAIRE DANS LE MEME COMMIT.                                               #
#                                                                           #
#  tests/test_contrat_unites.py verifie a l'EXECUTION que la correspondance  #
#  declaree ici est bien celle du code. Il echoue si l'une bouge sans        #
#  l'autre, dans un sens comme dans l'autre.                                #
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

# Pour chaque champ enregistre dans une reference :
#   position  : indice dans le tuple rendu par generateP, ou None si le champ
#               est derive d'un autre (les variantes en kPa) ;
#   grandeur  : ce que le champ contient REELLEMENT aujourd'hui (defaut #9) ;
#   unite_mm  : unite dans les references produites avant la phase 4 ;
#   unite_si  : unite dans les references produites depuis la phase 4 ;
#   facteur   : valeur_si / valeur_mm attendue, ou NON_DECLARABLE.
CONTRAT = {
    "P":      dict(position=0, grandeur="P",    unite_mm="Pa",
                   unite_si="Pa",     facteur=1.0),
    "P_kPa":  dict(position=None, grandeur="P/1000", unite_mm="kPa",
                   unite_si="kPa",    facteur=1.0),
    "eta":    dict(position=1, grandeur="eta",  unite_mm="Pa.s",
                   unite_si="Pa.s",   facteur=1.0),
    "SR":     dict(position=2, grandeur="SR",   unite_mm="1/s",
                   unite_si="1/s",    facteur=1.0),
    "Q":      dict(position=3, grandeur="Q",    unite_mm="mm^3/s",
                   unite_si="m^3/s",  facteur=1e-9),
    "dP":     dict(position=4, grandeur="deta", unite_mm="Pa.s",
                   unite_si="Pa.s",   facteur=1.0),
    "dP_kPa": dict(position=None, grandeur="deta/1000", unite_mm="Pa.s/1000",
                   unite_si="Pa.s/1000", facteur=1.0),
    "dRi":    dict(position=5, grandeur="dP",   unite_mm="non homogene",
                   unite_si="non homogene", facteur=NON_DECLARABLE),
    "deta":   dict(position=6, grandeur="dRi",  unite_mm="non homogene",
                   unite_si="non homogene", facteur=NON_DECLARABLE),
    "dSR":    dict(position=7, grandeur="dSR",  unite_mm="1/s",
                   unite_si="1/s",    facteur=1.0),
}

# Justification des deux NON_DECLARABLE, defaut #20.
#
# calculateReqError additionne sous une meme racine trois termes de dimensions
# differentes. Il en resulte que dRi ne porte pas la dimension de Ri, et que
# dP = sqrt((ReqError Q_eq)^2 + (R_eq sum dQ)^2) combine deux termes qui ne se
# mettent pas a la meme echelle. Facteurs mesures, s = 1e-3 :
#
#   grandeur dRi   cylindrique        s^-5        = 1e+15
#                  conique analytique s^(1-6n)    = 10^(18n-3)
#                  conique empirique  s^1         = 1e-03
#
#   grandeur dP    cylindrique        A ~ s^-2 domine  = 1e+06
#                  conique analytique A ~ s^(4-6n) domine = 10^(18n-12)
#                  conique empirique  A ~ s^4 et B ~ s^3 sont COMPARABLES,
#                                     le rapport depend du cas et de la
#                                     vitesse : aucun facteur n'existe.
#
# Ces deux champs sont donc rapportes par le comparateur, avec leur rapport
# observe minimal et maximal, mais ne sont pas soumis au budget en ULP. C'est
# le seul endroit ou la neutralite de la phase 4 n'est pas demontrable, et la
# raison en est un defaut anterieur, pas la conversion.

# Budget d'ecart accorde a la phase 4, et a elle seule. Voir CLAUDE.md.
BUDGET_ULP_PHASE_4 = 32
