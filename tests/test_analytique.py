#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests analytiques du MEPM, phase 3 de la refonte.

Ces tests confrontent le modele a des solutions analytiques connues. Ils ne
corrigent rien : aucune ligne de physique n'a ete modifiee pour les ecrire.

Un test dont on sait qu'il echoue est marque xfail(strict=True) avec une
raison nommant le defaut concerne. La suite reste verte, l'echec est
documente, et si un jour il se met a passer sans decision explicite, pytest le
signale comme une erreur. C'est ce mecanisme qui se declenchera en phase 7.

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

from tests.reference_io import make_D                  # noqa: E402
from tools.unites import MILLIMETRE, entrees_vers_si    # noqa: E402

P_AMB = 101325.0
RHO = 973.0
ANGLE_DEG = 5.3          # ignore par la branche conique analytique
ERREUR_D = 0.001


def delta_P(n, K, De, L, v, Noz_type="cylindrical", Do=3.55, alpha=1,
            eta_inf=0.0, eta_0=0.0, tau_0=0.0, lmbda=0.0, a=0.0):
    """Chute de pression rendue par le modele, P_amb deduit.

    Args:
        n (float): indice d'ecoulement. [-]
        K (float): indice de consistance. [Pa.s^n]
        De (float): diametre de sortie de buse. [mm]
        L (float): longueur de buse. [mm]
        v (float): vitesse en sortie de buse. [mm/s]
        Noz_type (str): "tapered" ou "cylindrical".
        Do (float): diametre d'entree, utilise en conique. [mm]
        alpha (int): nombre de buses identiques.

    Returns:
        float: Delta_P = P - P_amb. [Pa]

    Les arguments geometriques sont exprimes en mm, comme une buse se mesure
    a l'atelier. La conversion vers le SI a lieu ici, par la meme frontiere
    que celle de main.py, et le modele appele travaille en SI strict.
    """
    import main                                        # noqa: PLC0415
    D_si, L_si, v_si = entrees_vers_si(
        make_D(De, Do, alpha, ERREUR_D),
        np.array([float(L), 0.01]),
        np.array([float(v)]))
    with contextlib.redirect_stdout(io.StringIO()):
        resultat = main.compute_pressures(
            RHO, v_si, D_si, L_si, math.radians(ANGLE_DEG), n, K, eta_0,
            eta_inf, tau_0, lmbda, a, P_AMB, Noz_type, 0.0, 0.0, alpha, False)
    return float(resultat["P"][0]) - P_AMB


def en_metres(longueur_mm):
    """Longueur de mm vers m, pour ecrire les solutions analytiques en SI."""
    return float(longueur_mm) * MILLIMETRE


def debit(De_mm, v_mm_par_s):
    """Debit volumique d'une buse, a partir de grandeurs en mm. [m^3/s]"""
    return (math.pi * 0.25 * en_metres(De_mm) ** 2
            * en_metres(v_mm_par_s))


# ---------------------------------------------------------------------------
# T1. Newtonien contre Hagen-Poiseuille
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("eta, De, L, v", [
    (100.0, 0.45, 17.25, 100.0),
    (12.5, 0.25, 6.5, 50.0),
    (2500.0, 0.60, 30.0, 10.0),
])
def test_T1_newtonien_hagen_poiseuille(eta, De, L, v):
    """Un fluide newtonien en conduite cylindrique doit donner Hagen-Poiseuille.

    Delta_P = 128 eta L Q / (pi D^4)

    Pour n = 1, le facteur de Weissenberg-Rabinowitsch (3 + 1/n)/4 vaut 1 :
    la chaine du modele doit se reduire exactement a Hagen-Poiseuille.
    """
    obtenu = delta_P(n=1.0, K=0.0, De=De, L=L, v=v, eta_inf=eta)
    attendu = (128 * eta * en_metres(L) * debit(De, v)
               / (math.pi * en_metres(De) ** 4))
    assert obtenu == pytest.approx(attendu, rel=1e-12), (
        f"\nHagen-Poiseuille : attendu {attendu!r}, obtenu {obtenu!r}, "
        f"ecart relatif {(obtenu - attendu) / attendu:.3e}")


