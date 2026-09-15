#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lecture de materiaux.xlsx, la base a en-tetes nommes.

Lecture PAR NOM DE COLONNE, jamais par position. Ajouter une colonne ou en
reordonner ne casse rien, contrairement a l'ancien lecteur positionnel dont le
defaut #10 etait la consequence directe.

Voir tools/creer_base_materiaux.py pour le format et la provenance des valeurs.

Auteurs : contribution de la refonte. Les donnees rheologiques sont celles
rassemblees par David Brzeski, Jean-Francois Chauvette et Raphael Plante.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import pandas as pd                                    # noqa: E402

from Velocity_driven.modeles import valide_mode, valide_modele  # noqa: E402

BASE_MATERIAUX = os.path.join(RACINE, "materiaux.xlsx")
FEUILLE = "materiaux"

PARAMETRES = ("rho", "n", "K", "eta_inf", "eta_0", "tau_0", "lambda", "a")

# Correspondance entre la colonne d'incertitude de la base et la cle attendue
# par calculateVisco. rho n'y figure pas : sa propagation n'est pas implementee.
CLES_INCERTITUDES = ("K", "n", "eta_inf", "eta_0", "tau_0", "lambda", "a")


def materiaux_disponibles(fichier=BASE_MATERIAUX):
    """Noms des materiaux presents dans la base, dans l'ordre du fichier."""
    table = pd.read_excel(fichier, sheet_name=FEUILLE)
    return list(table["materiau"])


def lireMateriau(nom, fichier=BASE_MATERIAUX):
    """Lit un materiau et rend un dictionnaire complet.

    Args:
        nom (str): nom du materiau, colonne 'materiau'.
        fichier (str): chemin du classeur.

    Returns:
        dict: cles
            materiau (str), modele (str), mode (str),
            provenance (str), provenance_ajustement (str),
            rho [kg/m^3], w [wt.%], f [vol.%], n [-], K [Pa.s^n],
            eta_inf [Pa.s], eta_0 [Pa.s], tau_0 [Pa], lambda [s], a [-],
            mP [-], R [unite indeterminee],
            incertitudes (dict) aux cles CLES_INCERTITUDES, dans l'unite du
                parametre correspondant. Une case vide vaut zero.

    Raises:
        KeyError: si le materiau n'existe pas.
        ValueError: si le modele ou le mode declare est inconnu.
    """
    table = pd.read_excel(fichier, sheet_name=FEUILLE)
    lignes = table[table["materiau"] == nom]
    if lignes.empty:
        raise KeyError(
            f"Materiau inconnu : {nom!r}. Disponibles : "
            f"{materiaux_disponibles(fichier)}")
    ligne = lignes.iloc[0]

    def nombre(colonne, defaut=0.0):
        if colonne not in table.columns:
            return defaut
        brute = ligne[colonne]
        return defaut if pd.isna(brute) else float(brute)

    def texte(colonne):
        brute = ligne.get(colonne)
        return "" if pd.isna(brute) else str(brute)

    materiau = {
        "materiau": nom,
        "modele": valide_modele(texte("modele")),
        "mode": valide_mode(texte("mode")),
        "provenance": texte("provenance"),
        "provenance_ajustement": texte("provenance_ajustement"),
        "w": nombre("w"),
        "f": nombre("f"),
        "mP": nombre("mP"),
        "R": nombre("R"),
        "incertitudes": {cle: nombre(f"d_{cle}") for cle in CLES_INCERTITUDES},
    }
    for parametre in PARAMETRES:
        materiau[parametre] = nombre(parametre)
    return materiau
