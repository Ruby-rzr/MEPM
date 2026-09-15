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
from tests.contrat_unites import (                    # noqa: E402
    BUDGET_ULP_PHASE_4, CORRESPONDANCE_PAR_DEFAUT, NON_DECLARABLE,
    UNITE_PAR_GRANDEUR_MM, UNITE_PAR_GRANDEUR_SI, facteur_du_champ,
    grandeur_du_champ)
from tests.reference_io import (                       # noqa: E402
    CHAMPS_NUMERIQUES, distances_ulp)

COLONNES = ["cas", "champ", "facteur_declare", "n_elements", "n_differents",
            "n_nan_apparus", "n_nan_disparus", "ulp_max", "n_hors_budget",
            "rapport_min", "rapport_max", "ecart_rel_max", "indice_max",
            "valeur_avant", "valeur_apres"]


def facteurs_applicables(doc_avant, doc_apres):
    """Facteurs de conversion a appliquer entre deux versions de reference.

    Si les deux versions declarent le meme systeme d'unites, aucun facteur
    n'est applique et la comparaison redevient une egalite bit a bit. Si elles
    different, les facteurs declares dans tests/contrat_unites.py sont
    appliques a la version anterieure avant comparaison.

    Une reference produite avant la phase 4 ne porte pas de champ
    systeme_unites : elle est en millimetres.
    """
    avant = doc_avant["metadonnees"].get("systeme_unites", "mm_historique")
    apres = doc_apres["metadonnees"].get("systeme_unites", "mm_historique")
    corr_avant = doc_avant["metadonnees"].get("correspondance_champ_grandeur",
                                              CORRESPONDANCE_PAR_DEFAUT)
    if avant == apres:
        facteurs = {champ: 1.0 for champ in CHAMPS_NUMERIQUES}
    else:
        facteurs = {champ: facteur_du_champ(champ, corr_avant)
                    for champ in CHAMPS_NUMERIQUES}
    return facteurs, avant, apres


def statut_du_cas(sorties):
    """Resume textuel du statut d'un cas."""
    lecture = sorties.get("lecture_materiau")
    if lecture and lecture.get("statut") == "exception":
        return f"lecture {lecture['type']}"
    calcul = sorties.get("calcul", {})
    if calcul.get("statut") == "exception":
        return f"calcul {calcul['type']}"
    return "ok"


def compare_champ(avant, apres, facteur=1.0, budget_ulp=BUDGET_ULP_PHASE_4):
    """Compare un champ numerique et retourne ses statistiques d'ecart.

    Args:
        avant, apres: valeurs des deux versions.
        facteur: facteur de conversion declare, applique a 'avant' avant
            comparaison. NON_DECLARABLE si la grandeur n'en a pas : la
            comparaison rapporte alors le rapport observe sans rien exiger.
        budget_ulp: ecart tolere, en ULP, au dela duquel une valeur est
            comptee hors budget.
    """
    a_brut = np.asarray(avant, dtype=np.float64).ravel()
    b = np.asarray(apres, dtype=np.float64).ravel()
    if a_brut.shape != b.shape:
        return dict(forme_differente=True, n_elements=a_brut.size,
                    forme_avant=np.asarray(avant).shape,
                    forme_apres=np.asarray(apres).shape)

    declarable = facteur is not NON_DECLARABLE
    a = a_brut * facteur if declarable else a_brut

    with np.errstate(divide="ignore", invalid="ignore"):
        rapport = np.where((a_brut != 0) & np.isfinite(a_brut) & np.isfinite(b),
                           b / a_brut, np.nan)
    rapports_finis = rapport[np.isfinite(rapport)]
    rapport_min = float(np.min(rapports_finis)) if rapports_finis.size else float("nan")
    rapport_max = float(np.max(rapports_finis)) if rapports_finis.size else float("nan")

    if declarable:
        ulp = distances_ulp(a, b)
        ulp_max = float(np.max(ulp)) if ulp.size else 0.0
        n_hors_budget = int(np.sum(ulp > budget_ulp))
    else:
        ulp_max = float("nan")
        n_hors_budget = 0

    nan_a, nan_b = np.isnan(a), np.isnan(b)
    nan_apparus = int(np.sum(~nan_a & nan_b))
    nan_disparus = int(np.sum(nan_a & ~nan_b))
    if not declarable:
        n_hors_budget = nan_apparus + nan_disparus

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

    commun = dict(forme_differente=False, n_elements=a.size,
                  facteur_declare=("non declarable" if not declarable
                                   else facteur),
                  ulp_max=ulp_max, n_hors_budget=n_hors_budget,
                  rapport_min=rapport_min, rapport_max=rapport_max)

    if n_differents == 0:
        return dict(commun, n_differents=0, n_nan_apparus=0, n_nan_disparus=0,
                    ecart_abs_max=0.0, ecart_rel_max=0.0, indice_max=None,
                    valeur_avant=None, valeur_apres=None)

    if np.any(comparables) and np.nanmax(ecart_abs[comparables], initial=0.0) > 0:
        indice_plat = int(np.nanargmax(np.where(comparables, ecart_abs, -np.inf)))
    else:
        indice_plat = int(np.flatnonzero(~identiques)[0])

    forme = np.asarray(avant).shape
    return dict(
        commun,
        n_differents=n_differents,
        n_nan_apparus=nan_apparus,
        n_nan_disparus=nan_disparus,
        ecart_abs_max=float(np.nanmax(ecart_abs)) if np.any(comparables) else float("nan"),
        ecart_rel_max=float(np.nanmax(ecart_rel)) if np.any(comparables) else float("nan"),
        indice_max=tuple(int(c) for c in np.unravel_index(indice_plat, forme)),
        valeur_avant=float(a[indice_plat]),
        valeur_apres=float(b[indice_plat]),
    )


