from Velocity_driven import calculateQ, calculatePrequired, calculateReq, calculateReqError, calculateSR, calculateVisco, validateReynolds
from tools import printTableInConsole
from tools.unites import MILLIMETRE, m3_par_s_vers_mm3_par_s, m_vers_mm
import os
import sys
import numpy as np

# Add the MEPM directory to the Python path
mepm_path = r"C:\Users\anirb\OneDrive\Desktop\Additive Nozzle Manufacturing\CODE FOR MEPM"
sys.path.append(mepm_path)


def generateP(rho, v, D, L, theta, n, K, eta_0, eta_inf, tau_0, lmbda, a, P_amb, Noz_type, R, mP, debug_mode, modele, mode, incertitudes):
    """
    generateP function's purpose is to regroup all the necessary function calls in order to calculate the required pressure for a given material 
    and nozzle exit velocity. It validates the Reynold numbers. Finally, it returns the required Pressure along with Viscosities and Shear rates 
    arrays for plots.

    Unites : SI strict en entree et en sortie. La conversion depuis les mm de
    saisie a lieu en amont, dans tools.unites.entrees_vers_si. Les seules
    conversions presentes ici sont des conversions D'AFFICHAGE, pour que les
    messages de la console restent lus en mm comme a l'atelier.

    Inputs:
        rho (numeric): Density. [kg/m^3]
        v (numeric): Nozzle exit velocity. [m/s]
        D (array-like): Nozzle diameter array (3, alpha) : sortie, erreur,
            entree. [m]
        L (array-like): Nozzle length and its error. [m]
        theta (numeric): Half-cone angle of the nozzle. [rad]
        n (numeric): Viscosity index. [-]
        K (numeric): Consistency index. [Pa.s^n]
        eta_0 (numeric): Rest-state viscosity. [Pa.s]
        eta_inf (numeric): Infinite viscosity. [Pa.s]
        tau_0 (numeric): Creep factor. [Pa]
        lmbda (numeric): Relaxation time. [s]
        a (numeric): Carreau model exponent. [-]
        P_amb (numeric): Ambient pressure. [Pa]
        Noz_type (str): "tapered", ou toute autre valeur pour cylindrique.
        R (numeric): Resistance ajustee empiriquement. Unite indeterminee.
        mP (numeric): Exposant ajuste empiriquement. [-]
        debug_mode (bool): Flag for printing debug information
        modele (str): loi rheologique explicite, voir Velocity_driven.modeles.
        mode (str): ANALYTIQUE ou EMPIRIQUE, voir Velocity_driven.modeles.
        incertitudes (dict): incertitudes sur les parametres du materiau,
            voir calculateVisco.

    Outputs:
        P (numeric): Required pressure. [Pa]
        eta (array-like): Viscosity array. [Pa.s]
        SR (array-like): Shear rate array. [1/s]
        Q (array-like): Flow rate array. [m^3/s]
        deta (array-like): Error in viscosity array. [Pa.s]
        dP (numeric): Error in required pressure. Unite NON homogene a des Pa,
            voir le defaut #20 dans calculateReqError.
        dRi (array-like): Error in individual hydraulic resistance array.
            Unite NON homogene a Ri, meme raison.
        dSR (array-like): Error in shear rate array. [1/s]

        Author: Jean-François Chauvette, Raphaël Plante
        Date: June 13, 2020 - February 13, 2024
    """

    print('------------------------------------------------------------------------------------------------')
    # Affichage : frontiere de sortie, on revient aux mm d'usage.
    print(f'Desired nozzle exit speed (mm/s) = {m_vers_mm(v):.2f}\n')

    # Flows computation
    Q, dQ, Q_eq = calculateQ.calculateQ(D, v, Noz_type)

    if debug_mode:
        print(f'Total equivalent Q (mm³/s) = '
              f'{np.mean(m3_par_s_vers_mm3_par_s(Q_eq)):.2f}')
        print('Volumetric flow rates (mm³/s):')
        printTableInConsole.printTableInConsole(m3_par_s_vers_mm3_par_s(Q))

    # Shear rate computation
    SR, dSR = calculateSR.calculateSR(Q, D, v, n, Noz_type)

    if debug_mode:
        print('Shear rates (1/s):')
        printTableInConsole.printTableInConsole(SR)

    # Viscosity computation
    eta, deta = calculateVisco.calculateVisco(
        SR, n, K, eta_inf, eta_0, tau_0, lmbda, a, modele, incertitudes,
        debug_mode, dSR)

    if debug_mode:
        print('Viscosities (Pa.s):')
        printTableInConsole.printTableInConsole(eta)

    # Reynolds number hypothesis validation
    typeEcoul, Re = validateReynolds.validateReynolds(
        rho, v, D, eta, debug_mode)

    if debug_mode:
        print('Reynold numbers:')
        printTableInConsole.printTableInConsole(Re)

    if typeEcoul == 0:  # Laminar flow

        # Equivalent flow resistance computation
        R_eq, Ri = calculateReq.calculateReq(
            eta, theta, K, n, L, D, Noz_type, R, mode)

        R_eq_error, dRi = calculateReqError.calculateReqError(
            R_eq, Ri, D.shape[1], D, L, eta, deta)

        if debug_mode:
            # print(f'Total equivalent R (Pa.s/mm³) = {R_eq:.2f}')
            print('Individual flow resistances (Pa.s/m³):')
            printTableInConsole.printTableInConsole(Ri)

        # Required pressure computation
        P = calculatePrequired.calculatePrequired(
            R_eq, Q_eq, P_amb, n, mP, Noz_type, R, mode)
        dP = np.sqrt((R_eq_error * Q_eq)**2 + (R_eq * np.sum(dQ))**2)
        print(f'Required pressure (Pa) = {P:.0f}')
    else:  # Transition flow, turbulent flow or negative Reynolds
        P = np.nan
        eta = np.nan
        SR = np.nan
        Q = np.nan
        deta = np.nan
        dP = np.nan
        dRi = np.nan
        dSR = np.nan

    return P, eta, SR, Q, deta, dP, dRi, dSR
