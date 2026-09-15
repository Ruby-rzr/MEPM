#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Conversions d'unites aux frontieres du MEPM.

Regle 4 de CLAUDE.md : unites SI en interne, m, Pa, s, kg. Conversion
uniquement aux frontieres, a la lecture des entrees et a l'affichage.

Les frontieres du modele sont :
  - la saisie de la geometrie et de la vitesse, exprimees en mm et mm/s par
    l'utilisateur, converties par entrees_vers_si ;
  - l'affichage, qui reconvertit vers les unites d'usage de l'atelier ;
  - la branche empirique de calculatePrequired, dont les parametres ajustes
    R et mP ont ete determines dans une convention en mm^3/s. Voir
    FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE dans calculatePrequired.

La base de materiaux materials.xls est deja en SI : rho en kg/m^3, K en
Pa.s^n, eta en Pa.s, tau_0 en Pa, lambda en s. Elle ne demande aucune
conversion.

ATTENTION : la conversion n'est pas neutre au bit pres. 0.45 * 1e-3 ne vaut
pas le flottant 0.00045, donc une chaine de calcul menee en m ne rend pas
exactement le meme flottant que la meme chaine menee en mm, meme quand les
millimetres s'annulent algebriquement. L'ecart est de quelques ULP.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import numpy as np

# Facteurs de conversion vers le SI.
MILLIMETRE = 1e-3          # 1 mm en m
MILLIMETRE_CUBE = 1e-9     # 1 mm^3 en m^3
KILO = 1e3                 # Pa vers kPa, kg vers g


def mm_vers_m(longueur_mm):
    """Longueur ou vitesse, de mm vers m, ou de mm/s vers m/s."""
    return np.asarray(longueur_mm, dtype=float) * MILLIMETRE


def m_vers_mm(longueur_m):
    """Longueur ou vitesse, de m vers mm, ou de m/s vers mm/s."""
    return np.asarray(longueur_m, dtype=float) / MILLIMETRE


def m3_par_s_vers_mm3_par_s(debit_m3_par_s):
    """Debit volumique, de m^3/s vers mm^3/s."""
    return np.asarray(debit_m3_par_s, dtype=float) / MILLIMETRE_CUBE


def mm3_par_s_vers_m3_par_s(debit_mm3_par_s):
    """Debit volumique, de mm^3/s vers m^3/s."""
    return np.asarray(debit_mm3_par_s, dtype=float) * MILLIMETRE_CUBE


def entrees_vers_si(D_mm, L_mm, v_mm_par_s):
    """Convertit la geometrie et la vitesse saisies en mm vers le SI.

    C'est LA frontiere d'entree du modele. Tout ce qui est en aval travaille
    en m, Pa, s, kg.

    Args:
        D_mm (array-like): tableau (3, alpha) des diametres, sortie, erreur,
            entree. [mm]
        L_mm (array-like): longueur de buse et son erreur. [mm]
        v_mm_par_s (float or array-like): vitesse en sortie de buse. [mm/s]

    Returns:
        tuple: (D [m], L [m], v [m/s]).
    """
    return (mm_vers_m(D_mm), mm_vers_m(L_mm), mm_vers_m(v_mm_par_s))
