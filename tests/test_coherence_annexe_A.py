#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coherence entre la forme en PRESSION du code et la forme en DEBIT de l'annexe A.

Le memoire dont ce depot est issu donne la formulation conique sous forme de
DEBIT a pression imposee, tandis que le code l'implemente sous forme de
PRESSION a debit impose. Les deux doivent etre algebriquement inverses l'une de
l'autre.

Forme du code, apres correction du defaut #8, dans
Velocity_driven.calculateReq._resistance_conique_analytique :

    Delta_P = (2K / (3 n tan(theta))) ((3n+1) Q / (n pi))^n
              (R_sortie^-3n - R_entree^-3n)

Forme de l'annexe A :

    Q = (n pi / (3n+1))
        [ 3 n Delta_P tan(theta)
          / (2 K (R_sortie^-3n - R_entree^-3n)) ]^(1/n)

L'inversion de la premiere donne litteralement la seconde. Ce fichier le
verifie NUMERIQUEMENT, par aller-retour : partir d'un debit, calculer la
pression par le code, reinjecter dans la forme en debit, et retrouver le debit
de depart. Ecart observe : au plus 3.1e-15 en relatif sur 45 combinaisons, soit
la precision machine.

ATTENTION, tan(theta) EST GEOMETRIQUE ET NON DECLARE. La branche conique
analytique du code n'utilise PAS l'argument theta qu'on lui passe : elle
travaille avec L, De et Do, ce qui revient implicitement a

    tan(theta) = (Do - De) / (2 L)

L'aller-retour ne boucle qu'avec cette valeur. Utiliser l'angle declare dans
main.py, 5.3 degres, au lieu des 5.1345 degres qu'impose la geometrie livree,
fait sortir le debit de 3 a 14 pour cent selon n. Voir
test_l_angle_doit_etre_celui_de_la_geometrie.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import pytest                                          # noqa: E402

from tests.test_analytique import delta_P              # noqa: E402
from tools.unites import MILLIMETRE                    # noqa: E402

# Ecart tolere sur l'aller-retour. Trois decades au-dessus du pire ecart
# observe, 3.1e-15, ce qui laisse la marge d'une chaine de quelques dizaines
# d'operations flottantes sans rien masquer d'algebrique.
TOLERANCE_ALLER_RETOUR = 1e-12

# (n, K [Pa.s^n]). Cinq valeurs de n, dont n = 1 ou le defaut #8 etait
# invisible, et les valeurs des materiaux de la base.
LOIS = [(0.2429, 10120.0), (0.3100, 4363.0), (0.4900, 3280.0),
        (0.8000, 120.0), (1.0000, 100.0)]

# (De [mm], Do [mm], L [mm]). Trois geometries, dont celle de main.py.
GEOMETRIES = [(0.45, 3.55, 17.25), (0.25, 1.00, 6.50), (0.60, 2.00, 30.0)]

VITESSES_MM_PAR_S = [10.0, 100.0, 300.0]


def tangente_theta_geometrique(De_m, Do_m, L_m):
    """Tangente du demi-angle du cone, deduite de la GEOMETRIE. [-]

    Le rayon varie lineairement de Do/2 a De/2 sur la longueur L, donc

        tan(theta) = (Do/2 - De/2) / L = (Do - De) / (2 L)

    C'est cette valeur, et elle seule, que la formule du code utilise
    implicitement. L'argument theta de calculateReq n'est pas lu.
    """
    return (Do_m - De_m) / (2.0 * L_m)


def debit_annexe_A(delta_p, K, n, De_m, Do_m, L_m, tan_theta=None):
    """Debit volumique a pression imposee, forme de l'annexe A. [m^3/s]

        Q = (n pi / (3n+1))
            [ 3 n Delta_P tan(theta)
              / (2 K (R_sortie^-3n - R_entree^-3n)) ]^(1/n)

    Args:
        delta_p (float): chute de pression dans la buse, P moins P_amb. [Pa]
        K (float): indice de consistance. [Pa.s^n]
        n (float): indice d'ecoulement. [-]
        De_m, Do_m (float): diametres de sortie et d'entree. [m]
        L_m (float): longueur de buse. [m]
        tan_theta (float): tangente du demi-angle. Geometrique par defaut.

    Returns:
        float: debit volumique. [m^3/s]
    """
    rayon_sortie, rayon_entree = De_m / 2.0, Do_m / 2.0
    if tan_theta is None:
        tan_theta = tangente_theta_geometrique(De_m, Do_m, L_m)
    crochet = (3.0 * n * delta_p * tan_theta
               / (2.0 * K * (rayon_sortie ** (-3.0 * n)
                             - rayon_entree ** (-3.0 * n))))
    return (n * math.pi / (3.0 * n + 1.0)) * crochet ** (1.0 / n)


