#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic : le seuil d'ecoulement compte-t-il dans ma plage de vitesses ?

SCRIPT AUTONOME, HORS DU CHEMIN DE CALCUL. Il n'importe aucune fonction du
modele et ne modifie rien. Les formules y sont reecrites, volontairement : il
doit rester un controle INDEPENDANT, qu'une modification du modele ne peut pas
casser silencieusement.

Il ne lit du depot que la base de materiaux, et seulement si on le lui demande.

POURQUOI CE SCRIPT
La chaine cylindrique du MEPM donne, pour un fluide de Herschel-Bulkley,

    Delta_P = 4 L (tau_y + K gamma_paroi^n) / D

ou le bilan de forces et la loi de comportement sont exacts, mais ou
gamma_paroi est tire du debit par la correction de Weissenberg-Rabinowitsch
d'une LOI DE PUISSANCE, (3n+1)/(4n), qui ignore le bouchon central. C'est le
defaut #7 du registre.

L'ampleur de ce probleme depend entierement de la part que le seuil prend dans
la contrainte parietale. Si cette part est de l'ordre du centieme de pour
cent, comme pour Parrafin wax-40%, traiter le materiau en loi de puissance
pure suffit et la phase 7 se reduit a l'extension conique. Si elle est de
l'ordre de la dizaine de pour cent, la solution exacte de l'ecoulement
Herschel-Bulkley en conduite devient necessaire.

LE CRITERE EST LA PART DU SEUIL PONDEREE PAR LA CHUTE DE PRESSION
En buse conique, la part du seuil est la plus grande a l'ENTREE, ou le
cisaillement est le plus faible. Mais le gradient de pression local varie comme
R^(-3n-1) : la chute de pression se concentre cote SORTIE, et la part elevee de
l'entree s'applique a une portion qui pese presque rien. Sur EC3515-8% avec un
seuil de 120 Pa a 10 mm/s, 78 pour cent de Delta_P s'accumulent dans le tiers
du cone cote sortie.

Le critere qui decide est donc la part du seuil MOYENNEE le long de la buse et
PONDEREE par la contribution locale a Delta_P :

    f_ponderee = integrale( (tau_y/tau_w) dP/dz dz ) / integrale( dP/dz dz )

Avec dP/dz = 2 tau_w(R)/R, le numerateur se simplifie en integrale(2 tau_y/R),
et f_ponderee est EXACTEMENT l'ecart relatif sur Delta_P entre un traitement a
seuil et un traitement en loi de puissance pure. C'est la generalisation, a une
section variable, de l'identite valable pour une section unique.

Les parts en entree et en sortie sont conservees et affichees : elles encadrent
la ponderee, qui ne peut pas sortir de leur intervalle.

CE QUE CE SCRIPT NE FAIT PAS
Il ne calcule PAS la solution exacte de l'ecoulement Herschel-Bulkley. Il
mesure la PART DU SEUIL dans la contrainte parietale, evaluee avec la
correction de la loi de puissance. C'est une estimation de premier ordre, et
elle est utilisee ici comme INDICATEUR, pas comme borne d'erreur.

  DEMONTRE   la part du seuil ponderee est exactement l'ecart relatif sur
             Delta_P entre le traitement a seuil et le traitement en loi de
             puissance pure, puisque dP/dz est proportionnel a tau_w.
  SUPPOSE    l'erreur due au bouchon central, celle que la correction de
             Rabinowitsch manque, est du MEME ORDRE. Ce n'est pas demontre. La
             quantifier demande la solution exacte, qui sera ecrite en phase 7
             a partir des equations de reference.

Usage :

    python3 tools/nombre_de_bingham.py --materiau "Parrafin wax-40%"

    python3 tools/nombre_de_bingham.py --K 4363 --n 0.31 --tau-y 120 \\
        --De 0.45 --Do 3.55 --L 17.25

    python3 tools/nombre_de_bingham.py --materiau EC3515-8% --tau-y 120 \\
        --vitesses 5 10 20 50 100

Toutes les grandeurs de la ligne de commande sont dans les unites d'atelier :
diametres et longueurs en mm, vitesses en mm/s. K, tau_y et les contraintes
sont en SI.