def compare(version_avant, version_apres, tous=False,
            budget_ulp=BUDGET_ULP_PHASE_4):
    """Compare deux versions et retourne (lignes, anomalies, resume)."""
    doc_a = reference_io.charge(version_avant)
    doc_b = reference_io.charge(version_apres)
    res_a, res_b = doc_a["resultats"], doc_b["resultats"]
    facteurs, unites_avant, unites_apres = facteurs_applicables(doc_a, doc_b)
    corr_a = doc_a["metadonnees"].get("correspondance_champ_grandeur",
                                      CORRESPONDANCE_PAR_DEFAUT)
    corr_b = doc_b["metadonnees"].get("correspondance_champ_grandeur",
                                      CORRESPONDANCE_PAR_DEFAUT)

    anomalies = []
    if corr_a != corr_b:
        for champ in CHAMPS_NUMERIQUES:
            ga, gb = grandeur_du_champ(champ, corr_a), grandeur_du_champ(champ, corr_b)
            if ga != gb:
                anomalies.append(
                    f"CHANGEMENT DE SENS du champ {champ!r} : contenait "
                    f"{ga!r}, contient desormais {gb!r}. Les ecarts rapportes "
                    f"pour ce champ comparent DEUX GRANDEURS DIFFERENTES.")
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
            stats = compare_champ(sa[champ], sb[champ],
                                  facteurs.get(champ, 1.0), budget_ulp)
            if stats.get("forme_differente"):
                anomalies.append(
                    f"forme differente, {identifiant}, {champ} : "
                    f"{stats['forme_avant']} -> {stats['forme_apres']}")
                cas_modifies.add(identifiant)
                continue
            if (stats["n_differents"] == 0 and stats["ulp_max"] in (0.0,)
                    and not tous):
                continue
            if stats["n_differents"]:
                cas_modifies.add(identifiant)
            lignes.append(dict(cas=identifiant, champ=champ, **{
                k: stats[k] for k in COLONNES[2:]}))

    resume = dict(
        version_avant=version_avant,
        version_apres=version_apres,
        unites_avant=unites_avant,
        unites_apres=unites_apres,
        budget_ulp=budget_ulp,
        facteurs=facteurs,
        cas_communs=len(set(res_a) & set(res_b)),
        cas_modifies=len(cas_modifies),
        lignes=len(lignes),
        correspondance_avant=corr_a,
        correspondance_apres=corr_b,
        sha_avant=doc_a["metadonnees"].get("git_sha_court"),
        sha_apres=doc_b["metadonnees"].get("git_sha_court"),
        base_avant=doc_a["metadonnees"].get("base_materiaux_sha256"),
        base_apres=doc_b["metadonnees"].get("base_materiaux_sha256"),
    )
    return lignes, anomalies, resume


