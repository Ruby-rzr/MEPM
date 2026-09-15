import numpy as np

from Velocity_driven.modeles import ANALYTIQUE, EMPIRIQUE, valide_mode


def calculateReq(eta, theta, K, n, L, D, Noz_type, R, mode):
    """
    calculateReq is the function used to obtain the equivalent hydraulic
    resistance of several nozzles in parallel.

    Unites : SI strict.

    ATTENTION, R_eq N'A PAS LA MEME DIMENSION SELON LA BRANCHE (defaut #2) :
      - cylindrique       : Pa.s/m^3, multiplie Q pour donner des Pa ;
      - conique analytique: Pa/(m^3/s)^n, multiplie Q^n pour donner des Pa ;
      - conique empirique : unite indeterminee, R est un parametre ajuste.

    Inputs:
        eta (array-like): Apparent viscosity array. [Pa.s]
        theta (numeric): Half-cone angle. [rad] Non utilise par cette branche,
            la geometrie conique etant decrite par L, De et Do.
        K (numeric): Flow consistency index. [Pa.s^n]
        n (numeric): Flow behaviour index. [-]
        L (array-like): Nozzle length and its error. [m]
        D (array-like): Nozzle diameter array (3, alpha). [m]
        Noz_type (str): "tapered", ou toute autre valeur pour cylindrique.
        R (numeric): Resistance ajustee empiriquement, base de materiaux.
            Unite indeterminee, voir calculatePrequired.
        mode (str): ANALYTIQUE ou EMPIRIQUE, voir Velocity_driven.modeles.
            Le choix etait auparavant devine par 'if R != 0'.

    Outputs:
        R_eq (numeric or array-like): Equivalent hydraulic resistance.
            Unite dependante de la branche, voir ci-dessus.
        Ri (array-like): Individual hydraulic resistance for each nozzle.

    Référence:
        J.-F. Chauvette, thèse de doctorat, Polytechnique Montréal (2023),
        section 4.3.1.1, équation 4.4, elle-même référencée [38] :

            R_i = (128 L eta_i / (pi D_avg^4)) * ((3 + 1/n)/4)

        Le facteur (3 + 1/n)/4 apparaît ici ET sur le taux de cisaillement
        dans calculateSR (équation 4.2). Ce n'est PAS un doublon : la
        composition des deux redonne la solution analytique d'une loi de
        puissance en conduite cylindrique,

            Delta_P = 4 L K gamma_point_paroi^n / D

        Ne jamais retirer l'un des deux facteurs. Voir CLAUDE.md.

        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    valide_mode(mode)
    eta = np.array(eta)
    L = np.array(L)
    D = np.array(D)

    if len(eta) != D.shape[1]:
        raise ValueError(" Inputs eta, L and D must have the same length.")

    if Noz_type == "tapered":
        if mode == EMPIRIQUE:
            R_eq, Ri = _resistance_conique_empirique(R, len(eta))
        else:
            R_eq, Ri = _resistance_conique_analytique(K, n, L, D)
    else:
        R_eq, Ri = _resistance_cylindrique(eta, n, L, D)

    return R_eq, Ri


def _resistance_conique_empirique(R, alpha):
    """Resistance conique en mode empirique : le parametre ajuste, tel quel.

    Le choix etait auparavant devine par 'if R != 0'.

    Args:
        R (numeric): resistance ajustee, base de materiaux. Unite indeterminee.
        alpha (int): nombre de buses.

    Returns:
        (R_eq, Ri), l'un et l'autre valant R sur chaque buse. La geometrie et
        la rheologie n'interviennent pas : c'est tout l'objet du defaut #1.
    """
    Ri = R*np.ones(alpha)
    R_eq = Ri
    return R_eq, Ri


def _resistance_conique_analytique(K, n, L, D):
    """Resistance conique analytique, loi de puissance en lubrification.

    En posant tan(theta) = (Do - De) / (2 L), l'integration le long de l'axe
    donne

        Delta_P = (2K / (3 n tan(theta))) ((3n+1) Q / (n pi))^n
                  (Re^-3n - Ro^-3n)

    et cette fonction rend le facteur qui multiplie Q^n.

    DEFAUT #8, corrige en phase 5. L'ecriture precedente etait

        ((3*n+1)/(n*np.pi)
                          ** n)

    ou la coupure de ligne masquait que l'exposant n se liait au seul
    denominateur (n*pi) et non a la fraction entiere. Le code calculait
    (3n+1)/(n pi)^n au lieu de ((3n+1)/(n pi))^n, soit un facteur parasite
    (3n+1)^(1-n), valant 1.59 pour n = 0.49 et 1 pour n = 1. Les parentheses
    sont desormais explicites et le terme tient sur une seule ligne.

    eta n'intervient pas : c'est le defaut #11, traite en phase 7.

    Args:
        K (numeric): indice de consistance. [Pa.s^n]
        n (numeric): indice d'ecoulement. [-]
        L (array-like): longueur de buse et son erreur. [m]
        D (array-like): tableau (3, alpha) des diametres. [m]

    Returns:
        (R_eq, Ri) en Pa/(m^3/s)^n.
    """
    De = D[0, :]  # outlet diamter
    Do = D[2, :]  # inlet diameter

    terme_debit = ((3*n + 1) / (n*np.pi)) ** n
    Ri = ((4*K*L[0]) / (3*n*(Do - De))) * terme_debit \
        * ((De/2)**(-3*n) - (Do/2)**(-3*n))

    # Pas de mise en parallele ici, contrairement au cylindrique : c'est le
    # defaut #4, traite en phase 7 puis en phase 8.
    R_eq = Ri
    return R_eq, Ri


def _resistance_cylindrique(eta, n, L, D):
    """Resistance cylindrique, Hagen-Poiseuille corrige de Rabinowitsch.

    Chauvette 2023, section 4.3.1.1, equation 4.4, referencee [38] :

        R_i = (128 L eta_i / (pi D_avg^4)) * ((3 + 1/n)/4)

    NE PAS RETIRER LE FACTEUR rabi. Voir le piege en tete de CLAUDE.md : il est
    applique une seconde fois sur le taux de cisaillement dans calculateSR,
    equation 4.2, et la composition des deux redonne exactement

        Delta_P = 4 L K gamma_point_paroi^n / D

    Le garde-fou est test_T2_loi_de_puissance_cylindre.

    Args:
        eta (array-like): viscosite apparente par buse. [Pa.s]
        n (numeric): indice d'ecoulement. [-]
        L (array-like): longueur de buse et son erreur. [m]
        D (array-like): tableau (3, alpha) des diametres. [m]

    Returns:
        (R_eq, Ri) en Pa.s/m^3.
    """
    # Extract diameters from the first column of D
    diametres_sortie = D[0, :]

    # Calculate individual hydraulic resistance for each nozzle
    Ri = (128*L[0]*eta)/(np.pi*diametres_sortie**4)

    # Calculate equivalent hydraulic resistance for nozzles in parallel
    R_eq = 1/np.sum(1/Ri)
    # Weissenberg-Rabinowitsch correction (Chauvette 2023, éq. 4.4)
    rabi = (3 + (1 / n)) / 4
    R_eq = R_eq * rabi
    Ri = Ri * rabi
    return R_eq, Ri
