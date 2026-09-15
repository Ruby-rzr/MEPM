#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Invariance du nombre de Reynolds, phase 4 de la refonte.

validateReynolds calculait Re = rho v D / eta puis divisait par 1e6. Cette
division N'ETAIT PAS un rustinage : c'etait une conversion d'unites correcte.
Avec rho en kg/m^3, v en mm/s, D en mm et eta en Pa.s, le produit rho v D / eta
valait 1e6 fois le nombre de Reynolds, puisque v D valait 1e-6 fois sa valeur
en m^2/s.

Depuis la phase 4, la conversion a lieu a la frontiere d'entree et la division
a disparu. Ce test verifie que la valeur rendue est inchangee : il compare Re
au produit rho v D / eta calcule en SI, qui est la meme grandeur avant et
apres la conversion.

Il fige aussi le defaut #13 : Re est calcule sur les TROIS lignes du tableau D,
donc sur le diametre de sortie, sur l'erreur de mesure et sur le diametre
d'entree. Le critere de laminarite porte sur les trois. Ce comportement est
gele tel quel, sa correction change le domaine de validite du modele et releve
d'une phase ulterieure.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import numpy as np                                     # noqa: E402
import pytest                                          # noqa: E402

from tests.reference_io import make_D                  # noqa: E402
from tools.unites import entrees_vers_si               # noqa: E402
from Velocity_driven import validateReynolds           # noqa: E402

# Budget d'ecart entre la valeur rendue par le code et la valeur recalculee en
# SI. Il n'est pas nul : 0.45 * 1e-3 ne vaut pas le flottant 0.00045, donc
# l'egalite dimensionnelle exacte n'est pas une egalite binaire exacte. Trois
# ULP couvrent largement les trois multiplications en jeu.
BUDGET_ULP = 3

CAS = [
    # (rho [kg/m^3], v [mm/s], De [mm], Do [mm], eta [Pa.s], alpha)
    (973.0, 100.0, 0.45, 3.55, 207.59241610358117, 4),
    (1279.0, 250.0, 0.25, 3.55, 1000.0, 2),
    (1084.0, 10.0, 0.60, 1.00, 12.5, 3),
    (500.0, 3920.0, 0.45, 3.55, 325.85, 1),
]


def ecart_ulp(a, b):
    """Distance en ULP entre deux flottants de meme signe."""
    ia = np.float64(a).view(np.int64).astype(object)
    ib = np.float64(b).view(np.int64).astype(object)
    return abs(int(ia) - int(ib))


@pytest.mark.parametrize("rho, v, De, Do, eta_val, alpha", CAS)
def test_reynolds_egale_la_valeur_SI(rho, v, De, Do, eta_val, alpha):
    """Re rendu par le code egale rho v D / eta calcule directement en SI."""
    D_si, _, v_si = entrees_vers_si(make_D(De, Do, alpha), np.array([0.0]), v)
    eta = np.full(alpha, eta_val)
    _, Re = validateReynolds.validateReynolds(rho, float(v_si), D_si, eta, False)

    Re_si = rho * float(v_si) * D_si / eta

    assert Re.shape == Re_si.shape
    ecarts = [(indice, float(Re[indice]), float(Re_si[indice]),
               ecart_ulp(Re[indice], Re_si[indice]))
              for indice in np.ndindex(Re.shape)
              if ecart_ulp(Re[indice], Re_si[indice]) > BUDGET_ULP]
    assert not ecarts, (
        "\nRe s'ecarte de la valeur SI de plus de "
        f"{BUDGET_ULP} ULP :\n  " + "\n  ".join(
            f"indice {i} : code={a!r} SI={b!r} ecart {u} ULP"
            for i, a, b, u in ecarts))


@pytest.mark.parametrize("rho, v, De, Do, eta_val, alpha", CAS)
def test_reynolds_porte_sur_les_trois_lignes_de_D(rho, v, De, Do, eta_val, alpha):
    """Defaut #13 gele : Re est un tableau (3, alpha), pas (alpha,).

    La ligne 0 correspond au diametre de sortie, la ligne 1 a l'erreur de
    mesure sur ce diametre, la ligne 2 au diametre d'entree. Les lignes 1 et 2
    ne sont pas des nombres de Reynolds, et le critere de laminarite porte
    pourtant sur elles.
    """
    D_si, _, v_si = entrees_vers_si(make_D(De, Do, alpha), np.array([0.0]), v)
    eta = np.full(alpha, eta_val)
    _, Re = validateReynolds.validateReynolds(rho, float(v_si), D_si, eta, False)

    assert Re.shape == (3, alpha), (
        f"Re a la forme {Re.shape}, attendu (3, {alpha}). Si cette forme a "
        "change, le defaut #13 a ete corrige : le constater explicitement.")
    # Les trois lignes sont proportionnelles aux trois lignes de D.
    for ligne in range(3):
        attendu = rho * float(v_si) * D_si[ligne, :] / eta
        assert np.allclose(Re[ligne, :], attendu, rtol=1e-15, atol=0.0)
