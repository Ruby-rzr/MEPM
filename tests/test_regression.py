#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de non-regression du MEPM, phase 2 de la refonte.

Rejoue la reference active (tests/reference_io.VERSION_ACTIVE) et exige une
egalite BIT A BIT. Il n'y a aucune tolerance : a ce stade, rien n'est cense
bouger. Un ecart, meme au dernier bit, est un echec, et le message nomme le
cas, le champ et l'indice de l'element fautif.

Ces tests gelent le comportement ACTUEL, defauts compris. Les exceptions
levees par readMaterial (defaut #10) et par validateReynolds quand rho vaut
zero (defaut #19) sont enregistrees comme comportement attendu. Quand la
phase 5 corrigera readMaterial, ces tests echoueront bruyamment : c'est
voulu, c'est le mecanisme qui oblige a prendre la decision consciemment et a
produire une nouvelle version de reference.

Lancement :
    python3 -m pytest tests -q

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import os
import sys
import warnings

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import numpy as np                                    # noqa: E402

from tests import reference_io                        # noqa: E402
from tests.reference_io import (                       # noqa: E402
    BASE_MATERIAUX, CHAMPS_NUMERIQUES, decrit_ecart, differences, execute,
    sha256_fichier)

REFERENCE = reference_io.charge()
RESULTATS = REFERENCE["resultats"]
METADONNEES = REFERENCE["metadonnees"]
IDENTIFIANTS = sorted(RESULTATS)

# La base de materiaux est une entree du modele au meme titre que le code.
# Si elle a change, la famille B ne compare plus la meme chose.
SHA_BASE_ATTENDU = METADONNEES["base_materiaux_sha256"]
SHA_BASE_COURANT = sha256_fichier(BASE_MATERIAUX)
BASE_INCHANGEE = SHA_BASE_COURANT == SHA_BASE_ATTENDU


# ---------------------------------------------------------------------------
# Integrite
# ---------------------------------------------------------------------------

def test_integrite_base_materiaux():
    """materials.xls doit etre celui sur lequel la reference a ete produite."""
    assert BASE_INCHANGEE, (
        "\nLa base de materiaux a change depuis la production de la "
        f"reference {reference_io.VERSION_ACTIVE!r}.\n"
        f"  fichier  : {BASE_MATERIAUX}\n"
        f"  attendu  : {SHA_BASE_ATTENDU}\n"
        f"  obtenu   : {SHA_BASE_COURANT}\n"
        "Aucune comparaison de la famille B n'est tentee tant que ce point "
        "n'est pas tranche : soit la base est restauree, soit une nouvelle "
        "version de reference est produite et l'ecart est justifie.")


def test_integrite_de_la_reference():
    """Le fichier de reference n'a pas ete edite depuis sa production."""
    empreinte = reference_io.hashlib.sha256(
        reference_io.json.dumps(RESULTATS, sort_keys=True,
                                ensure_ascii=False).encode("utf-8")).hexdigest()
    assert empreinte == REFERENCE["sha256_des_resultats"], (
        "\nLe contenu de la reference ne correspond plus a son empreinte.\n"
        f"  attendu : {REFERENCE['sha256_des_resultats']}\n"
        f"  obtenu  : {empreinte}\n"
        "Une reference ne s'edite pas a la main, elle se regenere sous un "
        "nouveau nom de version.")


def test_nombre_de_cas():
    """Aucun cas n'a disparu de la reference."""
    assert len(IDENTIFIANTS) == REFERENCE["nombre_de_cas"]
    assert len(IDENTIFIANTS) > 0


def test_versions_environnement():
    """Avertit, sans echouer, si l'environnement differe de la reference."""
    attendu = {"Python": METADONNEES["python"], "numpy": METADONNEES["numpy"]}
    import platform
    obtenu = {"Python": platform.python_version(), "numpy": np.__version__}
    ecarts = [f"{k} : reference={attendu[k]} courant={obtenu[k]}"
              for k in attendu if attendu[k] != obtenu[k]]
    if ecarts:
        warnings.warn(
            "\nL'environnement differe de celui de la reference "
            f"{reference_io.VERSION_ACTIVE!r} :\n  " + "\n  ".join(ecarts) +
            "\nUn ecart bit a bit peut venir de la, et non du code.",
            UserWarning, stacklevel=1)


# ---------------------------------------------------------------------------
# Rejeu des cas
# ---------------------------------------------------------------------------

def _compare_bloc_statut(identifiant, nom, attendu, obtenu, anomalies):
    """Compare un bloc {statut, type, message} a l'identique."""
    if attendu is None and obtenu is None:
        return
    if attendu is None or obtenu is None:
        anomalies.append(f"cas {identifiant!r}, bloc {nom!r} : "
                         f"reference={attendu!r} obtenu={obtenu!r}")
        return
    for cle in ("statut", "type", "message"):
        a, b = attendu.get(cle), obtenu.get(cle)
        if a != b:
            anomalies.append(f"cas {identifiant!r}, bloc {nom!r}, "
                             f"champ {cle!r} :\n    reference={a!r}\n"
                             f"    obtenu   ={b!r}")


def _compare_parametres(identifiant, attendu, obtenu, anomalies):
    """Compare les parametres materiau, bit a bit."""
    if attendu is None and obtenu is None:
        return
    if attendu is None or obtenu is None:
        anomalies.append(f"cas {identifiant!r} : presence de "
                         f"'parametres_materiau' incoherente")
        return
    if set(attendu) != set(obtenu):
        anomalies.append(
            f"cas {identifiant!r}, parametres_materiau : cles differentes, "
            f"reference={sorted(attendu)} obtenu={sorted(obtenu)}")
        return
    for cle in sorted(attendu):
        _, _, ecarts = differences(attendu[cle], obtenu[cle])
        if ecarts:
            anomalies.append(
                f"cas {identifiant!r}, parametres_materiau[{cle!r}] : "
                f"reference={attendu[cle]!r} obtenu={obtenu[cle]!r}")


@pytest.mark.parametrize("identifiant", IDENTIFIANTS)
def test_cas(identifiant):
    """Rejoue un cas de la reference et exige une egalite bit a bit."""
    enregistrement = RESULTATS[identifiant]
    entrees = enregistrement["entrees"]
    attendu = enregistrement["sorties"]

    if entrees["famille"] == "B" and not BASE_INCHANGEE:
        pytest.skip("materials.xls a change, voir test_integrite_base_materiaux")

    obtenu = execute(entrees, attendu.get("parametres_materiau"))

    anomalies = []

    if attendu.get("alpha") != obtenu.get("alpha"):
        anomalies.append(f"cas {identifiant!r}, alpha : "
                         f"reference={attendu.get('alpha')!r} "
                         f"obtenu={obtenu.get('alpha')!r}")

    _compare_bloc_statut(identifiant, "lecture_materiau",
                         attendu.get("lecture_materiau"),
                         obtenu.get("lecture_materiau"), anomalies)
    _compare_bloc_statut(identifiant, "calcul", attendu.get("calcul"),
                         obtenu.get("calcul"), anomalies)

    # La famille A fournit ses parametres, les comparer n'aurait aucun sens.
    # La famille B les relit depuis materials.xls : la lecture est testee.
    if entrees["famille"] == "B":
        _compare_parametres(identifiant, attendu.get("parametres_materiau"),
                            obtenu.get("parametres_materiau"), anomalies)

    for champ in CHAMPS_NUMERIQUES:
        present_ref = champ in attendu
        present_obt = champ in obtenu
        if present_ref != present_obt:
            anomalies.append(
                f"cas {identifiant!r}, champ {champ!r} : present dans la "
                f"reference={present_ref}, dans le resultat={present_obt}")
            continue
        if not present_ref:
            continue
        forme_ref, forme_obt, ecarts = differences(attendu[champ], obtenu[champ])
        if forme_ref != forme_obt:
            anomalies.append(
                f"cas {identifiant!r}, champ {champ!r} : forme "
                f"reference={forme_ref} obtenu={forme_obt}")
            continue
        if ecarts:
            anomalies.append(decrit_ecart(identifiant, champ, forme_ref, ecarts))

    assert not anomalies, "\n" + "\n".join(anomalies)
