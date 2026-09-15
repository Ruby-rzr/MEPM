#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construit materiaux.xlsx, la base de materiaux a en-tetes nommes.

materials.xls devient un ARTEFACT GELE. Son sha256 est l'ancre d'integrite de
toutes les references de non-regression, il ne doit donc jamais etre modifie.
Il n'est plus lu que par tools/readMaterial.py, pour la reproduction des
references historiques.

La nouvelle base corrige les defauts de forme de l'ancienne :

  - en-tetes NOMMES, un materiau par ligne, plus de lecture positionnelle ni
    de feuille par materiau ;
  - un champ 'modele' explicite, au lieu d'une loi devinee d'apres les
    parametres laisses a zero ;
  - un champ 'mode' explicite, analytique ou empirique ;
  - une colonne d'INCERTITUDE par parametre, ces grandeurs etant des
    proprietes du materiau et de son ajustement, non du code ;
  - une colonne de PROVENANCE par materiau, et une pour l'ajustement.

Ce script est versionne pour que la base soit reproductible et que la
provenance de chaque valeur soit lisible dans le code qui l'a ecrite.

Usage :
    python3 tools/creer_base_materiaux.py [chemin/vers/materiaux.xlsx]

Auteurs : contribution de la refonte. Les donnees rheologiques sont celles
rassemblees par David Brzeski, Jean-Francois Chauvette et Raphael Plante.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import openpyxl                                        # noqa: E402
import pandas as pd                                    # noqa: E402

from Velocity_driven.modeles import (                   # noqa: E402
    ANALYTIQUE, deduire_modele_historique)

BASE_HISTORIQUE = os.path.join(RACINE, "materials.xls")
BASE_NOUVELLE = os.path.join(RACINE, "materiaux.xlsx")

COLONNES = [
    "materiau", "modele", "mode", "provenance",
    "rho", "d_rho", "w", "f",
    "n", "d_n", "K", "d_K",
    "eta_inf", "d_eta_inf", "eta_0", "d_eta_0",
    "tau_0", "d_tau_0", "lambda", "d_lambda", "a", "d_a",
    "mP", "R", "provenance_ajustement",
]

UNITES = {
    "rho": "kg/m3", "d_rho": "kg/m3", "w": "wt.%", "f": "vol.%",
    "n": "-", "d_n": "-", "K": "Pa.s^n", "d_K": "Pa.s^n",
    "eta_inf": "Pa.s", "d_eta_inf": "Pa.s", "eta_0": "Pa.s", "d_eta_0": "Pa.s",
    "tau_0": "Pa", "d_tau_0": "Pa", "lambda": "s", "d_lambda": "s",
    "a": "-", "d_a": "-", "mP": "-", "R": "indeterminee",
}

# Valeurs mP et R trouvees en colonne C de materials.xls, la ou readMaterial
# lit la colonne B. Voir notes/colonne_C_materials_xls.md. Elles figurent ici
# pour ne pas etre perdues, avec une provenance INCONNUE et un mode
# ANALYTIQUE : elles ne sont donc PAS utilisees.
AJUSTEMENTS_COLONNE_C = {
    "EC3515-0%": (0.4728957491325613, 1.3344569767816075),
    "EC3515-8%": (0.3828177864281889, 0.29637175877940436),
    "Wax-Bruneaux": (0.3828177864281889, 0.29637175877940436),
    "Wax-JFC": (0.3828177864281889, 0.29637175877940436),
}

PROVENANCE_AJUSTEMENT_INCONNUE = (
    "INCONNUE. Script d'ajustement absent du depot, auteur du portage "
    "interroge sans resultat. Non utilise, mode analytique. Voir "
    "notes/colonne_C_materials_xls.md.")

PROVENANCE_RHEOLOGIE = (
    "materials.xls, feuille de meme nom, colonne B. Conditions de mesure et "
    "date non documentees dans le depot.")