Auteurs : contribution de la refonte. Le code modelise est de David Brzeski,
Jean-Francois Chauvette et Raphael Plante.
"""

import argparse
import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

MILLIMETRE = 1e-3          # 1 mm en m

# ---------------------------------------------------------------------------
# Bornes du verdict.
#
# Elles portent sur la part du seuil PONDEREE par la chute de pression, qui est
# exactement l'ecart relatif sur Delta_P entre un traitement a seuil et un
# traitement en loi de puissance pure. Pas sur la part en sortie, pas sur le
# maximum entre les sections : voir la docstring de module.
#
# Le choix de 1 pour cent : en dessous, negliger le seuil deplace la pression
# predite de moins d'un centieme, ce qui est petit devant la dispersion
# habituelle d'un ajustement rheologique et devant l'incertitude de mesure
# d'une pression d'extrusion. Ce n'est PAS une valeur mesuree sur ce montage :
# c'est une tolerance de modelisation, assumee comme telle et modifiable par
# --negligeable.
#
# Le choix de 10 pour cent : au-dela, le seuil deplace la pression d'un
# dixieme au moins, ce qu'aucun ajustement ne rattrape sans biaiser K et n. Le
# bouchon central occupe alors une fraction non marginale de la section et la
# correction de Rabinowitsch d'une loi de puissance n'est plus defendable.
#
# Entre les deux, le seuil est dit MARGINAL : il faut le porter dans le
# modele, mais l'erreur du traitement actuel reste du meme ordre que
# l'incertitude sur les parametres.
SEUIL_NEGLIGEABLE_PAR_DEFAUT = 0.01     # 1 %
SEUIL_GOUVERNANT_PAR_DEFAUT = 0.10      # 10 %

VITESSES_PAR_DEFAUT = [10.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0]

# Nombre de tranches de l'integration numerique le long de l'axe. 2000 suffit :
# l'ecart a la forme fermee est verifie sous 1e-6 en relatif par
# tests/test_nombre_de_bingham.py.
TRANCHES_INTEGRATION = 2000

# Portion de la longueur, cote sortie, dont on rapporte la contribution a
# Delta_P. C'est l'indicateur qui explique l'ecart entre la part en sortie, la
# part en entree et la ponderee.
FRACTION_LONGUEUR_COTE_SORTIE = 1.0 / 3.0


def debit_volumique(diametre_sortie_m, vitesse_m_par_s):
    """Debit volumique d'une buse. [m^3/s]

    Args:
        diametre_sortie_m (float): diametre de sortie. [m]
        vitesse_m_par_s (float): vitesse debitante en sortie. [m/s]
    """
    return math.pi * 0.25 * diametre_sortie_m ** 2 * vitesse_m_par_s


def cisaillement_apparent(debit_m3_par_s, diametre_m):
    """Taux de cisaillement parietal APPARENT, dit de Newton. [1/s]

        gamma_apparent = 32 Q / (pi D^3)

    C'est la valeur que donnerait un fluide newtonien. Elle ne depend d'aucun
    parametre rheologique.
    """
    return 32.0 * debit_m3_par_s / (math.pi * diametre_m ** 3)


def correction_rabinowitsch(n):
    """Facteur (3n+1)/(4n) de Weissenberg-Rabinowitsch, loi de puissance. [-]

    ATTENTION : exact pour une loi de puissance SANS seuil. C'est tout l'objet
    du defaut #7. Il est utilise ici faute de mieux, et le resultat du script
    sert precisement a decider s'il faut le remplacer.
    """
    return (3.0 * n + 1.0) / (4.0 * n)


def cisaillement_corrige(debit_m3_par_s, diametre_m, n):
    """Taux de cisaillement parietal corrige de Rabinowitsch. [1/s]"""
    return cisaillement_apparent(debit_m3_par_s, diametre_m) * \
        correction_rabinowitsch(n)


def contrainte_parietale(K, n, tau_y, cisaillement_1_par_s):
    """Contrainte parietale d'un Herschel-Bulkley evaluee a la paroi. [Pa]

        tau_paroi = tau_y + K gamma_paroi^n

    Args:
        K (float): indice de consistance. [Pa.s^n]
        n (float): indice d'ecoulement. [-]
        tau_y (float): seuil d'ecoulement. [Pa]
        cisaillement_1_par_s (float): taux de cisaillement parietal. [1/s]

    Returns:
        (tau_paroi, tau_visqueux) en Pa.
    """
    tau_visqueux = K * cisaillement_1_par_s ** n
    return tau_y + tau_visqueux, tau_visqueux


def rayon_a_l_abscisse(abscisse_reduite, rayon_sortie_m, rayon_entree_m):
    """Rayon de la buse a une abscisse reduite, 0 a l'entree et 1 a la sortie.

    Le rayon varie lineairement avec l'abscisse : c'est l'hypothese de la buse
    conique du modele. Pour une buse cylindrique, les deux rayons sont egaux et
    le profil est constant.
    """
    return rayon_entree_m + (rayon_sortie_m - rayon_entree_m) * abscisse_reduite


def profil_le_long_de_la_buse(K, n, tau_y, debit_m3_par_s, rayon_sortie_m,
                              rayon_entree_m, abscisse_debut=0.0,
                              abscisse_fin=1.0, tranches=None):
    """Echantillonne la buse sur un intervalle d'abscisse reduite.

    Args:
        K (float): indice de consistance. [Pa.s^n]
        n (float): indice d'ecoulement. [-]
        tau_y (float): seuil d'ecoulement. [Pa]
        debit_m3_par_s (float): debit volumique. [m^3/s]
        rayon_sortie_m, rayon_entree_m (float): rayons aux deux extremites. [m]
        abscisse_debut, abscisse_fin (float): bornes en abscisse reduite, 0 a
            l'entree et 1 a la sortie. L'echantillonnage est uniforme sur cet
            intervalle, de sorte que toute borne est atteinte exactement.
        tranches (int): nombre de tranches, TRANCHES_INTEGRATION par defaut.

    Returns:
        (pas, rayons, tau_paroi, gradient), ou gradient vaut dP/dz a un facteur
        multiplicatif constant pres, qui se simplifie dans tous les rapports
        calcules ici.
    """
    tranches = TRANCHES_INTEGRATION if tranches is None else tranches
    pas = (abscisse_fin - abscisse_debut) / tranches
    rayons = [rayon_a_l_abscisse(abscisse_debut + k * pas,
                                 rayon_sortie_m, rayon_entree_m)
              for k in range(tranches + 1)]
    cisaillements = [((3.0 * n + 1.0) / n) * debit_m3_par_s
                     / (math.pi * R ** 3) for R in rayons]
    tau_paroi = [tau_y + K * g ** n for g in cisaillements]
    # dP/dz = 2 tau_w / R. Le facteur 2 se simplifie partout, on le garde pour
    # que la grandeur reste lisible.
    gradient = [2.0 * t / R for t, R in zip(tau_paroi, rayons)]
    return pas, rayons, tau_paroi, gradient


def _integre(valeurs, pas):
    """Integrale par la methode des trapezes, pas constant."""
    return pas * (sum(valeurs) - 0.5 * (valeurs[0] + valeurs[-1]))


def _integrale_gradient(K, n, tau_y, debit_m3_par_s, rayon_sortie_m,
                        rayon_entree_m, abscisse_debut, abscisse_fin,
                        tranches=None):
    """Integrale de dP/dz sur un intervalle d'abscisse reduite."""
    pas, _, _, gradient = profil_le_long_de_la_buse(
        K, n, tau_y, debit_m3_par_s, rayon_sortie_m, rayon_entree_m,
        abscisse_debut, abscisse_fin, tranches)
    return _integre(gradient, pas)


