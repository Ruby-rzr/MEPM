#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifications sur materiaux.xlsx, la base a en-tetes nommes.

Elle remplace materials.xls comme source de verite. materials.xls devient un
artefact gele, dont le sha256 est l'ancre d'integrite des references
historiques et qui n'est plus lu que par tools/readMaterial.py.

Auteurs : contribution de la refonte.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import pandas as pd                                    # noqa: E402
import pytest                                          # noqa: E402

from Velocity_driven.modeles import (                   # noqa: E402
    ANALYTIQUE, EMPIRIQUE, MODELES, MODES, deduire_modele_historique)
from tools.creer_base_materiaux import COLONNES        # noqa: E402
from tools.lireMateriaux import (                       # noqa: E402
    BASE_MATERIAUX, CLES_INCERTITUDES, lireMateriau, materiaux_disponibles)

NOMS = materiaux_disponibles()


def test_toutes_les_colonnes_attendues_sont_presentes():
    table = pd.read_excel(BASE_MATERIAUX, sheet_name="materiaux")
    assert list(table.columns) == COLONNES


def test_chaque_parametre_a_sa_colonne_d_incertitude():
    """Une incertitude est une propriete du materiau, pas une constante du code."""
    table = pd.read_excel(BASE_MATERIAUX, sheet_name="materiaux")
    manquantes = [f"d_{cle}" for cle in CLES_INCERTITUDES
                  if f"d_{cle}" not in table.columns]
    assert not manquantes, f"colonnes d'incertitude manquantes : {manquantes}"


def test_la_base_couvre_les_memes_materiaux_que_l_ancienne():
    ancienne = pd.ExcelFile(os.path.join(RACINE, "materials.xls")).sheet_names
    assert NOMS == ancienne


@pytest.mark.parametrize("nom", NOMS)
def test_materiau_lisible_et_declare(nom):
    """Chaque materiau se lit, declare un modele, un mode et une provenance."""
    materiau = lireMateriau(nom)
    assert materiau["modele"] in MODELES
    assert materiau["mode"] in MODES
    assert materiau["provenance"], f"{nom} n'a pas de provenance"
    assert set(materiau["incertitudes"]) == set(CLES_INCERTITUDES)


@pytest.mark.parametrize("nom", NOMS)
def test_modele_declare_egale_le_modele_deduit(nom):
    """Le modele declare est celui que l'ancienne cascade aurait devine.

    C'est le seul controle possible aujourd'hui : la base a ete construite
    depuis l'ancienne, ou le modele n'etait pas ecrit. Il garantit qu'aucune
    loi n'a ete changee au passage. Un materiau ajoute plus tard declarera sa
    loi sans que ce test ait quoi que ce soit a dire, ce qui est le but.
    """
    materiau = lireMateriau(nom)
    deduit = deduire_modele_historique(
        materiau["n"], materiau["K"], materiau["eta_inf"], materiau["eta_0"],
        materiau["tau_0"], materiau["lambda"], materiau["a"])
    assert materiau["modele"] == deduit


@pytest.mark.parametrize("nom", NOMS)
def test_aucun_ajustement_de_provenance_inconnue_n_est_utilise(nom):
    """Un mP ou un R present exige une provenance et un mode coherent.

    Decision de la phase 5 : aucun parametre ajuste de provenance inconnue
    n'alimente un resultat. Tous les materiaux de la base sont donc en mode
    analytique, les valeurs mP et R etant conservees sans etre utilisees.
    """
    materiau = lireMateriau(nom)
    if materiau["mP"] != 0.0 or materiau["R"] != 0.0:
        assert materiau["provenance_ajustement"], (
            f"{nom} porte mP ou R sans provenance d'ajustement")
    if materiau["mode"] == EMPIRIQUE:
        assert materiau["mP"] != 0.0 and materiau["R"] != 0.0, (
            f"{nom} est declare empirique sans les deux parametres ajustes")
        assert "INCONNUE" not in materiau["provenance_ajustement"], (
            f"{nom} est declare empirique avec un ajustement de provenance "
            "inconnue, ce que la phase 5 interdit")
    else:
        assert materiau["mode"] == ANALYTIQUE
