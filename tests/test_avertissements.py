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
  #12 calculateReqError applique la formule cylindrique quelle que soit la
      geometrie. Avec Ri nul, elle divise par zero, d'ou les deux
      avertissements par appel.

Quand la phase 7 corrigera Ri = 0 en conique, le compte changera et ce test se
declenchera. C'est voulu : il obligera a constater le changement plutot qu'a
le subir.

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
     "divide by zero encountered in divide"): 304,
    ("RuntimeWarning", "calculateReqError.py",
     "invalid value encountered in scalar divide"): 304,
}

# Les 19 cas concernes sont tous coniques, avec K = 0 et R = 0, donc Ri = 0.
CAS_ATTENDUS = {
    f"A|{loi}|tapered|{geo}|{mode}"
    for loi in ("bingham_synthetique", "carreau_PLA_solvent_cast_25",
                "newtonien_synthetique")
    for geo in ("De=0.25", "De=0.45", "De=0.6")
    for mode in ("analytique", "mP_seul_aberrant")
} | {"A|newtonien_synthetique|tapered|heterogene|analytique"}

OCCURRENCES_PAR_CAS = 32


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
    """Exactement 19 cas emettent des avertissements, et ce sont ceux-la."""
    par_cas, _ = avertissements_captures
    obtenus = set(par_cas)
    assert obtenus == CAS_ATTENDUS, (
        "\nLe jeu des cas emettant des avertissements a change.\n"
        f"  apparus  : {sorted(obtenus - CAS_ATTENDUS)}\n"
        f"  disparus : {sorted(CAS_ATTENDUS - obtenus)}\n"
        "Si la phase 7 a corrige Ri = 0 en conique, c'est attendu : mettre a "
        "jour ce test en connaissance de cause.")
    assert len(obtenus) == 19


def test_signatures_et_comptes(avertissements_captures):
    """Les signatures et les occurrences totales sont celles attendues."""
    _, total = avertissements_captures
    assert dict(total) == SIGNATURES_ATTENDUES, (
        "\nLes avertissements emis ont change.\n"
        f"  obtenu  : {dict(total)}\n"
        f"  attendu : {SIGNATURES_ATTENDUES}")
    assert sum(total.values()) == 608


def test_occurrences_par_cas(avertissements_captures):
    """Chaque cas emetteur emet 32 occurrences, 16 par signature."""
    par_cas, _ = avertissements_captures
    anomalies = [f"{identifiant} : {sum(sig.values())}"
                 for identifiant, sig in par_cas.items()
                 if sum(sig.values()) != OCCURRENCES_PAR_CAS]
    assert not anomalies, ("\nNombre d'occurrences inattendu :\n  " +
                           "\n  ".join(anomalies))
