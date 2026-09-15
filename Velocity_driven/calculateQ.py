import numpy as np


def calculateQ(D, v, Noz_type):
    """
    calculateQ is the function used to obtain the volumetric flow rate through several nozzles.

    Unites : SI strict. Conversion des mm de saisie assuree en amont par
    tools.unites.entrees_vers_si.

    Inputs:
        D (array-like): Nozzle diameter array (3, alpha) : sortie, erreur,
            entree. [m]
        v (numeric): Desired speed for all nozzles. [m/s]
        Noz_type (str): "tapered", ou toute autre valeur pour cylindrique.

    Outputs:
        Q (array-like): Flow rate array for each of the nozzles. [m^3/s]
        dQ (array-like): Change in flow rate for each of the nozzles. [m^3/s]
        Q_eq (numeric or array-like): Equivalent total flow rate. [m^3/s]
            Somme sur les buses en cylindrique, tableau par buse en conique.

        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    # Ensure inputs are valid
    if D.ndim != 2:
        raise ValueError("Input array D must be 2-dimensional")
    if not (isinstance(D, (list, np.ndarray))):
        raise ValueError("Inputs D and v must be numeric or array-like.")

    if isinstance(D, list):
        D = np.array(D)

    alpha = D.shape[1]

    # Initialize arrays for Q and dQ
    Q = np.empty(alpha)
    dQ = np.empty(alpha)

    # Le debit par buse et son incertitude ne dependent pas de la geometrie de
    # la buse : seul le diametre de SORTIE intervient. Les deux branches
    # d'origine calculaient exactement les memes lignes.
    for i in range(alpha):
        # Calculate cross-sectional area of the nozzle
        area = np.pi * 0.25 * D[0, i] ** 2
        Q[i] = area * v  # Calculate flow rate for each nozzle
        # Calculate change in flow rate for each nozzle
        dQ[i] = np.pi * 0.5 * D[0, i] * D[1, i] * v

    if Noz_type == 'tapered':
        # Debit PAR BUSE. calculatePrequired en prend ensuite la moyenne, ce
        # qui revient a la chute de pression d'une buse. Voir le defaut #4.
        Q_eq = Q
    else:
        Q_eq = np.sum(Q)  # Calculate the equivalent total flow rate

    return Q, dQ, Q_eq
