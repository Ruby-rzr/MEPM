import numpy as np


def calculateSR(Q, D, v, n, Noz_type):
    """
    calculateSR is the function used to obtain the shear rate inside multiple nozzles.

    Inputs:
        Q (array-like): Flow rate array
        D (array-like): Nozzle diameter array
        v (numeric): Desired speed for all nozzles

    Outputs:
        SR (array-like): Shear rate array
        dSR (array-like): Change in shear rate array

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
    if isinstance(Q, np.ndarray) and isinstance(D, np.ndarray):
        # if D.shape[0] != 2:
        #     raise ValueError("Input D must be a matrix with 2 rows.")

        # Extract the columns of D
        D0 = D[0, :]
        D1 = D[1, :]

        # Ensure Q and D0 are compatible in length
        if len(Q) != len(D0):
            raise ValueError(
                "Input Q must have the same length as the number of rows in D.")
        if Noz_type == "tapered":

            # Forme algébriquement identique à l'équation 4.2 :
            # ((3n+1)/n) * 8Q/(pi D^3) == ((3 + 1/n)/4) * 32Q/(pi D^3)
            SR = ((3*n+1)/n)*((8*Q)/(np.pi*D0**3))

            dSR = 8 * v * D1 / D0 ** 2

        else:
            # Calculate shear rate
            SR = 32 * Q / (np.pi * D0 ** 3)

            # Calculate change in shear rate
            dSR = 8 * v * D1 / D0 ** 2

            # Weissenberg-Rabinowitsch correction (Chauvette 2023, éq. 4.2)
            rabi = (3 + (1 / n)) / 4
            SR = SR * rabi

        return SR, dSR
    else:
        raise ValueError("Inputs Q and D must be NumPy arrays.")
