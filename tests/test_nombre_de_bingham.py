#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verrou du diagnostic tools/nombre_de_bingham.py.

Ce script decide si la phase 7 est necessaire dans son integralite ou si elle
se reduit a l'extension conique. Il doit donc etre verifie, meme s'il vit hors
du chemin de calcul.

Controles :
  - il retrouve les chiffres etablis a la main pour Parrafin wax-40%,
    0.0129 pour cent a 10 mm/s et 0.0113 pour cent a 300 mm/s ;
  - il retrouve les trois valeurs du cas EC3515-8% a 120 Pa de seuil,
    0.4789 pour cent en sortie, 3.1810 pour cent en entree et 1.0715 pour cent
    en ponderee, ainsi que les 78.3 pour cent de Delta_P accumules dans le
    tiers cote sortie ;
  - l'integration numerique converge vers la forme fermee de l'integrale ;
  - SUR UNE BUSE CYLINDRIQUE, la ponderee, la valeur en sortie et le maximum
    COINCIDENT, la section etant constante. C'est le controle de coherence ;
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
    FRACTION_LONGUEUR_COTE_SORTIE, SEUIL_GOUVERNANT_PAR_DEFAUT,
    SEUIL_NEGLIGEABLE_PAR_DEFAUT, cisaillement_apparent, cisaillement_corrige,
    contrainte_parietale, correction_rabinowitsch, debit_volumique, diagnostic,
    part_du_seuil_ponderee, verdict)

# Cas de reference du critere pondere : EC3515-8% avec un seuil hypothetique.
EPOXY_A_SEUIL = dict(K=4363.0, n=0.31, tau_y=120.0)


def integrale_fermee(K, n, tau_y, Q, R1, R2):
    """Integrale de dP/dz entre deux rayons, forme fermee.

    dP/dz = 2 tau_w(R)/R avec tau_w = tau_y + K (A R^-3)^n et
    A = ((3n+1)/n) Q/pi. A un facteur constant pres, commun au numerateur et au
    denominateur de tout rapport,

        integrale = tau_y ln(R2/R1) + (K A^n / 3n) (R1^-3n - R2^-3n)

    C'est une integration elementaire de l'expression deja etablie dans le
    depot, utilisee ici comme oracle independant de l'integration numerique.
    """
    A = ((3 * n + 1) / n) * Q / math.pi
    return (tau_y * math.log(R2 / R1)
            + (K * A ** n / (3 * n)) * (R1 ** (-3 * n) - R2 ** (-3 * n)))

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
    # Meme la part la plus defavorable, celle de l'entree, reste negligeable.
    assert all(l["part_du_seuil_entree"] < SEUIL_NEGLIGEABLE_PAR_DEFAUT
               for l in lignes)


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


def test_retrouve_les_trois_valeurs_du_cas_epoxy_a_seuil():
    """Sortie, entree et ponderee sur EC3515-8% avec tau_y = 120 Pa a 10 mm/s."""
    ligne = diagnostic(vitesses_mm_par_s=[10.0], **EPOXY_A_SEUIL,
                       **GEOMETRIE)[0]
    assert ligne["part_du_seuil"] == pytest.approx(0.004789, rel=1e-3)
    assert ligne["part_du_seuil_entree"] == pytest.approx(0.031810, rel=1e-3)
    assert ligne["part_du_seuil_ponderee"] == pytest.approx(0.010715, rel=1e-3)
    assert ligne["fraction_delta_P_cote_sortie"] == pytest.approx(0.7830,
                                                                  rel=1e-3)
    assert ligne["verdict"] == "seuil marginal"


def test_la_ponderee_est_encadree_par_la_sortie_et_l_entree():
    """La moyenne ponderee ne peut pas sortir de l'intervalle des extremites."""
    for vitesse in (10.0, 100.0, 300.0):
        ligne = diagnostic(vitesses_mm_par_s=[vitesse], **EPOXY_A_SEUIL,
                           **GEOMETRIE)[0]
        assert (ligne["part_du_seuil"] <= ligne["part_du_seuil_ponderee"]
                <= ligne["part_du_seuil_entree"]), (
            f"v = {vitesse} : ponderee hors de l'encadrement")


