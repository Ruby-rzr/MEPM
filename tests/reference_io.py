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

import hashlib
import json
import os

import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER_REFERENCES = os.path.join(RACINE, "tests", "references")

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
