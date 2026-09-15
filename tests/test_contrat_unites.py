#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verrou entre le defaut #9 et la table de facteurs d'unites.

La table de tests/contrat_unites.py attache un facteur de conversion a chaque
champ enregistre dans les references. Ces facteurs sont ceux de la GRANDEUR
REELLEMENT CONTENUE dans le champ, laquelle ne correspond pas au nom du champ
a cause du defaut #9.

Ce test verifie a l'execution que la correspondance declaree est bien celle du
code. Il compare, sur un cas reel, ce que main.compute_pressures range dans
chaque champ avec ce que Velocity_driven.generateP rend a la position
declaree. L'egalite exigee est bit a bit.

Il echoue dans les deux sens :
  - si le defaut #9 est corrige sans mettre la table a jour ;
  - si la table est modifiee sans que le code ne le soit.

C'est le seul endroit de cette refonte ou une erreur pourrait passer
inapercue, d'ou ce verrou.

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

from tests.contrat_unites import (                      # noqa: E402
    CONTRAT, GRANDEURS_RENDUES_PAR_GENERATEP)
from tests.reference_io import CHAMPS_NUMERIQUES, make_D  # noqa: E402
from tools.unites import entrees_vers_si                # noqa: E402

# Un cas par branche du modele, pour que le verrou porte sur toutes.
CAS = [
    ("cylindrique", dict(Noz_type="cylindrical", n=0.49, K=3280.0, R=0.0, mP=0.0)),
    ("conique analytique", dict(Noz_type="tapered", n=0.49, K=3280.0, R=0.0, mP=0.0)),
    ("conique empirique", dict(Noz_type="tapered", n=0.3575, K=6673.0,
                               R=1.548459269275235, mP=0.34455727852674917)),
]


def _execute(Noz_type, n, K, R, mP):
    """Rend (sorties de compute_pressures, sorties de generateP) sur un cas."""
    import main                                        # noqa: PLC0415
    from Velocity_driven import generateP              # noqa: PLC0415

    alpha = 3
    D_si, L_si, v_si = entrees_vers_si(
        make_D(0.45, 3.55, alpha, 0.001),
        np.array([17.25, 0.01]),
        np.array([100.0]))
    args = (973.0, D_si, L_si, math.radians(5.3), n, K, 0.0, 0.0, 0.0, 0.0,
            0.0, 101325.0, Noz_type, R, mP)
    with contextlib.redirect_stdout(io.StringIO()):
        dictionnaire = main.compute_pressures(
            args[0], v_si, *args[1:], alpha, False)
        tuple_generateP = generateP.generateP(
            args[0], float(v_si[0]), *args[1:], False)
    return dictionnaire, tuple_generateP


@pytest.mark.parametrize("etiquette, parametres", CAS)
def test_correspondance_champ_grandeur(etiquette, parametres):
    """Chaque champ contient bien la sortie de generateP declaree dans CONTRAT."""
    dictionnaire, tuple_generateP = _execute(**parametres)

    anomalies = []
    for champ, contrat in CONTRAT.items():
        position = contrat["position"]
        if position is None:
            continue
        attendu = np.atleast_1d(np.asarray(tuple_generateP[position],
                                           dtype=float)).ravel()
        obtenu = np.atleast_1d(np.asarray(dictionnaire[champ],
                                          dtype=float)).ravel()
        # main.compute_pressures range une sortie scalaire de generateP dans
        # une ligne de largeur alpha, par diffusion numpy. On diffuse de la
        # meme facon avant de comparer.
        if attendu.shape != obtenu.shape:
            try:
                attendu = np.broadcast_to(attendu, obtenu.shape)
            except ValueError:
                anomalies.append(
                    f"champ {champ!r} : forme {obtenu.shape} contre "
                    f"{attendu.shape} pour generateP[{position}], non "
                    f"diffusables")
                continue
        deux_nan = np.isnan(attendu) & np.isnan(obtenu)
        if not np.all(deux_nan | (attendu == obtenu)):
            anomalies.append(
                f"champ {champ!r}, declare contenir la grandeur "
                f"{contrat['grandeur']!r} rendue en position {position} par "
                f"generateP, ne la contient pas.\n"
                f"      attendu {attendu[:3]}\n      obtenu  {obtenu[:3]}")

    assert not anomalies, (
        f"\nCas {etiquette} : la table de tests/contrat_unites.py ne decrit "
        f"plus le code.\n  " + "\n  ".join(anomalies) +
        "\n\nSi le defaut #9 vient d'etre corrige, mettre a jour CONTRAT dans "
        "LE MEME COMMIT, en reattachant chaque facteur a la grandeur reelle.")


def test_contrat_couvre_tous_les_champs():
    """CONTRAT decrit exactement les champs enregistres dans les references."""
    assert set(CONTRAT) == set(CHAMPS_NUMERIQUES), (
        f"\nchamps sans contrat : {sorted(set(CHAMPS_NUMERIQUES) - set(CONTRAT))}"
        f"\ncontrats orphelins  : {sorted(set(CONTRAT) - set(CHAMPS_NUMERIQUES))}")


def test_positions_declarees_coherentes():
    """Les positions declarees couvrent les 8 sorties de generateP, sans doublon."""
    positions = [c["position"] for c in CONTRAT.values()
                 if c["position"] is not None]
    assert sorted(positions) == list(range(len(GRANDEURS_RENDUES_PAR_GENERATEP)))
    for champ, contrat in CONTRAT.items():
        if contrat["position"] is None:
            continue
        assert (contrat["grandeur"] ==
                GRANDEURS_RENDUES_PAR_GENERATEP[contrat["position"]]), (
            f"champ {champ!r} : grandeur declaree {contrat['grandeur']!r} mais "
            f"la position {contrat['position']} de generateP rend "
            f"{GRANDEURS_RENDUES_PAR_GENERATEP[contrat['position']]!r}")