# ---------------------------------------------------------------------------
# T2. Loi de puissance en cylindre, garde-fou du double facteur de Rabinowitsch
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n, K, De, L, v", [
    (0.49, 3280.0, 0.45, 17.25, 100.0),
    (0.31, 4363.0, 0.25, 6.5, 50.0),
    (0.3575, 6673.0, 0.25, 6.5, 250.0),
    (0.8, 120.0, 0.60, 30.0, 10.0),
])
def test_T2_loi_de_puissance_cylindre(n, K, De, L, v):
    """Loi de puissance en conduite cylindrique : Delta_P = 4 L K gamma_w^n / D.

    avec gamma_w = ((3n+1)/(4n)) * 32 Q / (pi D^3).

    CE TEST EST LE GARDE-FOU DU DOUBLE FACTEUR DE RABINOWITSCH decrit dans
    CLAUDE.md. Le facteur (3 + 1/n)/4 est applique DEUX FOIS dans la chaine
    cylindrique, volontairement :
      - une fois sur le taux de cisaillement, dans calculateSR
        (Chauvette 2023, section 4.3.1.1, equation 4.2, referencee [38]) ;
      - une fois sur la resistance hydraulique, dans calculateReq
        (meme section, equation 4.4, meme reference).

    Ce n'est pas un doublon : la composition des deux redonne exactement la
    solution analytique ci-dessus. Supprimer l'une des deux occurrences ne
    provoque aucune erreur visible et fausse tous les resultats d'un facteur
    dependant de n. Si ce test echoue, quelque chose a ete casse, et il faut
    le reparer avant toute autre chose.
    """
    Q = debit(De, v)
    gamma_w = ((3 * n + 1) / (4 * n)) * 32 * Q / (math.pi * en_metres(De) ** 3)
    attendu = 4 * en_metres(L) * K * gamma_w ** n / en_metres(De)
    obtenu = delta_P(n=n, K=K, De=De, L=L, v=v)
    assert obtenu == pytest.approx(attendu, rel=1e-12), (
        f"\nDouble facteur de Rabinowitsch rompu.\n"
        f"  attendu {attendu!r}\n  obtenu  {obtenu!r}\n"
        f"  ecart relatif {(obtenu - attendu) / attendu:.3e}\n"
        f"  rapport {obtenu / attendu!r}, comparer a (3n+1)/(4n) = "
        f"{(3 * n + 1) / (4 * n)!r}")


# ---------------------------------------------------------------------------
# T3. Invariants d'echelle
# ---------------------------------------------------------------------------

EXPOSANTS_N = [0.2429, 0.31, 0.49, 0.8, 1.0]


def exposant_mesure(valeur_base, valeur_doublee):
    """Exposant p tel que valeur_doublee = valeur_base * 2^p."""
    return math.log(valeur_doublee / valeur_base) / math.log(2.0)


@pytest.mark.parametrize("n", EXPOSANTS_N)
def test_T3_invariants_echelle(n):
    """Exposants d'echelle de Delta_P en cylindrique loi de puissance.

    Delta_P proportionnel a L^1 * K^1 * Q^n * D^(-3n-1).

    Ces invariants sont sans unites : ils testent la structure de la relation
    sans rien supposer sur le systeme d'unites. C'est plus informatif qu'un
    test de changement d'unites, impossible aujourd'hui puisque les mm sont
    partout en dur (defaut #3, traite en phase 4).

    Le debit est impose par la vitesse, Q = pi D^2 v / 4. Pour doubler Q a
    diametre fixe on double v. Pour doubler D a debit fixe on divise v par 4.
    """
    K, De, L, v = 3280.0, 0.45, 17.25, 100.0
    base = delta_P(n=n, K=K, De=De, L=L, v=v)

    mesures = {
        "L": (exposant_mesure(base, delta_P(n=n, K=K, De=De, L=2 * L, v=v)), 1.0),
        "K": (exposant_mesure(base, delta_P(n=n, K=2 * K, De=De, L=L, v=v)), 1.0),
        "Q": (exposant_mesure(base, delta_P(n=n, K=K, De=De, L=L, v=2 * v)), n),
        "D": (exposant_mesure(base, delta_P(n=n, K=K, De=2 * De, L=L, v=v / 4)),
              -3 * n - 1),
    }
    anomalies = [f"exposant sur {grandeur} : mesure {mesure!r}, attendu "
                 f"{attendu!r}, ecart {abs(mesure - attendu):.3e}"
                 for grandeur, (mesure, attendu) in mesures.items()
                 if abs(mesure - attendu) > 1e-10]
    assert not anomalies, f"\nn = {n} :\n  " + "\n  ".join(anomalies)