def debit_impose(De_mm, v_mm_par_s):
    """Debit impose par la vitesse en sortie de buse. [m^3/s]"""
    return math.pi * 0.25 * (De_mm * MILLIMETRE) ** 2 * (v_mm_par_s * MILLIMETRE)


@pytest.mark.parametrize("n, K", LOIS)
@pytest.mark.parametrize("De_mm, Do_mm, L_mm", GEOMETRIES)
@pytest.mark.parametrize("v_mm_par_s", VITESSES_MM_PAR_S)
def test_aller_retour_debit_pression_debit(n, K, De_mm, Do_mm, L_mm,
                                           v_mm_par_s):
    """Q vers Delta_P par le code, puis Delta_P vers Q par l'annexe A.

    Les deux formes doivent etre exactement inverses. Un ecart au-dela de la
    precision machine signalerait qu'un facteur manque ou est en trop dans
    l'une des deux.
    """
    attendu = debit_impose(De_mm, v_mm_par_s)

    chute_de_pression = delta_P(n=n, K=K, De=De_mm, L=L_mm, v=v_mm_par_s,
                                Noz_type="tapered", Do=Do_mm)

    obtenu = debit_annexe_A(chute_de_pression, K, n, De_mm * MILLIMETRE,
                            Do_mm * MILLIMETRE, L_mm * MILLIMETRE)

    assert obtenu == pytest.approx(attendu, rel=TOLERANCE_ALLER_RETOUR), (
        f"\nL'aller-retour ne boucle pas.\n"
        f"  n = {n}, K = {K}, De = {De_mm} mm, Do = {Do_mm} mm, "
        f"L = {L_mm} mm, v = {v_mm_par_s} mm/s\n"
        f"  Delta_P calcule par le code : {chute_de_pression!r} Pa\n"
        f"  Q impose                    : {attendu!r} m^3/s\n"
        f"  Q rendu par l'annexe A      : {obtenu!r} m^3/s\n"
        f"  rapport obtenu sur attendu  : {obtenu / attendu!r}\n"
        "Un rapport constant en n indiquerait un facteur numerique manquant, "
        "un rapport dependant de n un facteur en (3n+1) ou equivalent.")


def test_l_ecart_reste_a_la_precision_machine_sur_toute_la_grille():
    """Recapitulatif : le pire ecart de la grille reste au niveau de l'arrondi.

    Ce test double les precedents, volontairement : il donne en une seule
    valeur l'ordre de grandeur de l'ecart, ce qui rend immediatement visible
    toute derive algebrique future.
    """
    pire = 0.0
    for n, K in LOIS:
        for De_mm, Do_mm, L_mm in GEOMETRIES:
            for v_mm_par_s in VITESSES_MM_PAR_S:
                attendu = debit_impose(De_mm, v_mm_par_s)
                obtenu = debit_annexe_A(
                    delta_P(n=n, K=K, De=De_mm, L=L_mm, v=v_mm_par_s,
                            Noz_type="tapered", Do=Do_mm),
                    K, n, De_mm * MILLIMETRE, Do_mm * MILLIMETRE,
                    L_mm * MILLIMETRE)
                pire = max(pire, abs(obtenu - attendu) / attendu)
    assert pire < 1e-13, (
        f"\nPire ecart de l'aller-retour : {pire:.3e}. Il etait de 3.1e-15 a "
        "l'ecriture de ce test. Une remontee de plusieurs decades indique une "
        "modification algebrique, pas un changement d'arrondi.")