def part_du_seuil_ponderee(K, n, tau_y, debit_m3_par_s, rayon_sortie_m,
                           rayon_entree_m, tranches=None):
    """Part du seuil moyennee le long de la buse, ponderee par dP/dz.

        f_ponderee = integrale( (tau_y/tau_w) dP/dz dz )
                     / integrale( dP/dz dz )

    Comme dP/dz = 2 tau_w/R, le numerateur se reduit a integrale(2 tau_y/R).
    C'est EXACTEMENT l'ecart relatif sur Delta_P entre un traitement a seuil et
    un traitement en loi de puissance pure.

    L'integration est numerique, par trapezes, sur un maillage uniforme en
    abscisse. La portion cote sortie est integree sur son PROPRE maillage
    uniforme, et non par selection de tranches dans le maillage global : ainsi
    sa borne est atteinte exactement et la convergence reste quadratique.

    Returns:
        (f_ponderee, fraction_delta_P_cote_sortie), la seconde valeur etant la
        part de Delta_P accumulee dans la portion FRACTION_LONGUEUR_COTE_SORTIE
        de la longueur, cote sortie.
    """
    pas, rayons, _, gradient = profil_le_long_de_la_buse(
        K, n, tau_y, debit_m3_par_s, rayon_sortie_m, rayon_entree_m,
        tranches=tranches)

    total = _integre(gradient, pas)
    if not total:
        return float("nan"), float("nan")

    contribution_seuil = [2.0 * tau_y / R for R in rayons]
    f_ponderee = _integre(contribution_seuil, pas) / total

    cote_sortie = _integrale_gradient(
        K, n, tau_y, debit_m3_par_s, rayon_sortie_m, rayon_entree_m,
        1.0 - FRACTION_LONGUEUR_COTE_SORTIE, 1.0, tranches)
    return f_ponderee, cote_sortie / total