# ---------------------------------------------------------------------------
# T4. Mise en parallele de buses identiques
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("Noz_type", ["cylindrical", "tapered"])
@pytest.mark.parametrize("n, K", [(0.49, 3280.0), (0.31, 4363.0), (1.0, 100.0)])
def test_T4_mise_en_parallele_buses_identiques(Noz_type, n, K):
    """alpha buses identiques en parallele donnent le meme Delta_P qu'une seule.

    C'est l'annulation des alpha demontree par Chauvette 2023 sous l'equation
    4.6 : la resistance equivalente est divisee par alpha, le debit total est
    multiplie par alpha, le produit est invariant.

    Le test ne dit rien du cas des buses NON identiques, ou la moyenne
    utilisee en conique et la somme des inverses utilisee en cylindrique ne
    resolvent pas le reseau (defaut #4).
    """
    une = delta_P(n=n, K=K, De=0.45, L=17.25, v=100.0,
                  Noz_type=Noz_type, alpha=1)
    trente_six = delta_P(n=n, K=K, De=0.45, L=17.25, v=100.0,
                         Noz_type=Noz_type, alpha=36)
    assert trente_six == pytest.approx(une, rel=1e-12), (
        f"\nalpha = 1 donne {une!r}, alpha = 36 donne {trente_six!r}, "
        f"ecart relatif {(trente_six - une) / une:.3e}")


# ---------------------------------------------------------------------------
# T5. Continuite conique vers cylindrique
# ---------------------------------------------------------------------------

# Suite decroissante de Do/De - 1. Deux sources d'erreur s'opposent :
#   - l'erreur d'approche de la limite, en O(delta) ;
#   - l'annulation catastrophique, la formule contenant (Do - De) au
#     denominateur et une difference de deux puissances voisines au
#     numerateur, en O(eps / (3 n delta)).
# Leur somme est minimale vers delta = sqrt(eps / 3n), soit environ 1.2e-8.
DELTAS = [5e-1, 2e-1, 1e-1, 5e-2, 2e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4,
          1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10, 1e-11, 1e-12, 1e-13, 1e-14]

# Tolerance d'accord des rapports a l'interieur d'une fenetre de plateau.
# Elle est encadree par deux ordres de grandeur mesures :
#   - 1e-7 : dispersion effectivement observee au plateau, donc la tolerance
#     lui laisse deux decades de marge et ne coupe aucun plateau reel ;
#   - 0.28 : plus petit ecart a demontrer, celui de n = 0.8 pour lequel
#     (3n+1)^(1-n) vaut 1.277. La tolerance est plus de quatre decades en
#     dessous, donc elle ne peut pas masquer le defaut recherche.
TOLERANCE_PLATEAU = 1e-5

# Un plateau est retenu a partir de trois points. Les plateaux reellement
# observes en font cinq a six, la marge est donc reelle.
LARGEUR_PLATEAU_MINIMALE = 3


def rapports_conique_sur_cylindrique(n, K, De=0.45, L=17.25, v=100.0):
    """Rapport Delta_P conique sur Delta_P cylindrique, pour chaque delta."""
    reference = delta_P(n=n, K=K, De=De, L=L, v=v, Noz_type="cylindrical")
    return [delta_P(n=n, K=K, De=De, L=L, v=v, Noz_type="tapered",
                    Do=De * (1 + d)) / reference for d in DELTAS]


def detecte_plateau(rapports):
    """Plus longue fenetre contigue ou les rapports s'accordent.

    Returns:
        (indice_debut, indice_fin_exclu, valeur_du_plateau) ou None si aucune
        fenetre d'au moins LARGEUR_PLATEAU_MINIMALE points ne tient dans
        TOLERANCE_PLATEAU. Dans ce cas l'appelant doit refuser de conclure.
    """
    meilleure = None
    for debut in range(len(rapports)):
        for fin in range(debut + LARGEUR_PLATEAU_MINIMALE, len(rapports) + 1):
            fenetre = rapports[debut:fin]
            if max(fenetre) - min(fenetre) > TOLERANCE_PLATEAU:
                break
            if meilleure is None or (fin - debut) > (meilleure[1] - meilleure[0]):
                meilleure = (debut, fin)
    if meilleure is None:
        return None
    debut, fin = meilleure
    return debut, fin, float(np.median(rapports[debut:fin]))


