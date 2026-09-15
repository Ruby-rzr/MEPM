import numpy as np


def calculateReq(eta, theta, K, n, L, D, Noz_type, R):
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
    eta = np.array(eta)
    L = np.array(L)
    D = np.array(D)

    if isinstance(eta, np.ndarray) and isinstance(L, np.ndarray) and isinstance(D, np.ndarray):
        if len(eta) != D.shape[1]:
            raise ValueError(" Inputs eta, L and D must have the same length.")
        # if D.shape[0] != 2:
        #     raise ValueError(" Input D must be a matrix with 2 columns.")
        if Noz_type == "tapered":
            # Extract diameters from the first column of D
            if R != 0:
                Ri = R*np.ones(len(eta))
                R_eq = Ri
            else:

                De = D[0, :]  # outlet diamter
                Do = D[2, :]  # inlet diameter

                # Ri = (2*K*(De**(3*n)-Do**(3*n))/(3*n*np.tan(theta)
                #                                  )) * (((32)/(np.pi * Do**3 * De**3))**n)
                #
                # DEFAUT #8, corrige en phase 5. L'ecriture precedente etait
                #     ((3*n+1)/(n*np.pi)
                #                       ** n)
                # ou la coupure de ligne masquait que l'exposant n se liait au
                # seul denominateur (n*pi) et non a la fraction entiere. Le
                # code calculait (3n+1)/(n pi)^n au lieu de ((3n+1)/(n pi))^n,
                # soit un facteur parasite (3n+1)^(1-n), valant 1.59 pour
                # n = 0.49 et 1 pour n = 1. Les parentheses sont desormais
                # explicites et le terme tient sur une seule ligne.
                terme_debit = ((3*n + 1) / (n*np.pi)) ** n
                Ri = ((4*K*L[0]) / (3*n*(Do - De))) * terme_debit \
                    * ((De/2)**(-3*n) - (Do/2)**(-3*n))

                # Calculate equivalent hydraulic resistance for nozzles in parallel

                R_eq = Ri
            # R_eq = 1/np.sum(1/Ri)
        else:

            # Extract diameters from the first column of D
            diameters = D[0, :]

            # Calculate individual hydraulic resistance for each nozzle
            Ri = (128*L[0]*eta)/(np.pi*diameters**4)

            # Calculate equivalent hydraulic resistance for nozzles in parallel
            R_eq = 1/np.sum(1/Ri)
            # Weissenberg-Rabinowitsch correction (Chauvette 2023, éq. 4.4)
            rabi = (3 + (1 / n)) / 4
            R_eq = R_eq * rabi
            Ri = Ri * rabi

        return R_eq, Ri
