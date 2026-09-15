#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gel des sorties de reference du MEPM, phase 1 de la refonte.

Ce script execute le modele TEL QU'IL EST, sans aucune modification de la
physique, sur une grille de cas, et enregistre les sorties dans
tests/reference.json. Il constitue le filet de securite des phases suivantes :
toute modification ulterieure doit soit reproduire ces nombres a l'identique,
soit declarer explicitement l'ecart qu'elle introduit.

Il gele le comportement ACTUEL, defauts compris. En particulier :
  - le deballage permute des sorties de generateP dans main.compute_pressures
    (defaut #9 du diagnostic) ;
  - le facteur (3n+1)^(1-n) parasite de la branche conique analytique,
    du a une priorite d'operateurs dans calculateReq (defaut #8) ;
  - les exceptions levees par readMaterial sur les feuilles a 10 lignes
    (defaut #10), enregistrees comme comportement attendu.
Ces defauts seront corriges dans des commits ulterieurs, isoles et dates.

Deux familles de cas :

  Famille A, parametres explicites, sans readMaterial.
      Couvre les 7 branches rheologiques de calculateVisco, les deux types de
      buse, les 4 combinaisons de R et mP, plusieurs vitesses et diametres, et
      des cas a buses non identiques.

  Famille B, chemin complet via readMaterial et materials.xls.
      Objectif : pouvoir regenerer a l'identique des pressions susceptibles
      d'avoir ete utilisees dans un manuscrit. La reproductibilite de cette
      famille prime sur son elegance.

Versionnement : une reference n'est JAMAIS ecrasee. Ce script refuse d'ecrire
sur un fichier existant. Chaque phase qui modifie une valeur numerique de
sortie produit une nouvelle version sous tests/references/, les precedentes
sont conservees, et tests/compare_references.py produit le tableau comparatif
qui justifie chaque ecart.

Usage :
    python3 tests/generate_reference.py <nom_de_version>
    python3 tests/generate_reference.py reference_v2_phase4

Auteurs du code modelise : David Brzeski, Jean-Francois Chauvette,
Raphael Plante. Ce script de gel est une contribution de la refonte.
"""

import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

os.environ.setdefault("MPLBACKEND", "Agg")

import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
import xlrd                             # noqa: E402

from tests.reference_io import (         # noqa: E402
    BASE_MATERIAUX, DOSSIER_REFERENCES, execute)


# Geometrie conique de reference, celle de main.py au tag etat-initial.
GEO_CONIQUE = dict(De=0.45, Do=3.55, L=17.25, angle_deg=5.3, alpha=36)
# Geometrie cylindrique de reference, celle de la branche 'else' de main.py.
GEO_CYLINDRIQUE = dict(De=0.25, Do=3.55, L=6.5, angle_deg=5.3, alpha=26)


# ---------------------------------------------------------------------------
# Famille A : jeux rheologiques explicites
# ---------------------------------------------------------------------------
#
# 'provenance' distingue ce qui vient de la base livree de ce qui est
# synthetique. Aucun jeu synthetique ne pretend decrire un materiau reel : il
# n'existe pas de feuille lisible declenchant ces branches de calculateVisco,
# et la phase 1 exige pourtant de les couvrir.

LOIS_RHEOLOGIQUES = [
    dict(nom="power_law_EC3515_0",
         provenance="materials.xls, feuille EC3515-0%",
         rho=973.0, n=0.49, K=3280.0,
         eta_inf=0.0, eta_0=0.0, tau_0=0.0, lmbda=0.0, a=0.0),
    dict(nom="power_law_0HMGS_12FS_JF",
         provenance="materials.xls, feuille '0HMGS-12FS - JF'",
         rho=1279.0, n=0.3575, K=6673.0,
         eta_inf=0.0, eta_0=0.0, tau_0=0.0, lmbda=0.0, a=0.0),
    dict(nom="sisko_abradable_benchmark",
         provenance="materials.xls, feuille Abradable-Benchmark, colonne "
                    "'old combined' (non lue par readMaterial)",
         rho=500.0, n=0.0742, K=3600.3,
         eta_inf=325.85, eta_0=0.0, tau_0=0.0, lmbda=0.0, a=0.0),
    dict(nom="newtonien_synthetique",
         provenance="SYNTHETIQUE, aucune feuille de la base ne declenche cette "
                    "branche",
         rho=973.0, n=1.0, K=0.0,
         eta_inf=100.0, eta_0=0.0, tau_0=0.0, lmbda=0.0, a=0.0),
    dict(nom="carreau_PLA_solvent_cast_25",
         provenance="materials.xls, feuille 'PLA solvent cast-25%', rho force "
                    "a 973 car rho=0 fait planter generateP (defaut #19)",
         rho=973.0, n=0.62, K=0.0,
         eta_inf=1e-06, eta_0=43.6, tau_0=0.0, lmbda=0.028, a=3.15),
    dict(nom="bingham_synthetique",
         provenance="SYNTHETIQUE, tau_0 emprunte a 'Parrafin wax-40%', "
                    "eta_inf arbitraire",
         rho=1084.0, n=1.0, K=0.0,
         eta_inf=12.5, eta_0=0.0, tau_0=490.0, lmbda=0.0, a=0.0),
    dict(nom="herschel_bulkley_parrafin_wax_40",
         provenance="materials.xls, feuille 'Parrafin wax-40%' (illisible par "
                    "readMaterial, defaut #10)",
         rho=1084.0, n=0.04, K=2850000.0,
         eta_inf=0.0, eta_0=0.0, tau_0=490.0, lmbda=0.0, a=0.0),
    dict(nom="herschel_bulkley_etendu_synthetique",
         provenance="SYNTHETIQUE, aucune feuille de la base ne declenche cette "
                    "branche",
         rho=1084.0, n=0.31, K=4363.0,
         eta_inf=50.0, eta_0=0.0, tau_0=490.0, lmbda=0.0, a=0.0),
    dict(nom="carreau_rho_nul",
         provenance="materials.xls, feuille 'PLA solvent cast-25%' telle "
                    "quelle, rho=0 : gele le plantage de validateReynolds",
         rho=0.0, n=0.62, K=0.0,
         eta_inf=1e-06, eta_0=43.6, tau_0=0.0, lmbda=0.028, a=3.15),
]

# Les 4 combinaisons de R et mP, dont les deux aberrantes.
COMBINAISONS_R_MP = [
    dict(nom="analytique", R=0.0, mP=0.0),
    dict(nom="R_seul_aberrant", R=1.548459269275235, mP=0.0),
    dict(nom="mP_seul_aberrant", R=0.0, mP=0.34455727852674917),
    dict(nom="empirique", R=1.548459269275235, mP=0.34455727852674917),
]

VITESSES_A = [10.0, 50.0, 100.0, 250.0]
DIAMETRES_A = [0.25, 0.45, 0.60]


def cas_famille_A():
    """Enumere les cas de la famille A."""
    cas = []
    for loi in LOIS_RHEOLOGIQUES:
        for noz in ["cylindrical", "tapered"]:
            for De in DIAMETRES_A:
                for combi in COMBINAISONS_R_MP:
                    cas.append(dict(
                        famille="A",
                        identifiant=f"A|{loi['nom']}|{noz}|De={De}|{combi['nom']}",
                        loi=loi, Noz_type=noz, R=combi["R"], mP=combi["mP"],
                        v=list(VITESSES_A),
                        D_description=dict(type="homogene", De=De, Do=3.55,
                                           alpha=4, err=0.001),
                        L=[17.25, 0.01], angle_deg=5.3,
                        P_amb=101325.0,
                    ))
    # Buses non identiques : gele le comportement actuel de la mise en
    # parallele (defaut #4). Le mode empirique est inclus car mean(Q_eq) y
    # depend aussi de l'heterogeneite.
    for loi in [LOIS_RHEOLOGIQUES[0], LOIS_RHEOLOGIQUES[3]]:
        for noz in ["cylindrical", "tapered"]:
            for combi in [COMBINAISONS_R_MP[0], COMBINAISONS_R_MP[3]]:
                cas.append(dict(
                    famille="A",
                    identifiant=f"A|{loi['nom']}|{noz}|heterogene|{combi['nom']}",
                    loi=loi, Noz_type=noz, R=combi["R"], mP=combi["mP"],
                    v=list(VITESSES_A),
                    D_description=dict(type="heterogene",
                                       diametres=[0.45, 0.30, 0.25, 0.50],
                                       Do=3.55, err=0.001),
                    L=[17.25, 0.01], angle_deg=5.3,
                    P_amb=101325.0,
                ))
    return cas


# ---------------------------------------------------------------------------
# Famille B : chemin complet via readMaterial
# ---------------------------------------------------------------------------

# 10 a 300 mm/s par pas de 10, puis les vitesses laissees dans main.py.
VITESSES_B = [float(x) for x in range(10, 301, 10)] + \
             [3920.0, 3930.0, 3940.0, 3950.0, 3960.0]


def feuilles_base():
    """Retourne la liste des feuilles de materials.xls, dans l'ordre du fichier."""
    return pd.ExcelFile(BASE_MATERIAUX).sheet_names


def cas_famille_B():
    """Enumere les cas de la famille B, une entree par feuille et geometrie."""
    cas = []
    for feuille in feuilles_base():
        for geo_nom, geo, noz in [("conique", GEO_CONIQUE, "tapered"),
                                  ("cylindrique", GEO_CYLINDRIQUE, "cylindrical")]:
            cas.append(dict(
                famille="B",
                identifiant=f"B|{feuille}|{geo_nom}",
                feuille=feuille, Noz_type=noz,
                v=list(VITESSES_B),
                D_description=dict(type="homogene", De=geo["De"], Do=geo["Do"],
                                   alpha=geo["alpha"], err=0.001),
                L=[geo["L"], 0.01], angle_deg=geo["angle_deg"],
                P_amb=101325.0,
            ))
    return cas


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Metadonnees
# ---------------------------------------------------------------------------

def commande_git(*args):
    try:
        return subprocess.check_output(["git"] + list(args), cwd=RACINE,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:                     # noqa: BLE001
        return None


def metadonnees():
    suivis_modifies = commande_git("status", "--porcelain", "--untracked-files=no")
    return dict(
        horodatage_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        git_sha=commande_git("rev-parse", "HEAD"),
        git_sha_court=commande_git("rev-parse", "--short", "HEAD"),
        git_branche=commande_git("rev-parse", "--abbrev-ref", "HEAD"),
        git_fichiers_suivis_modifies=(suivis_modifies or "").splitlines(),
        python=platform.python_version(),
        python_implementation=platform.python_implementation(),
        numpy=np.__version__,
        pandas=pd.__version__,
        xlrd=xlrd.__version__,
        plateforme=platform.platform(),
        base_materiaux=os.path.basename(BASE_MATERIAUX),
        base_materiaux_sha256=hashlib.sha256(
            open(BASE_MATERIAUX, "rb").read()).hexdigest(),
    )


def execute_cas(cas):
    """Adaptateur : prepare les entrees et delegue a reference_io.execute."""
    entrees = {k: v for k, v in cas.items() if k != "loi"}
    resultat = execute(entrees, cas.get("loi"))
    if cas["famille"] == "A":
        ordonne = {}
        for cle, valeur in resultat.items():
            ordonne[cle] = valeur
            if cle == "parametres_materiau":
                ordonne["provenance_materiau"] = cas["loi"]["provenance"]
        resultat = ordonne
    return resultat


def main_script(chemin_sortie):
    cas = cas_famille_A() + cas_famille_B()
    resultats = {}
    for i, c in enumerate(cas, 1):
        print(f"  [{i:3d}/{len(cas)}] {c['identifiant']}", file=sys.stderr)
        entree = {k: v for k, v in c.items() if k != "loi"}
        resultats[c["identifiant"]] = dict(entrees=entree,
                                           sorties=execute_cas(c))

    document = dict(
        format="MEPM reference de non-regression, phase 1",
        avertissement=(
            "Ces valeurs gelent le comportement du code A LA DATE INDIQUEE, "
            "defauts compris. Elles ne constituent pas une verite physique. "
            "Voir la docstring de tests/generate_reference.py."),
        metadonnees=metadonnees(),
        nombre_de_cas=len(resultats),
        resultats=resultats,
    )
    empreinte = hashlib.sha256(
        json.dumps(document["resultats"], sort_keys=True,
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    document["sha256_des_resultats"] = empreinte

    with open(chemin_sortie, "w", encoding="utf-8") as fichier:
        json.dump(document, fichier, ensure_ascii=False, indent=1,
                  allow_nan=True)
        fichier.write("\n")
    print(f"\n{len(resultats)} cas ecrits dans {chemin_sortie}")
    print(f"sha256 des resultats : {empreinte}")
    return document


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        print("ERREUR : un nom de version est obligatoire, par exemple "
              "reference_v2_phase4", file=sys.stderr)
        raise SystemExit(2)
    nom_version = sys.argv[1]
    if nom_version.endswith(".json"):
        nom_version = nom_version[:-5]
    sortie = os.path.join(DOSSIER_REFERENCES, f"{nom_version}.json")
    if os.path.exists(sortie):
        print(f"ERREUR : {sortie} existe deja. Une reference n'est jamais "
              f"ecrasee : choisissez un nouveau nom de version.", file=sys.stderr)
        raise SystemExit(1)
    os.makedirs(DOSSIER_REFERENCES, exist_ok=True)
    main_script(sortie)