def lignes_depuis_base_historique():
    """Transpose materials.xls, une feuille par materiau, en lignes nommees."""
    lignes = []
    for feuille in pd.ExcelFile(BASE_HISTORIQUE).sheet_names:
        colonne_b = pd.read_excel(BASE_HISTORIQUE, sheet_name=feuille,
                                  header=None, usecols="B")

        def valeur(ligne):
            if ligne >= len(colonne_b):
                return 0.0
            brute = colonne_b.iloc[ligne, 0]
            return 0.0 if pd.isna(brute) else float(brute)

        rho, w, f = valeur(0), valeur(1), valeur(2)
        n, K = valeur(3), valeur(4)
        eta_inf, eta_0, tau_0 = valeur(5), valeur(6), valeur(7)
        lmbda, a = valeur(8), valeur(9)
        mP_b, R_b = valeur(10), valeur(11)

        try:
            modele = deduire_modele_historique(n, K, eta_inf, eta_0, tau_0,
                                               lmbda, a)
        except ValueError:
            modele = "INDETERMINE"

        mP_c, R_c = AJUSTEMENTS_COLONNE_C.get(feuille, (0.0, 0.0))
        mP = mP_b if mP_b != 0.0 else mP_c
        R = R_b if R_b != 0.0 else R_c
        ajustement = (PROVENANCE_AJUSTEMENT_INCONNUE
                      if (mP != 0.0 or R != 0.0) else "")

        lignes.append({
            "materiau": feuille,
            "modele": modele,
            # Decision : TOUS les materiaux sont en mode analytique. Aucun
            # parametre ajuste de provenance inconnue n'alimente un resultat.
            "mode": ANALYTIQUE,
            "provenance": PROVENANCE_RHEOLOGIE,
            "rho": rho, "d_rho": None, "w": w, "f": f,
            "n": n, "d_n": None, "K": K, "d_K": None,
            "eta_inf": eta_inf, "d_eta_inf": None,
            "eta_0": eta_0, "d_eta_0": None,
            "tau_0": tau_0, "d_tau_0": None,
            "lambda": lmbda, "d_lambda": None,
            "a": a, "d_a": None,
            "mP": mP, "R": R,
            "provenance_ajustement": ajustement,
        })
    return lignes


def ecrit(chemin, lignes):
    """Ecrit le classeur : une feuille de donnees, une feuille d'unites."""
    classeur = openpyxl.Workbook()

    feuille = classeur.active
    feuille.title = "materiaux"
    feuille.append(COLONNES)
    for ligne in lignes:
        feuille.append([ligne[colonne] for colonne in COLONNES])
    feuille.freeze_panes = "B2"

    unites = classeur.create_sheet("unites")
    unites.append(["colonne", "unite"])
    for colonne in COLONNES:
        unites.append([colonne, UNITES.get(colonne, "")])

    lisez_moi = classeur.create_sheet("lisez_moi")
    for texte in [
        ["Base de materiaux du MEPM, format a en-tetes nommes."],
        [""],
        ["Un materiau par ligne. Les colonnes d_<parametre> portent"],
        ["l'incertitude du parametre correspondant, dans la meme unite."],
        ["Une case vide vaut zero et annule la contribution du parametre"],
        ["a l'incertitude de la viscosite."],
        [""],
        ["modele : sisko, newtonien, loi_de_puissance, carreau, bingham,"],
        ["         herschel_bulkley, herschel_bulkley_etendu."],
        ["mode   : analytique ou empirique."],
        [""],
        ["Le mode empirique utilise mP et R, ajustes sur des mesures. Sa"],
        ["sortie N'EST PAS UNE PREDICTION et ne doit alimenter aucune figure"],
        ["de publication. Tous les materiaux de cette base sont en mode"],
        ["analytique : les valeurs mP et R presentes ont une provenance"],
        ["INCONNUE et ne sont donc pas utilisees."],
        [""],
        ["Genere par tools/creer_base_materiaux.py. Ne pas editer a la main"],
        ["sans mettre ce script a jour."],
    ]:
        lisez_moi.append(texte)

    classeur.save(chemin)


if __name__ == "__main__":
    sortie = sys.argv[1] if len(sys.argv) > 1 else BASE_NOUVELLE
    lignes_ecrites = lignes_depuis_base_historique()
    ecrit(sortie, lignes_ecrites)
    print(f"{len(lignes_ecrites)} materiaux ecrits dans {sortie}")