def test_le_verdict_porte_sur_la_ponderee_et_non_sur_le_maximum():
    """Le maximum dirait 'marginal' la ou la ponderee dit 'negligeable'.

    C'est tout l'objet de la correction : la part elevee de l'entree s'applique
    a une portion de buse qui ne pese presque rien dans Delta_P.
    """
    ligne = diagnostic(vitesses_mm_par_s=[10.0], K=4363.0, n=0.31, tau_y=50.0,
                       **GEOMETRIE)[0]
    assert ligne["part_du_seuil_maximale"] > SEUIL_NEGLIGEABLE_PAR_DEFAUT
    assert ligne["part_du_seuil_ponderee"] < SEUIL_NEGLIGEABLE_PAR_DEFAUT
    assert ligne["verdict"] == "seuil negligeable"


def test_sur_une_buse_cylindrique_les_trois_valeurs_coincident():
    """CONTROLE DE COHERENCE. Section constante, donc aucune ponderation."""
    for vitesse in (10.0, 100.0, 300.0):
        ligne = diagnostic(vitesses_mm_par_s=[vitesse], **EPOXY_A_SEUIL,
                           De_mm=0.45, L_mm=17.25, Do_mm=None)[0]
        assert ligne["part_du_seuil_entree"] == pytest.approx(
            ligne["part_du_seuil"], rel=1e-14)
        assert ligne["part_du_seuil_maximale"] == pytest.approx(
            ligne["part_du_seuil"], rel=1e-14)
        assert ligne["part_du_seuil_ponderee"] == pytest.approx(
            ligne["part_du_seuil"], rel=1e-12), (
            f"v = {vitesse} : la ponderee devrait egaler la valeur en sortie "
            "sur une section constante")
        assert ligne["fraction_delta_P_cote_sortie"] == pytest.approx(
            FRACTION_LONGUEUR_COTE_SORTIE, rel=1e-12), (
            "sur une section constante, le tiers de la longueur porte le "
            "tiers de Delta_P")


def test_l_integration_numerique_converge_vers_la_forme_fermee():
    """L'oracle est l'integrale analytique, independante du maillage."""
    K, n, tau_y = EPOXY_A_SEUIL["K"], EPOXY_A_SEUIL["n"], EPOXY_A_SEUIL["tau_y"]
    De, Do = 0.45e-3, 3.55e-3
    Q = debit_volumique(De, 0.010)
    rayon_sortie, rayon_entree = De / 2, Do / 2

    total = integrale_fermee(K, n, tau_y, Q, rayon_sortie, rayon_entree)
    attendu_ponderee = tau_y * math.log(rayon_entree / rayon_sortie) / total
    rayon_tiers = rayon_entree + (rayon_sortie - rayon_entree) * (
        1.0 - FRACTION_LONGUEUR_COTE_SORTIE)
    attendu_fraction = integrale_fermee(
        K, n, tau_y, Q, rayon_sortie, rayon_tiers) / total

    ponderee, fraction = part_du_seuil_ponderee(
        K, n, tau_y, Q, rayon_sortie, rayon_entree)
    assert ponderee == pytest.approx(attendu_ponderee, rel=1e-5)
    assert fraction == pytest.approx(attendu_fraction, rel=1e-5)

    # Convergence quadratique : quadrupler les tranches divise l'ecart par
    # environ quatre. On exige au moins un facteur trois.
    ecart = [abs(part_du_seuil_ponderee(K, n, tau_y, Q, rayon_sortie,
                                        rayon_entree, tranches=N)[0]
                 - attendu_ponderee) for N in (250, 1000)]
    assert ecart[0] > 3 * ecart[1], (
        f"convergence trop lente : {ecart[0]:.3e} puis {ecart[1]:.3e}")


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


def test_la_chute_de_pression_se_concentre_cote_sortie():
    """Le gradient variant comme R^(-3n-1), le tiers cote sortie domine."""
    ligne = diagnostic(vitesses_mm_par_s=[10.0], **EPOXY_A_SEUIL,
                       **GEOMETRIE)[0]
    assert ligne["fraction_delta_P_cote_sortie"] > 0.5, (
        "sur cette geometrie, le tiers cote sortie doit porter la majorite de "
        "Delta_P, c'est ce qui justifie la ponderation")


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