def resume_par_champ(lignes, facteurs, budget_ulp, correspondances,
                     systemes=("mm_historique", "SI")):
    """Agrege les ecarts par champ. C'est le tableau principal du livrable."""
    resume = {}
    for champ in CHAMPS_NUMERIQUES:
        resume[champ] = dict(
            champ=champ,
            grandeur_reelle=grandeur_du_champ(champ, correspondances[1]),
            facteur=facteurs.get(champ, 1.0),
            unite_avant=(UNITE_PAR_GRANDEUR_SI if systemes[0] == "SI"
                         else UNITE_PAR_GRANDEUR_MM)[
                grandeur_du_champ(champ, correspondances[0])],
            unite_apres=(UNITE_PAR_GRANDEUR_SI if systemes[1] == "SI"
                         else UNITE_PAR_GRANDEUR_MM)[
                grandeur_du_champ(champ, correspondances[1])],
            n_cas=0, n_elements=0, ulp_max=0.0, n_hors_budget=0,
            rapport_min=float("inf"), rapport_max=float("-inf"),
            n_nan_apparus=0, n_nan_disparus=0)
    for ligne in lignes:
        r = resume[ligne["champ"]]
        r["n_cas"] += 1
        r["n_elements"] += ligne["n_elements"]
        if np.isfinite(ligne["ulp_max"]):
            r["ulp_max"] = max(r["ulp_max"], ligne["ulp_max"])
        elif ligne["ulp_max"] != ligne["ulp_max"]:      # NaN, non declarable
            r["ulp_max"] = float("nan")
        else:
            r["ulp_max"] = float("inf")
        r["n_hors_budget"] += ligne["n_hors_budget"]
        r["n_nan_apparus"] += ligne["n_nan_apparus"]
        r["n_nan_disparus"] += ligne["n_nan_disparus"]
        if np.isfinite(ligne["rapport_min"]):
            r["rapport_min"] = min(r["rapport_min"], ligne["rapport_min"])
        if np.isfinite(ligne["rapport_max"]):
            r["rapport_max"] = max(r["rapport_max"], ligne["rapport_max"])
    return resume


def affiche_resume_par_champ(resume, budget_ulp):
    largeurs = [8, 10, 16, 14, 14, 10, 13, 26]
    entetes = ["champ", "contenu", "facteur declare", "unite avant",
               "unite apres", "ULP max", "hors budget", "rapport observe"]
    print(f"\n  Budget accorde : {budget_ulp} ULP par valeur.\n")
    print("  " + "  ".join(e.ljust(l) for e, l in zip(entetes, largeurs)))
    print("  " + "  ".join("-" * l for l in largeurs))
    for champ in CHAMPS_NUMERIQUES:
        r = resume[champ]
        if r["facteur"] is NON_DECLARABLE:
            facteur = "non declarable"
            ulp = "n/a"
        else:
            facteur = f"{r['facteur']:.0e}" if r["facteur"] != 1.0 else "1"
            ulp = f"{r['ulp_max']:.0f}"
        if r["rapport_min"] > r["rapport_max"]:
            plage = "identique"
        elif r["rapport_min"] == r["rapport_max"]:
            plage = f"{r['rapport_min']:.6e}"
        else:
            plage = f"[{r['rapport_min']:.3e}, {r['rapport_max']:.3e}]"
        cellules = [champ.ljust(largeurs[0]),
                    r["grandeur_reelle"].ljust(largeurs[1]),
                    facteur.ljust(largeurs[2]),
                    r["unite_avant"].ljust(largeurs[3]),
                    r["unite_apres"].ljust(largeurs[4]),
                    ulp.rjust(largeurs[5]),
                    str(r["n_hors_budget"]).rjust(largeurs[6]),
                    plage.ljust(largeurs[7])]
        print("  " + "  ".join(cellules))
    total = sum(r["n_hors_budget"] for r in resume.values())
    print(f"\n  TOTAL HORS BUDGET : {total}")
    return total


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
    print(f"  unites      : {resume['unites_avant']} -> {resume['unites_apres']}")
    print(f"  champs      : {resume['correspondance_avant']} -> "
          f"{resume['correspondance_apres']}")
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

    par_champ = resume_par_champ(
        lignes, resume["facteurs"], resume["budget_ulp"],
        (resume["correspondance_avant"], resume["correspondance_apres"]),
        (resume["unites_avant"], resume["unites_apres"]))
    print("\nSynthese par champ :")
    affiche_resume_par_champ(par_champ, resume["budget_ulp"])

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
    analyseur.add_argument("--budget-ulp", type=int,
                           default=BUDGET_ULP_PHASE_4, dest="budget_ulp",
                           help=f"ecart tolere en ULP (defaut "
                                f"{BUDGET_ULP_PHASE_4}, phase 4 uniquement)")
    args = analyseur.parse_args()

    for version in (args.avant, args.apres):
        if not os.path.exists(reference_io.chemin_version(version)):
            print(f"ERREUR : version inconnue {version!r}. Disponibles : "
                  f"{reference_io.versions_disponibles()}", file=sys.stderr)
            raise SystemExit(2)

    lignes, anomalies, resume = compare(args.avant, args.apres, args.tous,
                                        args.budget_ulp)
    affiche(lignes, anomalies, resume, limite=args.limite)
    if args.csv:
        ecrit_csv(lignes, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
