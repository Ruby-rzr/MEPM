#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Acces aux references de non-regression du MEPM et comparaison bit a bit.

Regle de versionnement : une reference n'est JAMAIS ecrasee. Chaque phase qui
modifie une valeur numerique de sortie produit une nouvelle version, sous
tests/references/, et les precedentes sont conservees. VERSION_ACTIVE designe
celle que la suite de non-regression rejoue.

Semantique de comparaison, volontairement stricte :
  - deux NaN sont consideres egaux, quelle que soit leur charge utile ;
  - un NaN face a un nombre est un echec, dans les deux sens ;
  - tout le reste est compare sur les 64 bits bruts du flottant. Cela rend
    +0.0 et -0.0 differents, et distingue +inf de -inf. Rien n'est cense
    bouger, donc aucune tolerance n'est accordee.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import contextlib
import hashlib
import io
import json
import math
import os
import sys

import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_REFERENCES = os.path.join(RACINE, "tests", "references")
BASE_MATERIAUX = os.path.join(RACINE, "materials.xls")

if RACINE not in sys.path:
    sys.path.insert(0, RACINE)
os.environ.setdefault("MPLBACKEND", "Agg")

# Reference rejouee par tests/test_regression.py.
VERSION_ACTIVE = "reference_v1_phase1"

# Champs numeriques enregistres pour un cas dont le calcul aboutit.
CHAMPS_NUMERIQUES = ("P", "P_kPa", "eta", "SR", "Q", "dP", "dP_kPa",
                     "dRi", "deta", "dSR")


def chemin_version(version):
    """Chemin du fichier d'une version de reference."""
    return os.path.join(DOSSIER_REFERENCES, f"{version}.json")


def versions_disponibles():
    """Noms des versions presentes sur disque, triees."""
    if not os.path.isdir(DOSSIER_REFERENCES):
        return []
    return sorted(f[:-5] for f in os.listdir(DOSSIER_REFERENCES)
                  if f.endswith(".json"))


def charge(version=VERSION_ACTIVE):
    """Charge une version de reference.

    json.load accepte les litteraux NaN et Infinity, presents dans les
    references. Un parseur JSON strict les refuserait : c'est assume, la
    reference doit rester une image fidele des sorties du modele.
    """
    with open(chemin_version(version), encoding="utf-8") as fichier:
        return json.load(fichier)


def sha256_fichier(chemin):
    """sha256 d'un fichier, en hexadecimal."""
    with open(chemin, "rb") as fichier:
        return hashlib.sha256(fichier.read()).hexdigest()


def _bits(tableau):
    """Vue entiere non signee des 64 bits bruts d'un tableau de float64."""
    return np.ascontiguousarray(tableau, dtype=np.float64).view(np.uint64)


def differences(attendu, obtenu):
    """Compare deux tableaux de flottants selon la semantique du module.

    Args:
        attendu: structure imbriquee (listes) issue de la reference.
        obtenu: structure de meme forme issue de l'execution courante.

    Returns:
        (forme_attendue, forme_obtenue, liste_des_ecarts) ou liste_des_ecarts
        contient des tuples (indice_multidimensionnel, valeur_attendue,
        valeur_obtenue). La liste est vide si les tableaux sont identiques.
        Si les formes different, la liste est vide et les formes sont a
        comparer par l'appelant.
    """
    a = np.asarray(attendu, dtype=np.float64)
    b = np.asarray(obtenu, dtype=np.float64)
    if a.shape != b.shape:
        return a.shape, b.shape, []

    deux_nan = np.isnan(a) & np.isnan(b)
    bits_egaux = _bits(a.ravel()) == _bits(b.ravel())
    identiques = deux_nan.ravel() | bits_egaux
    if identiques.all():
        return a.shape, b.shape, []

    plats = np.flatnonzero(~identiques)
    ecarts = [(tuple(int(c) for c in np.unravel_index(i, a.shape)),
               float(a.ravel()[i]), float(b.ravel()[i])) for i in plats]
    return a.shape, b.shape, ecarts


def decrit_ecart(identifiant, champ, forme, ecarts, maximum=5):
    """Message d'echec nommant le cas, le champ et les indices fautifs."""
    lignes = [f"cas {identifiant!r}, champ {champ!r}, forme {forme} : "
              f"{len(ecarts)} element(s) different(s)"]
    for indice, attendu, obtenu in ecarts[:maximum]:
        lignes.append(f"    indice {indice} : reference={attendu!r} "
                      f"obtenu={obtenu!r}")
    if len(ecarts) > maximum:
        lignes.append(f"    ... et {len(ecarts) - maximum} autre(s)")
    return "\n".join(lignes)