N_CONIQUES = [0.31, 0.49, 0.8]


@pytest.mark.xfail(strict=True,
                   reason="defaut #8 : priorite d'operateurs dans "
                          "calculateReq, le conique analytique est entache "
                          "d'un facteur (3n+1)^(1-n)")
@pytest.mark.parametrize("n, K", [(0.31, 4363.0), (0.49, 3280.0), (0.8, 120.0)])
def test_T5_continuite_conique_vers_cylindrique(n, K):
    """Quand l'angle tend vers zero, le conique doit rejoindre le cylindrique.

    A longueur et diametre de sortie fixes, on fait tendre Do vers De et on
    compare au resultat cylindrique. Le rapport attendu est 1, et c'est la
    VALEUR du rapport qui est testee, pas la seule convergence.

    ECHEC ATTENDU. Le rapport atteint un plateau a (3n+1)^(1-n), soit environ
    1.57 a 1.28 selon n, a cause du defaut #8 : dans calculateReq, l'ecriture

        ((3*n+1)/(n*np.pi)
                          ** n)

    lie l'exposant n au seul denominateur (n*pi) et non a la fraction entiere.
    Le code calcule (3n+1)/(n pi)^n au lieu de ((3n+1)/(n pi))^n.
    """
    rapports = rapports_conique_sur_cylindrique(n, K)
    plateau = detecte_plateau(rapports)
    assert plateau is not None, (
        "\nAucun plateau separable du bruit numerique n'a ete trouve pour "
        f"n = {n}. Refus de conclure.\n  rapports : {rapports}")
    debut, fin, valeur = plateau
    assert valeur == pytest.approx(1.0, rel=TOLERANCE_PLATEAU), (
        f"\nn = {n} : le conique ne rejoint pas le cylindrique.\n"
        f"  plateau sur Do/De - 1 dans [{DELTAS[fin - 1]:.0e}, "
        f"{DELTAS[debut]:.0e}], {fin - debut} points\n"
        f"  rapport observe : {valeur!r}\n"
        f"  (3n+1)^(1-n)    : {(3 * n + 1) ** (1 - n)!r}\n"
        f"  ecart entre les deux : "
        f"{abs(valeur - (3 * n + 1) ** (1 - n)) / (3 * n + 1) ** (1 - n):.3e}")


GEOMETRIES_BALAYEES = [(De, L, v)
                       for De in (0.25, 0.45, 0.60)
                       for L in (6.5, 17.25, 30.0)
                       for v in (10.0, 100.0, 250.0)]


@pytest.mark.parametrize("n, K", [(0.31, 4363.0), (0.49, 3280.0), (0.8, 120.0)])
def test_T5bis_le_rapport_ne_depend_que_de_n(n, K):
    """Le rapport conique sur cylindrique vaut (3n+1)^(1-n) et ne depend que de n.

    Ce test ne valide rien physiquement. Il epingle quantitativement le
    defaut #8 : tant qu'il passe, l'ecart observe est entierement explique par
    la priorite d'operateurs, et par rien d'autre.

    L'independance vis-a-vis de v, De et L est le point qui distingue une
    ERREUR D'ECRITURE d'une ERREUR DE DERIVATION. Une formule mal derivee
    laisserait en general une dependance residuelle en geometrie ou en debit.
    Ici le rapport est rigoureusement constant sur les 27 combinaisons
    balayees, a la dispersion du plateau pres.

    Quand le defaut sera corrige, ce test echouera, ce qui obligera a
    constater la correction plutot qu'a la subir. Il sera retourne en meme
    temps que le xfail de test_T5 sera leve, en phase 7, pas avant.
    """
    attendu = (3 * n + 1) ** (1 - n)
    observes = {}
    for De, L, v in GEOMETRIES_BALAYEES:
        plateau = detecte_plateau(
            rapports_conique_sur_cylindrique(n, K, De=De, L=L, v=v))
        assert plateau is not None, (
            f"aucun plateau separable du bruit pour n = {n}, "
            f"De = {De}, L = {L}, v = {v}. Refus de conclure.")
        observes[(De, L, v)] = plateau[2]

    hors_tolerance = {
        cle: valeur for cle, valeur in observes.items()
        if abs(valeur - attendu) / attendu > TOLERANCE_PLATEAU}
    assert not hors_tolerance, (
        f"\nn = {n} : (3n+1)^(1-n) = {attendu!r}\n  " + "\n  ".join(
            f"De={De} L={L} v={v} : {valeur!r}, ecart "
            f"{abs(valeur - attendu) / attendu:.3e}"
            for (De, L, v), valeur in sorted(hors_tolerance.items())))

    dispersion = max(observes.values()) - min(observes.values())
    assert dispersion <= TOLERANCE_PLATEAU * attendu, (
        f"\nn = {n} : le rapport n'est pas independant de la geometrie et du "
        f"debit, dispersion {dispersion:.3e} sur "
        f"{len(observes)} combinaisons (De, L, v).\n"
        "Une dependance residuelle indiquerait une erreur de derivation et "
        "non une simple erreur d'ecriture.")