def test_l_angle_doit_etre_celui_de_la_geometrie():
    """tan(theta) se deduit de L, De et Do, il ne se declare pas.

    main.py declare angle = 5.3 degres, mais la geometrie livree,
    De = 0.45 mm, Do = 3.55 mm et L = 17.25 mm, impose 5.1345 degres. La
    branche conique analytique ignore l'argument theta, donc cette
    incoherence est sans effet sur le modele. Elle n'est PAS sans effet sur
    quiconque inverserait le modele avec la forme de l'annexe A en prenant
    l'angle declare : le debit varie comme tan(theta)^(1/n), donc l'ecart
    s'amplifie quand n diminue.
    """
    De_mm, Do_mm, L_mm = 0.45, 3.55, 17.25
    De, Do, L = De_mm * MILLIMETRE, Do_mm * MILLIMETRE, L_mm * MILLIMETRE

    tan_geometrique = tangente_theta_geometrique(De, Do, L)
    assert math.degrees(math.atan(tan_geometrique)) == pytest.approx(
        5.1345, abs=1e-4), "la geometrie livree n'impose plus 5.1345 degres"

    tan_declare = math.tan(math.radians(5.3))
    ecarts = {}
    for n, K in LOIS:
        chute_de_pression = delta_P(n=n, K=K, De=De_mm, L=L_mm, v=100.0,
                                    Noz_type="tapered", Do=Do_mm)
        avec_geometrie = debit_annexe_A(chute_de_pression, K, n, De, Do, L)
        avec_declare = debit_annexe_A(chute_de_pression, K, n, De, Do, L,
                                      tan_theta=tan_declare)
        ecarts[n] = avec_declare / avec_geometrie - 1.0

    # Le rapport vaut (tan_declare / tan_geometrique)^(1/n), donc il croit
    # quand n diminue.
    for n, ecart in ecarts.items():
        attendu = (tan_declare / tan_geometrique) ** (1.0 / n) - 1.0
        assert ecart == pytest.approx(attendu, rel=1e-9)

    assert ecarts[1.0] == pytest.approx(0.0324, abs=1e-3)
    assert ecarts[0.2429] == pytest.approx(0.1403, abs=1e-3)


@pytest.mark.parametrize("n, K", LOIS)
def test_facteur_du_defaut_8_sur_le_debit(n, K):
    """A pression imposee, le defaut #8 vaut (3n+1)^((1-n)/n) sur le debit.

    OBSERVATION #24 du registre. La resistance fautive valait
    Ri_faux = Ri_juste (3n+1)^(1-n). A DEBIT impose, Delta_P etait donc
    surestimee de ce facteur. A PRESSION imposee, l'inversion eleve l'erreur a
    la puissance 1/n :

        Q_juste / Q_faux = (3n+1)^((1-n)/n)

    soit 2.56 pour n = 0.49 et 4.32 pour n = 0.31, contre 1.59 et 1.57 sur la
    pression. Ce test reproduit la formule fautive SUR PLACE, il ne remet
    aucun defaut dans le code.
    """
    De_mm, Do_mm, L_mm = 0.45, 3.55, 17.25
    De, Do, L = De_mm * MILLIMETRE, Do_mm * MILLIMETRE, L_mm * MILLIMETRE
    chute_de_pression = delta_P(n=n, K=K, De=De_mm, L=L_mm, v=100.0,
                                Noz_type="tapered", Do=Do_mm)

    # Forme fautive de l'annexe A : K est remplace par K (3n+1)^(1-n), ce qui
    # reproduit exactement la resistance d'avant la correction du defaut #8.
    facteur_sur_la_pression = (3.0 * n + 1.0) ** (1.0 - n)
    debit_faux = debit_annexe_A(chute_de_pression,
                                K * facteur_sur_la_pression, n, De, Do, L)
    debit_juste = debit_annexe_A(chute_de_pression, K, n, De, Do, L)

    attendu = (3.0 * n + 1.0) ** ((1.0 - n) / n)
    assert debit_juste / debit_faux == pytest.approx(attendu, rel=1e-12), (
        f"n = {n} : rapport {debit_juste / debit_faux!r}, "
        f"attendu (3n+1)^((1-n)/n) = {attendu!r}")