def verdict(part_du_seuil, negligeable, gouvernant):
    """Qualifie la part du seuil. Voir les bornes en tete de module."""
    if part_du_seuil >= gouvernant:
        return "SEUIL GOUVERNANT"
    if part_du_seuil >= negligeable:
        return "seuil marginal"
    return "seuil negligeable"


def diagnostic(K, n, tau_y, De_mm, L_mm, vitesses_mm_par_s, Do_mm=None,
               negligeable=SEUIL_NEGLIGEABLE_PAR_DEFAUT,
               gouvernant=SEUIL_GOUVERNANT_PAR_DEFAUT):
    """Calcule le diagnostic pour chaque vitesse.

    Args:
        K (float): indice de consistance. [Pa.s^n]
        n (float): indice d'ecoulement. [-]
        tau_y (float): seuil d'ecoulement. [Pa]
        De_mm (float): diametre de sortie. [mm]
        L_mm (float): longueur de buse. [mm]
        vitesses_mm_par_s (list): vitesses en sortie de buse. [mm/s]
        Do_mm (float): diametre d'entree, si la buse est conique. [mm]
        negligeable, gouvernant (float): bornes du verdict. [-]

    Returns:
        list de dict, une entree par vitesse.
    """
    De = De_mm * MILLIMETRE
    Do = Do_mm * MILLIMETRE if Do_mm else None

    lignes = []
    for v_mm in vitesses_mm_par_s:
        Q = debit_volumique(De, v_mm * MILLIMETRE)

        gamma_app = cisaillement_apparent(Q, De)
        gamma_cor = cisaillement_corrige(Q, De, n)
        tau_paroi, tau_visqueux = contrainte_parietale(K, n, tau_y, gamma_cor)

        part = tau_y / tau_paroi if tau_paroi else float("nan")
        # Deux conventions, toutes deux rapportees :
        #   Bi_paroi   = tau_y / tau_paroi, la definition demandee ;
        #   Bi_visqueux = tau_y / tau_visqueux, la plus repandue, rapport du
        #                 seuil au terme visqueux seul.
        bi_visqueux = tau_y / tau_visqueux if tau_visqueux else float("inf")

        # En buse conique, le cisaillement parietal est MINIMAL a l'entree, ou
        # le rayon est le plus grand, donc la part du seuil y est MAXIMALE.
        # Cette valeur encadre la ponderee, elle ne la remplace pas : la chute
        # de pression se concentre cote sortie.
        diametre_entree = Do if Do is not None else De
        gamma_entree = cisaillement_corrige(Q, diametre_entree, n)
        tau_entree, _ = contrainte_parietale(K, n, tau_y, gamma_entree)
        part_entree = tau_y / tau_entree if tau_entree else float("nan")

        ponderee, fraction_cote_sortie = part_du_seuil_ponderee(
            K, n, tau_y, Q, De / 2.0, diametre_entree / 2.0)

        lignes.append(dict(
            v_mm_par_s=v_mm,
            gamma_apparent=gamma_app,
            gamma_corrige=gamma_cor,
            tau_visqueux=tau_visqueux,
            tau_paroi=tau_paroi,
            bi_paroi=part,
            bi_visqueux=bi_visqueux,
            part_du_seuil=part,
            gamma_corrige_entree=gamma_entree,
            tau_paroi_entree=tau_entree,
            part_du_seuil_entree=part_entree,
            part_du_seuil_maximale=max(part, part_entree),
            part_du_seuil_ponderee=ponderee,
            fraction_delta_P_cote_sortie=fraction_cote_sortie,
            verdict=verdict(ponderee, negligeable, gouvernant),
        ))
    return lignes


