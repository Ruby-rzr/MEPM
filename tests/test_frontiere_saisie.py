#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Garde-fou de la frontiere de saisie de main.py.

La suite de non-regression passe par tests/reference_io.execute, qui fait sa
propre conversion mm vers SI. Elle ne teste donc PAS le chemin interactif de
main.py. Une conversion manquante dans ce chemin ne serait vue par personne,
alors que c'est le point d'entree reel du modele.

Ce fichier existe parce que cette erreur a effectivement eu lieu : les
modifications de phase 4 sur main.py ont ete annulees par un 'git checkout'
destine a defaire une mutation temporaire, et le commit de phase 4 a ete
produit sans elles. La suite est restee verte.

Le symptome est silencieux et grave : appeler compute_pressures avec des
millimetres alors qu'elle attend des metres donne un nombre de Reynolds un
million de fois trop grand, ce qui fait basculer le modele hors du regime
laminaire et rend des NaN, ou pire, laisse passer des pressions fausses.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import contextlib
import io
import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import numpy as np                                     # noqa: E402
import pytest                                          # noqa: E402

from Velocity_driven.modeles import (                  # noqa: E402
    ANALYTIQUE, LOI_DE_PUISSANCE)
from tests.reference_io import make_D                  # noqa: E402
from tools.readMaterial import INCERTITUDES_HISTORIQUES  # noqa: E402
from tools.unites import entrees_vers_si               # noqa: E402

CHOIX = (LOI_DE_PUISSANCE, ANALYTIQUE, INCERTITUDES_HISTORIQUES)

# Grandeurs de saisie, en mm et mm/s, comme dans main.py.
V_MM = np.array([10.0, 50.0, 100.0, 300.0])
L_MM = np.array([17.25, 0.01])
THETA = math.radians(5.3)
P_AMB = 101325.0


@pytest.mark.parametrize("Noz_type", ["cylindrical", "tapered"])
def test_executer_sur_saisie_mm_convertit_bien(Noz_type):
    """executer_sur_saisie_mm doit donner le meme resultat que la conversion explicite."""
    import main                                        # noqa: PLC0415
    alpha = 4
    D_mm = make_D(0.45, 3.55, alpha, 0.001)
    args = (0.49, 3280.0, 0.0, 0.0, 0.0, 0.0, 0.0, P_AMB, Noz_type, 0.0, 0.0,
            alpha, False) + CHOIX

    with contextlib.redirect_stdout(io.StringIO()):
        par_frontiere = main.executer_sur_saisie_mm(
            973.0, V_MM, D_mm, L_MM, THETA, *args)
        D_si, L_si, v_si = entrees_vers_si(D_mm, L_MM, V_MM)
        par_conversion_explicite = main.compute_pressures(
            973.0, v_si, D_si, L_si, THETA, *args)

    for champ in ("P", "eta", "SR", "Q"):
        a = np.asarray(par_frontiere[champ], dtype=float)
        b = np.asarray(par_conversion_explicite[champ], dtype=float)
        assert np.array_equal(a, b, equal_nan=True), (
            f"champ {champ!r} : la frontiere de saisie ne fait pas la meme "
            f"chose que la conversion explicite")


@pytest.mark.parametrize("Noz_type", ["cylindrical", "tapered"])
def test_saisie_en_mm_donne_un_resultat_physique(Noz_type):
    """Le chemin de saisie donne des pressions finies et positives.

    C'est le test qui aurait attrape la conversion manquante : sans elle, le
    nombre de Reynolds est un million de fois trop grand, le modele quitte le
    regime laminaire et rend des NaN.
    """
    import main                                        # noqa: PLC0415
    alpha = 4
    D_mm = make_D(0.45, 3.55, alpha, 0.001)
    with contextlib.redirect_stdout(io.StringIO()):
        resultat = main.executer_sur_saisie_mm(
            973.0, V_MM, D_mm, L_MM, THETA, 0.49, 3280.0, 0.0, 0.0, 0.0, 0.0,
            0.0, P_AMB, Noz_type, 0.0, 0.0, alpha, False, *CHOIX)

    P = np.asarray(resultat["P"], dtype=float)
    assert np.all(np.isfinite(P)), (
        f"{Noz_type} : pressions non finies {P}. Symptome typique d'une "
        "conversion mm vers SI manquante a la frontiere de saisie.")
    assert np.all(P > P_AMB), f"{Noz_type} : pressions sous l'ambiante {P}"
    # Ordre de grandeur attendu pour un epoxy charge en DIW : de 0.1 a 100 MPa.
    assert np.all(P < 1e8), f"{Noz_type} : pressions invraisemblables {P}"
    assert np.all(np.diff(P) > 0), (
        f"{Noz_type} : la pression doit croitre avec la vitesse, {P}")


def test_compute_pressures_en_mm_produit_un_resultat_faux():
    """Documente le symptome : appeler compute_pressures en mm rend des NaN.

    Ce test ne valide pas un comportement souhaitable, il fige le symptome
    pour que l'on sache le reconnaitre.
    """
    import main                                        # noqa: PLC0415
    alpha = 4
    with contextlib.redirect_stdout(io.StringIO()):
        faux = main.compute_pressures(
            973.0, V_MM, make_D(0.45, 3.55, alpha, 0.001), L_MM, THETA,
            0.49, 3280.0, 0.0, 0.0, 0.0, 0.0, 0.0, P_AMB, "cylindrical",
            0.0, 0.0, alpha, False, *CHOIX)
    assert np.all(np.isnan(np.asarray(faux["P"], dtype=float))), (
        "le symptome a change : les pressions calculees en mm ne sont plus "
        "des NaN. Le garde-fou de Reynolds ne rattrape donc plus l'erreur, "
        "et une conversion manquante deviendrait silencieuse.")
