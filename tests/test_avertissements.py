#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gel des avertissements d'execution emis par le modele.

Le bruit devient un garde-fou. Les RuntimeWarning emis pendant le rejeu de la
reference ne sont ni filtres ni resumes : leur nombre, leur nature et les cas
qui les produisent sont figes ici.

Ils documentent deux defauts du diagnostic :
  #11 en buse conique, la resistance n'utilise que K et n, jamais eta. Pour un
      materiau dont K vaut zero (newtonien, Carreau, Bingham), Ri vaut zero et
      la pression calculee se reduit a P_amb.
  #12 calculateReqError applique la propagation cylindrique quelle que soit la
      geometrie. Avec Ri nul, le rapport dRi/Ri^2 vaut zero sur zero, d'ou
      l'avertissement.

HISTORIQUE DES MISES A JOUR, chacune consentie apres declenchement du test.

  phase 3      608 occurrences, 19 cas, deux signatures, une division par zero
               et une valeur invalide, emises dans une boucle sur les buses.
  defaut #20    76 occurrences, 19 cas, une seule signature. La boucle a ete
               remplacee par un calcul vectorise et la division par zero a
               disparu de l'expression de dRi. Les 19 cas emetteurs sont
               restes LES MEMES, ce qui a confirme que la cause n'avait pas
               bouge.
  defauts #10 et #19   240 occurrences, 29 cas. Dix cas de plus, qui levaient
               auparavant une exception et qui calculent desormais. La cause
               est inchangee.

Le jeu des cas emetteurs n'est plus fige sous forme de liste : il est DERIVE
DE LA CAUSE, a savoir une buse conique dont la resistance analytique vaut zero
parce que K vaut zero. Une liste recopiee ne dirait pas pourquoi ces cas-la.
Quand la phase 7 corrigera Ri = 0 en conique, l'ensemble derive deviendra vide
et ce test se declenchera.

Le test n'assert pas les numeros de ligne, qui bougeraient au moindre
reformatage. Il assert la categorie, le fichier et le message.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import os
import sys
import warnings
from collections import Counter

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import pytest                                          # noqa: E402

from tests import reference_io                         # noqa: E402
from tests.reference_io import execute                 # noqa: E402

# Signatures attendues : (categorie, fichier, message).
SIGNATURES_ATTENDUES = {
    ("RuntimeWarning", "calculateReqError.py",
     "invalid value encountered in divide"): 240,
}

NOMBRE_DE_CAS_ATTENDU = 29


def cas_a_resistance_conique_nulle(reference):
    """Cas ou la resistance conique analytique vaut zero, donc ou Ri = 0.

    C'est la CAUSE des avertissements : en buse conique, calculateReq n'utilise
    que K et n, jamais eta (defaut #11). Quand K vaut zero, ce qui est le cas
    des lois newtonienne, de Carreau et de Bingham, la resistance est nulle, et
    calculateReqError divise alors zero par zero (defaut #12).

    La branche empirique, R non nul, remplace la resistance analytique par le
    parametre ajuste et n'est donc pas concernee.
    """
    concernes = set()
    for identifiant, enregistrement in reference["resultats"].items():
        entrees, sorties = enregistrement["entrees"], enregistrement["sorties"]
        if entrees["Noz_type"] != "tapered":
            continue
        if sorties.get("calcul", {}).get("statut") != "ok":
            continue
        parametres = sorties.get("parametres_materiau", {})
        if parametres.get("K", 1.0) != 0.0:
            continue
        if entrees.get("R", parametres.get("R", 0.0)) != 0.0:
            continue
        concernes.add(identifiant)
    return concernes


@pytest.fixture(scope="module")
def avertissements_captures():
    """Rejoue tous les cas de la reference en capturant les avertissements."""
    reference = reference_io.charge()
    par_cas = {}
    total = Counter()
    for identifiant, enregistrement in sorted(reference["resultats"].items()):
        with warnings.catch_warnings(record=True) as captures:
            warnings.simplefilter("always")
            execute(enregistrement["entrees"],
                    enregistrement["sorties"].get("parametres_materiau"))
        if captures:
            signatures = Counter(
                (w.category.__name__, os.path.basename(w.filename),
                 str(w.message)) for w in captures)
            par_cas[identifiant] = signatures
            total.update(signatures)
    return par_cas, total


def test_cas_emetteurs(avertissements_captures):
    """Les cas emetteurs sont exactement ceux dont la resistance conique est nulle."""
    par_cas, _ = avertissements_captures
    obtenus = set(par_cas)
    attendus = cas_a_resistance_conique_nulle(reference_io.charge())
    assert obtenus == attendus, (
        "\nLes avertissements ne viennent plus exactement des cas a "
        "resistance conique nulle.\n"
        f"  emettent sans raison connue : {sorted(obtenus - attendus)}\n"
        f"  devraient emettre et n'emettent plus : {sorted(attendus - obtenus)}\n"
        "Si la phase 7 a corrige Ri = 0 en conique, c'est attendu : mettre a "
        "jour ce test en connaissance de cause.")
    assert len(obtenus) == NOMBRE_DE_CAS_ATTENDU, (
        f"\n{len(obtenus)} cas emetteurs au lieu de "
        f"{NOMBRE_DE_CAS_ATTENDU}. Le compte a change, dire pourquoi.")


def test_signatures_et_comptes(avertissements_captures):
    """Les signatures et les occurrences totales sont celles attendues."""
    _, total = avertissements_captures
    assert dict(total) == SIGNATURES_ATTENDUES, (
        "\nLes avertissements emis ont change.\n"
        f"  obtenu  : {dict(total)}\n"
        f"  attendu : {SIGNATURES_ATTENDUES}")
    assert sum(total.values()) == 240


def test_occurrences_par_cas(avertissements_captures):
    """Chaque cas emetteur emet exactement une occurrence par vitesse.

    calculateReqError est appelee une fois par vitesse, et le calcul de dRi y
    est vectorise sur les buses depuis la correction du defaut #20. Le nombre
    d'occurrences ne depend donc que du nombre de vitesses du cas, pas du
    nombre de buses.
    """
    par_cas, _ = avertissements_captures
    reference = reference_io.charge()
    anomalies = []
    for identifiant, signatures in par_cas.items():
        attendu = len(reference["resultats"][identifiant]["entrees"]["v"])
        obtenu = sum(signatures.values())
        if obtenu != attendu:
            anomalies.append(f"{identifiant} : {obtenu} occurrences pour "
                             f"{attendu} vitesses")
    assert not anomalies, ("\nNombre d'occurrences inattendu :\n  " +
                           "\n  ".join(anomalies))