def affiche(lignes, K, n, tau_y, De_mm, L_mm, Do_mm, negligeable, gouvernant,
            etiquette):
    """Imprime le tableau de diagnostic et la conclusion."""
    conique = Do_mm is not None

    print("=" * 84)
    print(f"Diagnostic du seuil d'ecoulement : {etiquette}")
    print("=" * 84)
    print(f"  K     = {K!r} Pa.s^n")
    print(f"  n     = {n!r}")
    print(f"  tau_y = {tau_y!r} Pa")
    print(f"  buse  : De = {De_mm} mm, L = {L_mm} mm"
          + (f", Do = {Do_mm} mm (conique)" if conique else " (cylindrique)"))
    print(f"  correction de Rabinowitsch (3n+1)/(4n) = "
          f"{correction_rabinowitsch(n):.6f}")
    print(f"  bornes : negligeable sous {negligeable:.3%}, "
          f"gouvernant au-dela de {gouvernant:.3%}")
    print(f"  integration : {TRANCHES_INTEGRATION} tranches le long de l'axe")

    print("\n  ETAT A LA SORTIE DE BUSE, section la plus cisaillee\n")
    entetes = ["v (mm/s)", "gamma_app", "gamma_corr", "tau_visq", "tau_paroi",
               "Bi = ty/tw", "ty/tvisq"]
    largeurs = [9, 12, 12, 12, 12, 11, 11]
    print("  " + "  ".join(e.rjust(l) for e, l in zip(entetes, largeurs)))
    print("  " + "  ".join("-" * l for l in largeurs))
    for ligne in lignes:
        print("  " + "  ".join([
            f"{ligne['v_mm_par_s']:9.1f}",
            f"{ligne['gamma_apparent']:12.4g}",
            f"{ligne['gamma_corrige']:12.4g}",
            f"{ligne['tau_visqueux']:12.4g}",
            f"{ligne['tau_paroi']:12.4g}",
            f"{ligne['bi_paroi']:11.3e}",
            f"{ligne['bi_visqueux']:11.3e}",
        ]))

    print("\n  PART DU SEUIL. C'est la PONDEREE qui decide, les deux autres"
          " l'encadrent.\n")
    entetes = ["v (mm/s)", "en sortie", "en entree", "maximum", "PONDEREE",
               "dP au tiers sortie", "verdict"]
    largeurs = [9, 11, 11, 11, 12, 19, 18]
    print("  " + "  ".join(e.rjust(l) for e, l in zip(entetes, largeurs)))
    print("  " + "  ".join("-" * l for l in largeurs))
    for ligne in lignes:
        print("  " + "  ".join([
            f"{ligne['v_mm_par_s']:9.1f}",
            f"{ligne['part_du_seuil']:10.4%} ",
            f"{ligne['part_du_seuil_entree']:10.4%} ",
            f"{ligne['part_du_seuil_maximale']:10.4%} ",
            f"{ligne['part_du_seuil_ponderee']:11.4%} ",
            f"{ligne['fraction_delta_P_cote_sortie']:18.2%} ",
            f"{ligne['verdict']:>18}",
        ]))

    if not conique:
        print("\n  Buse cylindrique : la section est constante, donc la"
              " ponderee, la sortie")
        print("  et le maximum coincident. C'est le controle de coherence du"
              " script.")

    ponderees = [l["part_du_seuil_ponderee"] for l in lignes]
    ponderee_max = max(ponderees)
    conclusion = verdict(ponderee_max, negligeable, gouvernant)

    print("\n" + "=" * 84)
    print(f"  Part du seuil PONDEREE, maximum sur la plage de vitesses : "
          f"{ponderee_max:.4%}")
    print(f"  Pour memoire, en sortie "
          f"{max(l['part_du_seuil'] for l in lignes):.4%}, en entree "
          f"{max(l['part_du_seuil_entree'] for l in lignes):.4%}")
    print(f"  VERDICT : {conclusion}")
    print("=" * 84)
    if conclusion == "seuil negligeable":
        print("  Traiter le materiau en LOI DE PUISSANCE PURE suffit. Negliger")
        print("  le seuil deplace la pression predite de moins de "
              f"{ponderee_max:.4%}.")
        print("  La phase 7 se reduit alors a l'extension conique, le")
        print("  defaut #7 restant sans effet mesurable sur ce materiau.")
    elif conclusion == "seuil marginal":
        print("  Le seuil doit figurer dans le modele, mais l'erreur du")
        print("  traitement actuel reste du meme ordre que l'incertitude sur")
        print("  les parametres. La phase 7 est justifiee, sans urgence sur la")
        print("  solution exacte de l'ecoulement Herschel-Bulkley.")
    else:
        print("  La phase 7 est necessaire dans son integralite. La correction")
        print("  de Rabinowitsch d'une loi de puissance n'est pas defendable a")
        print("  ce niveau : il faut la solution exacte de l'ecoulement")
        print("  Herschel-Bulkley en conduite, et ses equations de reference.")
    print()
    print("  Rappel : la part ponderee est l'ecart EXACT entre un traitement a")
    print("  seuil et un traitement en loi de puissance pure. L'erreur due au")
    print("  bouchon central, elle, n'est PAS calculee ici et est SUPPOSEE du")
    print("  meme ordre. Voir la docstring de ce module.")
    return conclusion