def test_T5ter_continuite_conique_exacte_pour_n_egal_1():
    """Pour n = 1, le facteur parasite vaut 1 et la continuite est exacte.

    (3n+1)^(1-n) vaut 1 quand n vaut 1. C'est la demonstration que le
    defaut #8 depend de n : un test purement newtonien ne l'aurait jamais
    detecte. Ce test passe aujourd'hui et doit continuer a passer apres la
    correction.
    """
    plateau = detecte_plateau(rapports_conique_sur_cylindrique(1.0, 100.0))
    assert plateau is not None
    _, _, valeur = plateau
    assert valeur == pytest.approx(1.0, rel=TOLERANCE_PLATEAU), (
        f"rapport observe pour n = 1 : {valeur!r}")


# ---------------------------------------------------------------------------
# T6. Continuite du seuil
# ---------------------------------------------------------------------------

TAU_0_DECROISSANTS = [1.0, 1e-2, 1e-4, 1e-6, 1e-8]


@pytest.mark.parametrize("n, K", [(0.49, 3280.0), (0.31, 4363.0), (0.04, 2850000.0)])
def test_T6_continuite_du_seuil(n, K):
    """Herschel-Bulkley avec tau_0 tendant vers zero rejoint la loi de puissance.

    CE TEST NE VALIDE RIEN POUR tau_0 > 0. Il est trivialement satisfait : la
    branche Herschel-Bulkley de calculateVisco calcule
    eta = tau_0/gamma + K gamma^(n-1), qui se reduit litteralement a la loi de
    puissance quand tau_0 s'annule. Tout l'aval est alors identique.

    Le defaut #7 est ailleurs et ce test ne peut pas le voir. La chaine donne

        Delta_P = 4 L (tau_0 + K gamma_w^n) / D

    ou le bilan de forces et la loi de comportement sont exacts, mais ou
    gamma_w est obtenu de Q par la correction de Weissenberg-Rabinowitsch de
    la LOI DE PUISSANCE, (3n+1)/(4n). Pour un fluide a seuil, l'exposant local
    n' = dln(tau_w)/dln(gamma_apparent) n'est pas n et depend du nombre de
    Bingham : le bouchon central est ignore.

    Quantifier cette erreur demande la solution exacte de l'ecoulement
    Herschel-Bulkley en conduite. Elle ne sera pas ecrite ici : c'est l'objet
    de la phase 7, sur la base des equations de reference fournies a ce
    moment-la.
    """
    reference = delta_P(n=n, K=K, De=0.45, L=17.25, v=100.0)
    ecarts = [abs(delta_P(n=n, K=K, De=0.45, L=17.25, v=100.0, tau_0=t)
                  - reference) / reference for t in TAU_0_DECROISSANTS]
    non_decroissants = [(TAU_0_DECROISSANTS[i], ecarts[i], ecarts[i + 1])
                        for i in range(len(ecarts) - 1)
                        if ecarts[i + 1] > ecarts[i]]
    assert not non_decroissants, (
        f"\nn = {n} : la convergence n'est pas monotone : {non_decroissants}")
    assert ecarts[-1] < 1e-12, (
        f"\nn = {n} : a tau_0 = {TAU_0_DECROISSANTS[-1]:.0e}, l'ecart relatif "
        f"a la loi de puissance vaut {ecarts[-1]:.3e}, attendu sous 1e-12")
