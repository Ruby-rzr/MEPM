import numpy as np

from tools.unites import MILLIMETRE_CUBE

# ---------------------------------------------------------------------------
# Facteur d'unites de l'ajustement empirique.
#
# La branche empirique calcule P = R * Q^mP * FACTEUR, ou R et mP sont deux
# parametres lus dans materials.xls et ajustes sur des mesures. Ce facteur
# n'est derive d'AUCUNE equation physique : il est impose par la convention
# d'unites dans laquelle l'ajustement a ete realise, et il est solidaire des
# valeurs de R et de mP. Le modifier sans reajuster R et mP fausse la sortie.
#
# HYPOTHESE NON CONFIRMEE : la lecture la plus plausible est que R et mP ont
# ete ajustes sur des pressions exprimees en MPa, avec Q en mm^3/s, ce facteur
# convertissant alors les MPa en Pa. C'est la seule lecture qui donne le bon
# ordre de grandeur, environ 2 a 4 MPa sur la plage de vitesses de la these,
# la meme que celle de la branche conique analytique. Elle n'est PAS
# demontree : le script d'ajustement qui a produit R et mP est absent du
# depot, et l'auteur du portage n'a pas encore ete interroge. Tant que ce
# point n'est pas tranche, ce commentaire est la seule trace autorisee de
# l'hypothese, et le nom du facteur ne doit pas la prejuger.
#
# Unite : Pa par unite de (R * Q^mP), indeterminee.
FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE = 10**6


def calculatePrequired(R_eq, Q_eq, P_amb, n, mP, Noz_type, R):
    """
    calculatePrequired is the function used to obtain the required pressure to extrude material through the equivalent flow resistance network
    characterized by the nozzles in parallel.

    Unites : SI strict en entree et en sortie. La branche empirique fait
    exception et porte son propre contrat d'unites, decrit ci-dessous.

    CONTRAT D'UNITES DE L'AJUSTEMENT EMPIRIQUE
        Il s'applique des qu'un parametre ajuste intervient, R ou mP.
        Entree  : Q converti en mm^3/s, R_eq exprime dans la convention de
                  l'ajustement.
        Sortie  : P en Pa.
        La conversion a lieu ici, a la frontiere, et nulle part ailleurs.
        Le chemin purement analytique, R et mP tous deux nuls, reste en SI.

        Quand mP est non nul, P_amb n'est PAS ajoute, contrairement aux deux
        autres branches. Ce n'est pas un oubli de la refonte, c'est le
        comportement d'origine, conserve tel quel.

    Inputs:
        R_eq (numeric or array-like): Equivalent flow resistance. Unite
            dependante de la branche, voir calculateReq :
            Pa.s/m^3 en cylindrique, Pa/(m^3/s)^n en conique analytique,
            indeterminee en conique empirique.
        Q_eq (numeric or array-like): Equivalent total flow rate. [m^3/s]
        P_amb (numeric): Ambient pressure. [Pa]
        n (numeric): Flow behaviour index. [-]
        mP (numeric): Exposant ajuste empiriquement, base de materiaux. [-]
        Noz_type (str): "tapered", ou toute autre valeur pour cylindrique.
        R (numeric): Resistance ajustee empiriquement, base de materiaux.
            Sert ici uniquement a savoir dans quelle convention d'unites
            R_eq est exprime, voir le commentaire de la branche empirique.

    Output:
        P (numeric): Required pressure. [Pa]

    Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
        %Date: June 13, 2020 - February 13, 2024

    """
    if isinstance(P_amb, (int, float)):  # and isinstance(R_eq, (int, float)) and isinstance(Q_eq, (int, float)) :
        if Noz_type == "tapered":

            # Frontiere d'unites. Des qu'un parametre ajuste intervient, que
            # ce soit R ou mP, l'expression entiere doit etre evaluee dans la
            # convention d'unites de l'ajustement, Q en mm^3/s. Le chemin
            # purement analytique, R et mP tous deux nuls, reste en SI.
            convention_ajustement = (mP != 0) or (R != 0)

            if convention_ajustement:
                Q_contrat = np.mean(Q_eq) / MILLIMETRE_CUBE
                if R != 0:
                    # R_eq EST le parametre ajuste, deja dans la convention
                    # de l'ajustement, aucune conversion.
                    R_contrat = np.mean(R_eq)
                else:
                    # R_eq est la resistance conique analytique, en
                    # Pa/(m^3/s)^n, ramenee en Pa/(mm^3/s)^n.
                    R_contrat = np.mean(R_eq) * MILLIMETRE_CUBE ** n
            else:
                Q_contrat = np.mean(Q_eq)
                R_contrat = np.mean(R_eq)

            if mP != 0:
                print(f'R_eq moyen (Pa) = {R_contrat}')
                print(f'Q_eq moyen (Pa) = {Q_contrat}')
                P = (R_contrat * Q_contrat ** mP) \
                    * FACTEUR_UNITES_AJUSTEMENT_EMPIRIQUE  # + P_amb
                print(f'Required pressure (Pa) = {P}')
            else:
                # Weissenberg-Rabinowitsch correction
                rabi = (3 + (1 / n)) / 4
                P = R_contrat * Q_contrat ** n + P_amb
                print(f'Required pressure (Pa) = {P}')
        else:
            P = R_eq * Q_eq + P_amb
        return P
    else:
        raise ValueError("Inputs R_eq, Q_eq, and P_amb must be numeric.")