def parametres_du_materiau(nom):
    """Lit K, n et tau_y dans materiaux.xlsx."""
    from tools.lireMateriaux import lireMateriau       # noqa: PLC0415
    materiau = lireMateriau(nom)
    return materiau["K"], materiau["n"], materiau["tau_0"]


def main(argv=None):
    analyseur = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--materiau",
                           help="nom d'un materiau de materiaux.xlsx, dont K, "
                                "n et tau_0 sont lus")
    analyseur.add_argument("--K", type=float, help="indice de consistance [Pa.s^n]")
    analyseur.add_argument("--n", type=float, help="indice d'ecoulement [-]")
    analyseur.add_argument("--tau-y", type=float, dest="tau_y",
                           help="seuil d'ecoulement [Pa]")
    analyseur.add_argument("--De", type=float, default=0.45,
                           help="diametre de sortie [mm], defaut 0.45")
    analyseur.add_argument("--Do", type=float, default=None,
                           help="diametre d'entree [mm]. Absent : buse "
                                "cylindrique")
    analyseur.add_argument("--L", type=float, default=17.25,
                           help="longueur de buse [mm], defaut 17.25")
    analyseur.add_argument("--vitesses", type=float, nargs="+",
                           default=VITESSES_PAR_DEFAUT,
                           help="vitesses en sortie de buse [mm/s]")
    analyseur.add_argument("--negligeable", type=float,
                           default=SEUIL_NEGLIGEABLE_PAR_DEFAUT,
                           help="borne basse du verdict, defaut 0.01")
    analyseur.add_argument("--gouvernant", type=float,
                           default=SEUIL_GOUVERNANT_PAR_DEFAUT,
                           help="borne haute du verdict, defaut 0.10")
    args = analyseur.parse_args(argv)

    etiquette = args.materiau or "parametres fournis en ligne de commande"
    K, n, tau_y = args.K, args.n, args.tau_y
    if args.materiau:
        K_base, n_base, tau_base = parametres_du_materiau(args.materiau)
        # Les valeurs explicites de la ligne de commande priment, ce qui
        # permet d'essayer un seuil sur un materiau dont la base n'en porte
        # pas encore.
        K = K if K is not None else K_base
        n = n if n is not None else n_base
        tau_y = tau_y if tau_y is not None else tau_base

    manquants = [nom for nom, valeur in (("K", K), ("n", n), ("tau_y", tau_y))
                 if valeur is None]
    if manquants:
        analyseur.error(
            f"parametres manquants : {', '.join(manquants)}. Fournir --K, "
            "--n et --tau-y, ou --materiau.")
    if n <= 0:
        analyseur.error(f"n doit etre strictement positif, recu {n!r}.")
    if tau_y < 0:
        analyseur.error(f"tau_y ne peut pas etre negatif, recu {tau_y!r}.")
    if K <= 0:
        analyseur.error(
            f"K doit etre strictement positif, recu {K!r}. Un materiau de "
            "Carreau, dont K vaut zero, n'a pas de contrainte parietale en "
            "loi de puissance et ne releve pas de ce diagnostic.")

    lignes = diagnostic(K, n, tau_y, args.De, args.L, args.vitesses, args.Do,
                        args.negligeable, args.gouvernant)
    affiche(lignes, K, n, tau_y, args.De, args.L, args.Do,
            args.negligeable, args.gouvernant, etiquette)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
