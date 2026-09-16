#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verrou du diagnostic tools/nombre_de_bingham.py.

Ce script decide si la phase 7 est necessaire dans son integralite ou si elle
se reduit a l'extension conique. Il doit donc etre verifie, meme s'il vit hors
du chemin de calcul.

Trois controles :
  - il retrouve les chiffres etablis a la main pour Parrafin wax-40%,
    0.0129 pour cent a 10 mm/s et 0.0113 pour cent a 300 mm/s ;
  - ses formules sont coherentes entre elles et avec la definition de la
    correction de Rabinowitsch ;
  - le verdict bascule bien aux bornes annoncees.

Auteurs : contribution de la refonte.
"""

import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import pytest                                          # noqa: E402

from tools.nombre_de_bingham import (                   # noqa: E402
    SEUIL_GOUVERNANT_PAR_DEFAUT, SEUIL_NEGLIGEABLE_PAR_DEFAUT,
    cisaillement_apparent, cisaillement_corrige, contrainte_parietale,
    correction_rabinowitsch, debit_volumique, diagnostic, verdict)

# Parrafin wax-40%, materials.xls. Seul materiau a seuil de la base.
PARRAFIN = dict(K=2850000.0, n=0.04, tau_y=490.0)
GEOMETRIE = dict(De_mm=0.45, L_mm=17.25, Do_mm=3.55)


def test_retrouve_les_chiffres_de_parrafin_wax():
    """Les parts du seuil etablies a la main en phase 5 sont reproduites."""
    lignes = diagnostic(vitesses_mm_par_s=[10.0, 50.0, 100.0, 200.0, 300.0],
                        **PARRAFIN, **GEOMETRIE)
    parts = {l["v_mm_par_s"]: l["part_du_seuil"] for l in lignes}
    attendus = {10.0: 0.000129, 50.0: 0.000121, 100.0: 0.000118,
                200.0: 0.000115, 300.0: 0.000113}
    for vitesse, attendu in attendus.items():
        assert parts[vitesse] == pytest.approx(attendu, rel=5e-3), (
            f"v = {vitesse} mm/s : part du seuil {parts[vitesse]:.6%}, "
            f"attendu {attendu:.6%}")


def test_parrafin_wax_est_declare_negligeable():
    """Le verdict de reference : ce materiau ne teste pas un modele a seuil."""
    lignes = diagnostic(vitesses_mm_par_s=[10.0, 300.0], **PARRAFIN, **GEOMETRIE)
    assert all(l["verdict"] == "seuil negligeable" for l in lignes)
    assert all(l["verdict_entree"] == "seuil negligeable" for l in lignes)


def test_la_part_du_seuil_est_l_ecart_sur_delta_P():
    """f = tau_y / tau_paroi est exactement l'ecart entre avec et sans seuil.

    Delta_P etant proportionnel a tau_paroi, retirer le seuil divise la
    pression par (1 - f). C'est ce qui justifie d'utiliser f comme critere.
    """
    ligne = diagnostic(vitesses_mm_par_s=[100.0], **PARRAFIN, **GEOMETRIE)[0]
    avec_seuil = ligne["tau_paroi"]
    sans_seuil = ligne["tau_visqueux"]
    assert (avec_seuil - sans_seuil) / avec_seuil == pytest.approx(
        ligne["part_du_seuil"], rel=1e-12)


def test_le_cisaillement_corrige_est_bien_le_produit():
    """gamma_corrige = gamma_apparent fois (3n+1)/(4n)."""
    n = 0.31
    Q = debit_volumique(0.45e-3, 0.1)
    apparent = cisaillement_apparent(Q, 0.45e-3)
    corrige = cisaillement_corrige(Q, 0.45e-3, n)
    assert corrige == pytest.approx(apparent * correction_rabinowitsch(n),
                                    rel=1e-15)
    assert correction_rabinowitsch(1.0) == pytest.approx(1.0, rel=1e-15)


def test_cisaillement_apparent_egale_huit_v_sur_D():
    """32 Q / (pi D^3) vaut 8 V / D, ou V est la vitesse debitante."""
    D, v = 0.45e-3, 0.1
    assert cisaillement_apparent(debit_volumique(D, v), D) == pytest.approx(
        8.0 * v / D, rel=1e-14)


def test_en_conique_l_entree_est_plus_sensible_que_la_sortie():
    """Le cisaillement est minimal a l'entree, donc la part du seuil y est maximale."""
    lignes = diagnostic(vitesses_mm_par_s=[100.0], K=4363.0, n=0.31,
                        tau_y=200.0, **GEOMETRIE)
    ligne = lignes[0]
    assert ligne["gamma_corrige_entree"] < ligne["gamma_corrige"]
    assert ligne["part_du_seuil_entree"] > ligne["part_du_seuil"]


@pytest.mark.parametrize("part, attendu", [
    (0.0, "seuil negligeable"),
    (SEUIL_NEGLIGEABLE_PAR_DEFAUT - 1e-9, "seuil negligeable"),
    (SEUIL_NEGLIGEABLE_PAR_DEFAUT, "seuil marginal"),
    (SEUIL_GOUVERNANT_PAR_DEFAUT - 1e-9, "seuil marginal"),
    (SEUIL_GOUVERNANT_PAR_DEFAUT, "SEUIL GOUVERNANT"),
    (1.0, "SEUIL GOUVERNANT"),
])
def test_le_verdict_bascule_aux_bornes(part, attendu):
    assert verdict(part, SEUIL_NEGLIGEABLE_PAR_DEFAUT,
                   SEUIL_GOUVERNANT_PAR_DEFAUT) == attendu


def test_contrainte_parietale_sans_seuil_est_la_loi_de_puissance():
    """tau_y = 0 redonne exactement K gamma^n."""
    tau_paroi, tau_visqueux = contrainte_parietale(3280.0, 0.49, 0.0, 1000.0)
    assert tau_paroi == tau_visqueux
    assert tau_paroi == pytest.approx(3280.0 * 1000.0 ** 0.49, rel=1e-15)


def test_un_seuil_eleve_bascule_le_verdict():
    """Controle que le script sait dire 'gouvernant', pas seulement 'negligeable'."""
    lignes = diagnostic(vitesses_mm_par_s=[10.0], K=4363.0, n=0.31,
                        tau_y=50000.0, **GEOMETRIE)
    assert lignes[0]["verdict"] == "SEUIL GOUVERNANT"
