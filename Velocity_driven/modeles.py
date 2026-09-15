#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Choix explicite de la loi rhéologique et du mode de calcul.

Phase 5 de la refonte. Deux choix étaient auparavant DEVINÉS par le code :

  - la loi rhéologique, par une cascade de `if` testant quels paramètres
    valaient zéro dans la base de matériaux ;
  - le mode de calcul, analytique ou empirique, par `if R != 0` dans
    calculateReq et `if mP != 0` dans calculatePrequired, deux interrupteurs
    indépendants donnant quatre combinaisons dont deux sans aucun sens.

Les deux sont désormais des champs explicites. La déduction historique
subsiste dans ce module, isolée, documentée et appelée depuis un seul endroit,
le lecteur de l'ancienne base `materials.xls` qui ne porte pas ces champs.
C'est le seul endroit du dépôt où quelque chose est encore deviné.

Auteurs : contribution de la refonte. Le code modélisé est de David Brzeski,
Jean-François Chauvette et Raphaël Plante.
"""

# --- Lois rhéologiques ------------------------------------------------------
SISKO = "sisko"
NEWTONIEN = "newtonien"
LOI_DE_PUISSANCE = "loi_de_puissance"
CARREAU = "carreau"
BINGHAM = "bingham"
HERSCHEL_BULKLEY = "herschel_bulkley"
HERSCHEL_BULKLEY_ETENDU = "herschel_bulkley_etendu"

MODELES = (SISKO, NEWTONIEN, LOI_DE_PUISSANCE, CARREAU, BINGHAM,
           HERSCHEL_BULKLEY, HERSCHEL_BULKLEY_ETENDU)

# Lois à seuil d'écoulement. La correction de Weissenberg-Rabinowitsch
# appliquée par le modèle est celle d'une loi de puissance : elle n'est exacte
# pour aucune de ces lois. Voir le défaut #7, traité en phase 7.
MODELES_A_SEUIL = (BINGHAM, HERSCHEL_BULKLEY, HERSCHEL_BULKLEY_ETENDU)

# --- Modes de calcul --------------------------------------------------------
# Prédiction pure, aucun paramètre ajusté. C'est le seul mode publiable.
ANALYTIQUE = "analytique"
# Ajustement à deux paramètres R et mP sur des mesures. La sortie n'est PAS
# une prédiction. Voir CLAUDE.md.
EMPIRIQUE = "empirique"

MODES = (ANALYTIQUE, EMPIRIQUE)


def valide_modele(modele):
    """Lève une erreur si le modèle n'est pas l'un des modèles connus."""
    if modele not in MODELES:
        raise ValueError(
            f"Modèle rhéologique inconnu : {modele!r}. "
            f"Valeurs admises : {', '.join(MODELES)}.")
    return modele


def valide_mode(mode):
    """Lève une erreur si le mode n'est pas l'un des modes connus."""
    if mode not in MODES:
        raise ValueError(
            f"Mode de calcul inconnu : {mode!r}. "
            f"Valeurs admises : {', '.join(MODES)}.")
    return mode


def deduire_modele_historique(n, K, eta_inf, eta_0, tau_0, lmbda, a):
    """Devine la loi rhéologique d'après les paramètres nuls ou non.

    ADAPTATEUR DE COMPATIBILITÉ, RÉSERVÉ À L'ANCIENNE BASE materials.xls.
    Cette cascade reproduit exactement, dans le même ordre, les conditions qui
    étaient écrites dans calculateVisco. Elle n'est appelée que par le lecteur
    de l'ancienne base, qui ne porte pas de champ de modèle. Tout nouveau
    matériau déclare sa loi explicitement.

    Elle est fragile par nature : un paramètre laissé à zéro par oubli change
    silencieusement la loi appliquée. C'est précisément la raison pour
    laquelle elle ne sert plus qu'ici.

    Args:
        n (float): indice d'écoulement. [-]
        K (float): indice de consistance. [Pa.s^n]
        eta_inf (float): viscosité infinie. [Pa.s]
        eta_0 (float): viscosité au repos. [Pa.s]
        tau_0 (float): seuil d'écoulement. [Pa]
        lmbda (float): temps de relaxation. [s]
        a (float): exposant du modèle de Carreau. [-]

    Returns:
        str: l'un des MODELES.

    Raises:
        ValueError: si aucune combinaison ne correspond, comme auparavant.
    """
    if n != 0 and K != 0 and eta_inf != 0 and eta_0 == 0 and tau_0 == 0 and lmbda == 0 and a == 0:
        return SISKO
    if n == 1 and K == 0 and eta_inf != 0 and eta_0 == 0 and tau_0 == 0 and lmbda == 0 and a == 0:
        return NEWTONIEN
    if n != 0 and K != 0 and eta_inf == 0 and eta_0 == 0 and tau_0 == 0 and lmbda == 0 and a == 0:
        return LOI_DE_PUISSANCE
    if n != 0 and K == 0 and eta_inf != 0 and eta_0 != 0 and tau_0 == 0 and lmbda != 0 and a != 0:
        return CARREAU
    if n == 1 and K == 0 and eta_inf != 0 and eta_0 == 0 and tau_0 != 0 and lmbda == 0 and a == 0:
        return BINGHAM
    if n != 0 and K != 0 and eta_inf != 0 and eta_0 == 0 and tau_0 != 0 and lmbda == 0 and a == 0:
        return HERSCHEL_BULKLEY_ETENDU
    if n != 0 and K != 0 and eta_inf == 0 and eta_0 == 0 and tau_0 != 0 and lmbda == 0 and a == 0:
        return HERSCHEL_BULKLEY
    raise ValueError('No model was found for your material')


def deduire_mode_historique(R, mP):
    """Devine le mode de calcul d'après R et mP.

    ADAPTATEUR DE COMPATIBILITÉ, RÉSERVÉ À L'ANCIENNE BASE materials.xls.

    L'ancien code portait deux interrupteurs INDÉPENDANTS, `if R != 0` dans
    calculateReq et `if mP != 0` dans calculatePrequired, soit quatre
    combinaisons :

        R = 0, mP = 0   prédiction analytique
        R != 0, mP != 0 ajustement empirique complet
        R != 0, mP = 0  aberrant, une résistance ajustée avec l'exposant n
        R = 0, mP != 0  aberrant, une résistance prédite avec l'exposant mP

    Les deux dernières ne correspondent à rien et rendaient des pressions
    absurdes, proches de l'ambiante ou astronomiques, sans le moindre message.
    Elles n'existent plus : elles lèvent désormais une erreur. Un matériau dont
    un seul des deux paramètres ajustés est renseigné est une donnée
    incomplète, pas un troisième mode de calcul.

    Args:
        R (float): résistance ajustée. Unité indéterminée.
        mP (float): exposant ajusté. [-]

    Returns:
        str: ANALYTIQUE ou EMPIRIQUE.

    Raises:
        ValueError: si un seul des deux paramètres est non nul.
    """
    if R == 0 and mP == 0:
        return ANALYTIQUE
    if R != 0 and mP != 0:
        return EMPIRIQUE
    raise ValueError(
        f"Paramètres d'ajustement incomplets : R = {R!r}, mP = {mP!r}. "
        "Le mode empirique exige les deux, le mode analytique n'en exige "
        "aucun. Un seul des deux ne définit aucun mode de calcul : c'est une "
        "donnée incomplète dans la base de matériaux.")
