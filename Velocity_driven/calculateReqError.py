import numpy as np

def calculateReqError(R_eq, Ri, alpha, D, L, eta, deta):
    """
    calculateReqError is the function used to calculate the error in the equivalent hydraulic resistance.

    Unites : SI strict en entree.

    ATTENTION, DEFAUT #20 : cette formule n'est PAS homogene. Sous la racine
    elle additionne trois termes de dimensions differentes,

        T1 = (D^2/(eta L))^4 (L deta)^2   met a l'echelle en s^10
        T2 = (eta L1)^2                   met a l'echelle en s^2
        T3 = 16 (eta L D1/D0)^2           met a l'echelle en s^2

    ou s est le facteur d'echelle des longueurs. T1 vaut environ 3.9e-17
    contre 1012 pour T2 + T3 sur un cas courant, soit quatorze ordres de
    grandeur sous la resolution flottante de la somme : il ne contribue aucun
    bit, et l'inhomogeneite reste sans effet numerique observable. Elle a en
    revanche une consequence : dRi ne porte pas la dimension de Ri, mais
    celle de Ri^2 fois une longueur, et n'a donc pas de facteur de conversion
    partage avec Ri. Ce comportement est conserve tel quel, sa correction
    change des nombres.

    Inputs:
        R_eq (numeric): Equivalent hydraulic resistance. Unite dependante de
            la branche, voir calculateReq.
        Ri (array-like): Individual hydraulic resistance for each nozzle.
        alpha (int): Number of nozzles. [-]
        D (array-like): Nozzle diameter array (3, alpha). [m]
        L (array-like): Nozzle length and its error. [m]
        eta (array-like): Apparent viscosity array. [Pa.s]
        deta (array-like): Error in apparent viscosity array. [Pa.s]

    Outputs:
        ReqError (numeric): Error in the equivalent hydraulic resistance.
            Unite non homogene a R_eq, voir ci-dessus.
        dRi (array-like): Error in individual hydraulic resistance for each
            nozzle. Unite non homogene a Ri, voir ci-dessus.
        
        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    dRi = np.ones(alpha)
    sum_terms = np.zeros(alpha)

    for i in range(alpha):
        dRi[i] = (np.pi / 128) * (np.sum(1 / Ri) ** (-2)) * np.sqrt(((D[0,i] ** 2 / (eta[i] * L[0])) ** 4 * (L[0] * deta[i]) ** 2) +
                                                                      ((eta[i] * L[1]) ** 2) +
                                                                      16 * ((eta[i] * L[0] * D[1,i] / D[0,i])) ** 2)
        sum_terms[i] = (dRi[i] / Ri[i] ** 2) ** 2

    ReqError = R_eq ** 2 * np.sqrt(np.sum(sum_terms))

    return ReqError, dRi