# ---------------------------------------------------------------------------
# Construction des entrees et execution d'un cas
#
# Ce bloc est partage par tests/generate_reference.py, qui produit les
# references, et par tests/test_regression.py, qui les rejoue. Il ne contient
# aucune physique : uniquement la mise en forme des tableaux attendus par
# generateP. La physique reste dans Velocity_driven.
# ---------------------------------------------------------------------------

def make_D(De, Do, alpha, err=0.001):
    """Construit le tableau D attendu par le modele.

    Args:
        De (float): diametre de sortie de buse. [mm]
        Do (float): diametre d'entree de buse, utilise en conique. [mm]
        alpha (int): nombre de buses.
        err (float): erreur sur le diametre mesure. [mm]

    Returns:
        numpy.ndarray de forme (3, alpha) : sortie, erreur, entree. [mm]
    """
    D = np.zeros((3, alpha))
    D[0, :] = De
    D[1, :] = err
    D[2, :] = Do
    return D


def make_D_heterogene(diametres, Do, err=0.001):
    """Idem, mais avec un diametre de sortie different par buse. [mm]"""
    alpha = len(diametres)
    D = np.zeros((3, alpha))
    D[0, :] = np.asarray(diametres, dtype=float)
    D[1, :] = err
    D[2, :] = Do
    return D


def construit_D(description):
    """Reconstruit D depuis la description enregistree dans une reference."""
    if description["type"] == "homogene":
        return make_D(description["De"], description["Do"],
                      description["alpha"], description["err"])
    return make_D_heterogene(description["diametres"], description["Do"],
                             description["err"])


def _enregistre(x):
    """Convertit une sortie numpy en structure JSON, NaN et inf compris."""
    return np.asarray(x, dtype=float).tolist()


def execute(entrees, parametres_materiau=None):
    """Execute un cas et retourne ses sorties, ou l'exception levee.

    Args:
        entrees (dict): bloc 'entrees' d'un enregistrement de reference.
        parametres_materiau (dict): parametres rheologiques, obligatoire pour
            la famille A. Ignore pour la famille B, dont le materiau est relu
            depuis materials.xls : la lecture fait partie de ce qui est gele.

    Returns:
        dict: bloc 'sorties' au format des references.
    """
    import main                              # noqa: PLC0415
    from tools import readMaterial           # noqa: PLC0415

    D = construit_D(entrees["D_description"])
    alpha = D.shape[1]
    L = np.array(entrees["L"], dtype=float)
    theta = math.radians(entrees["angle_deg"])
    v = np.array(entrees["v"], dtype=float)

    resultat = dict(alpha=alpha)

    if entrees["famille"] == "A":
        p = parametres_materiau
        resultat["parametres_materiau"] = {
            k: p[k] for k in ("rho", "n", "K", "eta_inf", "eta_0",
                              "tau_0", "lmbda", "a")}
        rho, n, K = p["rho"], p["n"], p["K"]
        eta_inf, eta_0 = p["eta_inf"], p["eta_0"]
        tau_0, lmbda, a = p["tau_0"], p["lmbda"], p["a"]
        R, mP = entrees["R"], entrees["mP"]
    else:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                lu = readMaterial.readMaterial(BASE_MATERIAUX, entrees["feuille"])
        except Exception as exc:              # noqa: BLE001
            resultat["lecture_materiau"] = dict(statut="exception",
                                                type=type(exc).__name__,
                                                message=str(exc))
            return resultat
        rho, w, f, n, K, eta_inf, eta_0, tau_0, lmbda, a, mP, R = lu
        resultat["lecture_materiau"] = dict(statut="ok")
        resultat["parametres_materiau"] = dict(
            rho=float(rho), w=float(w), f=float(f), n=float(n), K=float(K),
            eta_inf=float(eta_inf), eta_0=float(eta_0), tau_0=float(tau_0),
            lmbda=float(lmbda), a=float(a), mP=float(mP), R=float(R))
        resultat["R"] = float(R)
        resultat["mP"] = float(mP)

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            sorties = main.compute_pressures(
                rho, v, D, L, theta, n, K, eta_0, eta_inf, tau_0, lmbda, a,
                entrees["P_amb"], entrees["Noz_type"], R, mP, alpha, False)
    except Exception as exc:                  # noqa: BLE001
        resultat["calcul"] = dict(statut="exception",
                                  type=type(exc).__name__,
                                  message=str(exc))
        return resultat

    resultat["calcul"] = dict(statut="ok")
    for cle in CHAMPS_NUMERIQUES:
        resultat[cle] = _enregistre(sorties[cle])
    return resultat
