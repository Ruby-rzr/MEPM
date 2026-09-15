import numpy as np


def calculateSR(Q, D, v, n, Noz_type):
    """
    calculateSR is the function used to obtain the shear rate inside multiple nozzles.

    Unites : SI strict. Le taux de cisaillement est en 1/s, donc invariant
    par changement d'unite de longueur, mais Q et D doivent etre coherents.

    Inputs:
        Q (array-like): Flow rate array. [m^3/s]
        D (array-like): Nozzle diameter array (3, alpha). [m]
        v (numeric): Desired speed for all nozzles. [m/s]
        n (numeric): Flow behaviour index. [-]
        Noz_type (str): "tapered", ou toute autre valeur pour cylindrique.

    Outputs:
        SR (array-like): Shear rate array. [1/s]
        dSR (array-like): Change in shear rate array. [1/s]

    Référence:
        J.-F. Chauvette, thèse de doctorat, Polytechnique Montréal (2023),
        section 4.3.1.1, équation 4.2, elle-même référencée [38] :

            gamma_point_i = (32 Q_i / (pi D_avg^3)) * ((3 + 1/n)/4)

        Le facteur (3 + 1/n)/4 est la correction de Weissenberg-Rabinowitsch.
        Il apparaît une seconde fois, volontairement, sur la résistance
        hydraulique dans calculateReq (équation 4.4). Voir CLAUDE.md.

        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    if not (isinstance(Q, np.ndarray) and isinstance(D, np.ndarray)):
        raise ValueError("Inputs Q and D must be NumPy arrays.")

    diametre_sortie = D[0, :]
    erreur_diametre = D[1, :]

    if len(Q) != len(diametre_sortie):
        raise ValueError(
            "Input Q must have the same length as the number of rows in D.")

    # Incertitude sur le taux de cisaillement, propagee depuis l'erreur de
    # mesure du diametre. Identique dans les deux geometries.
    dSR = 8 * v * erreur_diametre / diametre_sortie ** 2

    if Noz_type == "tapered":
        # Forme algébriquement identique à l'équation 4.2 :
        # ((3n+1)/n) * 8Q/(pi D^3) == ((3 + 1/n)/4) * 32Q/(pi D^3)
        SR = ((3*n+1)/n)*((8*Q)/(np.pi*diametre_sortie**3))
    else:
        # Calculate shear rate
        SR = 32 * Q / (np.pi * diametre_sortie ** 3)

        # Weissenberg-Rabinowitsch correction (Chauvette 2023, éq. 4.2)
        # NE PAS RETIRER. Voir le piège en tête de CLAUDE.md : ce facteur est
        # appliqué une seconde fois sur la résistance hydraulique dans
        # calculateReq, et la composition des deux redonne la solution
        # analytique. Le garde-fou est test_T2_loi_de_puissance_cylindre.
        rabi = (3 + (1 / n)) / 4
        SR = SR * rabi

    return SR, dSR
