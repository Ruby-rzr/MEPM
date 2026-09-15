#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tableau comparatif entre deux versions de reference du MEPM.

Les phases 4 et 5 vont modifier des valeurs numeriques de sortie. Chacune
produira une nouvelle version de reference, sans ecraser la precedente. Ce
script produit le tableau qui sert a justifier chaque ecart, cas par cas et
champ par champ. C'est ce tableau qui fait foi, pas le diff du JSON.

Traitement des cas particuliers :
  - un NaN devenu un nombre, ou l'inverse, est compte a part, l'ecart relatif
    n'ayant pas de sens ;
  - un changement de statut (calcul qui aboutit alors qu'il levait une
    exception, ou l'inverse) est signale en tete de tableau, avant les
    comparaisons numeriques ;
  - un cas present dans une seule des deux versions est signale.

Usage :
    python3 tests/compare_references.py <version_avant> <version_apres>
    python3 tests/compare_references.py reference_v1_phase1 reference_v2_phase4
    python3 tests/compare_references.py v1 v2 --csv ecarts.csv
    python3 tests/compare_references.py v1 v2 --tous   (inclut les champs identiques)

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import argparse
import csv
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import numpy as np                                    # noqa: E402

from tests import reference_io                        # noqa: E402
from tests.reference_io import CHAMPS_NUMERIQUES      # noqa: E402

COLONNES = ["cas", "champ", "n_elements", "n_differents", "n_nan_apparus",
            "n_nan_disparus", "ecart_abs_max", "ecart_rel_max", "indice_max",
            "valeur_avant", "valeur_apres"]


def statut_du_cas(sorties):
    """Resume textuel du statut d'un cas."""
    lecture = sorties.get("lecture_materiau")
    if lecture and lecture.get("statut") == "exception":
        return f"lecture {lecture['type']}"
    calcul = sorties.get("calcul", {})
    if calcul.get("statut") == "exception":
        return f"calcul {calcul['type']}"
    return "ok"


def compare_champ(avant, apres):
    """Compare un champ numerique et retourne ses statistiques d'ecart."""
    a = np.asarray(avant, dtype=np.float64).ravel()
    b = np.asarray(apres, dtype=np.float64).ravel()
    if a.shape != b.shape:
        return dict(forme_differente=True, n_elements=a.size,
                    forme_avant=np.asarray(avant).shape,
                    forme_apres=np.asarray(apres).shape)

    nan_a, nan_b = np.isnan(a), np.isnan(b)
    nan_apparus = int(np.sum(~nan_a & nan_b))
    nan_disparus = int(np.sum(nan_a & ~nan_b))

    comparables = ~nan_a & ~nan_b
    ecart_abs = np.zeros_like(a)
    ecart_abs[comparables] = np.abs(b[comparables] - a[comparables])

    with np.errstate(divide="ignore", invalid="ignore"):
        ecart_rel = np.where(
            comparables & (a != 0), ecart_abs / np.abs(a), np.nan)

    identiques = ((nan_a & nan_b) |
                  (comparables &
                   (reference_io._bits(np.ascontiguousarray(a)) ==
                    reference_io._bits(np.ascontiguousarray(b)))))
    n_differents = int(np.sum(~identiques))

    if n_differents == 0:
        return dict(forme_differente=False, n_elements=a.size, n_differents=0,
                    n_nan_apparus=0, n_nan_disparus=0, ecart_abs_max=0.0,
                    ecart_rel_max=0.0, indice_max=None,
                    valeur_avant=None, valeur_apres=None)

    if np.any(comparables) and np.nanmax(ecart_abs[comparables], initial=0.0) > 0:
        indice_plat = int(np.nanargmax(np.where(comparables, ecart_abs, -np.inf)))
    else:
        indice_plat = int(np.flatnonzero(~identiques)[0])

    forme = np.asarray(avant).shape
    return dict(
        forme_differente=False,
        n_elements=a.size,
        n_differents=n_differents,
        n_nan_apparus=nan_apparus,
        n_nan_disparus=nan_disparus,
        ecart_abs_max=float(np.nanmax(ecart_abs)) if np.any(comparables) else float("nan"),
        ecart_rel_max=float(np.nanmax(ecart_rel)) if np.any(comparables) else float("nan"),
        indice_max=tuple(int(c) for c in np.unravel_index(indice_plat, forme)),
        valeur_avant=float(a[indice_plat]),
        valeur_apres=float(b[indice_plat]),
    )


def compare(version_avant, version_apres, tous=False):
    """Compare deux versions et retourne (lignes, anomalies, resume)."""
    doc_a = reference_io.charge(version_avant)
    doc_b = reference_io.charge(version_apres)
    res_a, res_b = doc_a["resultats"], doc_b["resultats"]

    anomalies = []
    for identifiant in sorted(set(res_a) - set(res_b)):
        anomalies.append(f"cas disparu dans {version_apres} : {identifiant}")
    for identifiant in sorted(set(res_b) - set(res_a)):
        anomalies.append(f"cas apparu dans {version_apres} : {identifiant}")

    lignes = []
    cas_modifies = set()
    for identifiant in sorted(set(res_a) & set(res_b)):
        sa, sb = res_a[identifiant]["sorties"], res_b[identifiant]["sorties"]
        st_a, st_b = statut_du_cas(sa), statut_du_cas(sb)
        if st_a != st_b:
            anomalies.append(f"changement de statut, {identifiant} : "
                             f"{st_a} -> {st_b}")
            cas_modifies.add(identifiant)
            continue
        for champ in CHAMPS_NUMERIQUES:
            if champ not in sa and champ not in sb:
                continue
            if champ not in sa or champ not in sb:
                anomalies.append(f"champ {champ} present d'un seul cote, "
                                 f"{identifiant}")
                cas_modifies.add(identifiant)
                continue
            stats = compare_champ(sa[champ], sb[champ])
            if stats.get("forme_differente"):
                anomalies.append(
                    f"forme differente, {identifiant}, {champ} : "
                    f"{stats['forme_avant']} -> {stats['forme_apres']}")
                cas_modifies.add(identifiant)
                continue
            if stats["n_differents"] == 0 and not tous:
                continue
            if stats["n_differents"]:
                cas_modifies.add(identifiant)
            lignes.append(dict(cas=identifiant, champ=champ, **{
                k: stats[k] for k in COLONNES[2:]}))

    resume = dict(
        version_avant=version_avant,
        version_apres=version_apres,
        cas_communs=len(set(res_a) & set(res_b)),
        cas_modifies=len(cas_modifies),
        lignes=len(lignes),
        sha_avant=doc_a["metadonnees"].get("git_sha_court"),
        sha_apres=doc_b["metadonnees"].get("git_sha_court"),
        base_avant=doc_a["metadonnees"].get("base_materiaux_sha256"),
        base_apres=doc_b["metadonnees"].get("base_materiaux_sha256"),
    )
    return lignes, anomalies, resume


def formate(valeur, largeur):
    if valeur is None:
        return "".ljust(largeur)
    if isinstance(valeur, float):
        return f"{valeur:.6e}".rjust(largeur)
    return str(valeur).ljust(largeur)


def affiche(lignes, anomalies, resume, limite=None):
    print("=" * 100)
    print(f"Comparaison : {resume['version_avant']} -> {resume['version_apres']}")
    print(f"  commit      : {resume['sha_avant']} -> {resume['sha_apres']}")
    if resume["base_avant"] != resume["base_apres"]:
        print("  ATTENTION   : materials.xls a change entre les deux versions,")
        print("                les ecarts ne sont pas imputables au seul code.")
    print(f"  cas communs : {resume['cas_communs']}, "
          f"dont modifies : {resume['cas_modifies']}")
    print("=" * 100)

    if anomalies:
        print(f"\nAnomalies structurelles ({len(anomalies)}) :")
        for a in anomalies[:50]:
            print(f"  {a}")
        if len(anomalies) > 50:
            print(f"  ... et {len(anomalies) - 50} autre(s)")

    if not lignes:
        print("\nAucun ecart numerique.")
        return

    print(f"\nEcarts par cas et par champ ({len(lignes)} ligne(s)) :\n")
    largeurs = [72, 7, 10, 12, 13, 14, 14, 14, 12]
    entetes = ["cas", "champ", "n_elem", "n_differents", "nan_apparus",
               "nan_disparus", "ecart_abs_max", "ecart_rel_max", "indice_max"]
    print("  ".join(e.ljust(l) for e, l in zip(entetes, largeurs)))
    print("  ".join("-" * l for l in largeurs))
    for ligne in (lignes if limite is None else lignes[:limite]):
        cellules = [
            str(ligne["cas"])[:largeurs[0]].ljust(largeurs[0]),
            str(ligne["champ"]).ljust(largeurs[1]),
            str(ligne["n_elements"]).rjust(largeurs[2]),
            str(ligne["n_differents"]).rjust(largeurs[3]),
            str(ligne["n_nan_apparus"]).rjust(largeurs[4]),
            str(ligne["n_nan_disparus"]).rjust(largeurs[5]),
            formate(ligne["ecart_abs_max"], largeurs[6]),
            formate(ligne["ecart_rel_max"], largeurs[7]),
            str(ligne["indice_max"]).rjust(largeurs[8]),
        ]
        print("  ".join(cellules))
    if limite is not None and len(lignes) > limite:
        print(f"  ... et {len(lignes) - limite} ligne(s), utiliser --csv "
              f"pour le tableau complet")


def ecrit_csv(lignes, chemin):
    with open(chemin, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.DictWriter(fichier, fieldnames=COLONNES)
        ecrivain.writeheader()
        for ligne in lignes:
            ecrivain.writerow(ligne)
    print(f"\nTableau complet ecrit dans {chemin}")


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("avant", help="nom de la version de reference avant")
    analyseur.add_argument("apres", help="nom de la version de reference apres")
    analyseur.add_argument("--csv", help="chemin du tableau complet en CSV")
    analyseur.add_argument("--tous", action="store_true",
                           help="inclure aussi les champs identiques")
    analyseur.add_argument("--limite", type=int, default=40,
                           help="lignes affichees en console (defaut 40)")
    args = analyseur.parse_args()

    for version in (args.avant, args.apres):
        if not os.path.exists(reference_io.chemin_version(version)):
            print(f"ERREUR : version inconnue {version!r}. Disponibles : "
                  f"{reference_io.versions_disponibles()}", file=sys.stderr)
            raise SystemExit(2)

    lignes, anomalies, resume = compare(args.avant, args.apres, args.tous)
    affiche(lignes, anomalies, resume, limite=args.limite)
    if args.csv:
        ecrit_csv(lignes, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
