import numpy as np

# ---------------------------------------------------------------------------
# Seuils de regime d'ecoulement.
#
# Regle 5 de CLAUDE.md : aucune valeur numerique en dur dans le code de calcul.
# Ces deux seuils etaient ecrits en dur dans les comparaisons ci-dessous. Ils
# sont nommes ici, LEURS VALEURS SONT INCHANGEES.
#
# Ils ne sont derives d'aucune equation. Le seuil haut de 2500 est proche de la
# valeur usuelle de transition en conduite lisse, de l'ordre de 2100 a 2300. Le
# seuil bas de 100, qui declenche le rejet du calcul, est tres conservateur et
# sa provenance n'est pas etablie dans ce depot. Aucun ecoulement de ce modele
# n'en approche : les nombres de Reynolds rencontres valent 1e-4 ou moins.
REYNOLDS_LAMINAIRE_MAXIMAL = 100      # [-]
REYNOLDS_TURBULENT_MINIMAL = 2500     # [-]


def validateReynolds(rho, v, D, eta, debug_mode=False):
    """
    validateReynolds is the function used to validate whether a laminar flow is occurring in the nozzles of the robot. Upon validation, the Hagen-
    Poiseuille viscosity formulation may be used. If any of the flow rates are in the transition zone or turbulent, the function returns the position of
    nozzles having non-laminar flow.

    The output is the flow type: 0=laminar, 1=transition zone, 2=turbulent.
    pos is the position array of nozzles having non-laminar flow.
    Function valid only for the Extended Herschell-Bulkley, Herschell-Bulkley, Sisko, Ostwald-de-Waele, Bingham, and Newtonian models.

    Unites : SI strict. La division par 1e6 presente dans les versions
    anterieures a disparu : elle convertissait v et D de mm vers m, ce qui est
    desormais fait a la frontiere par tools.unites.entrees_vers_si. Ce
    n'etait PAS un rustinage mais une conversion correcte, voir
    tests/test_reynolds.py.

    Parameters:
    rho (numeric): Density of the fluid. [kg/m^3]
    v (numeric): Velocity of the fluid. [m/s]
    D (array-like): Diameter of the nozzles, tableau (3, alpha). [m]
    eta (array-like): Viscosity of the fluid. [Pa.s]
    debug_mode (bool, optional): Debug mode flag. Default is False.

    Returns:
    typeEcoul (int): Type of flow - 0 for laminar, 1 for transition zone, 2 for turbulent.
    Re (numpy.ndarray): Reynolds number array, forme (3, alpha). [-]
        DEFAUT #13 : Re est calcule sur les TROIS lignes de D, donc aussi sur
        l'erreur de mesure et sur le diametre d'entree, et le critere de
        laminarite porte sur les trois. Comportement conserve tel quel.
    
    Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
        %Date: June 13, 2020 - February 13, 2024
    """

    if np.isscalar(rho): #and np.isscalar(eta):
        if np.any(rho == 0):
            # DEFAUT #19, corrige en phase 5. typeEcoul valait ici un TABLEAU
            # de NaN, et generateP le testait par 'if typeEcoul == 0', ce qui
            # levait une ValueError sur l'ambiguite d'un tableau. Tout
            # materiau dont la masse volumique vaut zero dans la base faisait
            # donc planter le modele, alors que le message ci-dessous annonce
            # que la validation est simplement ignoree.
            #
            # typeEcoul vaut desormais le scalaire 0, c'est a dire laminaire,
            # ce qui laisse le calcul se poursuivre comme le message l'annonce.
            # L'HYPOTHESE DE LAMINARITE N'EST ALORS PAS VERIFIEE, d'ou le
            # message, qui est le seul avertissement disponible a ce stade.
            print('Reynolds validation is skipped since rho = 0. Update material database to activate Reynolds validation.')
            typeEcoul = 0
            Re = np.full(D.shape, np.nan)
        else:
            # Sans division : avec rho en kg/m^3, v en m/s, D en m et eta en
            # Pa.s, le quotient est directement adimensionnel.
            Re = rho * v * D / eta

            if np.all(Re > 0) and np.all(Re < REYNOLDS_LAMINAIRE_MAXIMAL):  # Laminar
                typeEcoul = 0
                if debug_mode:
                    print('All flow rates are laminar')
            elif np.any((Re >= REYNOLDS_LAMINAIRE_MAXIMAL)
                        & (Re <= REYNOLDS_TURBULENT_MINIMAL)):  # Transition
                typeEcoul = 1
                pos = np.where((Re >= REYNOLDS_LAMINAIRE_MAXIMAL)
                               & (Re <= REYNOLDS_TURBULENT_MINIMAL))[0]
                print('The flow is in the transition zone for nozzles #', pos)
            elif np.any(Re > REYNOLDS_TURBULENT_MINIMAL):  # Turbulent
                typeEcoul = 2
                pos = np.where(Re > REYNOLDS_TURBULENT_MINIMAL)[0]
                print('The flow is turbulent for nozzles #', pos)
            else:  # Negative Re number
                typeEcoul = np.nan
                print('Reynolds is negative')
    else:
        raise ValueError("Inputs 'rho', 'v', 'D', and 'eta' must be scalar values.")

    return typeEcoul, Re
