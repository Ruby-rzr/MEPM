import numpy as np

def calculateReqError(R_eq, Ri, alpha, D, L, eta, deta):
    """
    calculateReqError is the function used to calculate the error in the equivalent hydraulic resistance.

    Unites : SI strict.

    PROPAGATION, DERIVEE DE LA DEFINITION DE Ri
        En conduite cylindrique, la resistance d'une buse vaut

            Ri = (128 L eta / (pi D^4)) * (3 + 1/n)/4

        Les trois grandeurs mesurees qui l'affectent sont eta, L et D. Les
        derivees partielles logarithmiques valent

            dRi/dL   = Ri / L        dRi/dEta = Ri / eta
            dRi/dD   = -4 Ri / D

        d'ou, en sommant les contributions en quadrature,

            delta_Ri = Ri * sqrt( (delta_eta/eta)^2
                                + (delta_L/L)^2
                                + (4 delta_D/D)^2 )

        Ecrite ainsi, la formule est homogene par construction : delta_Ri
        porte la dimension de Ri quelle que soit cette dimension.

        La resistance equivalente vaut R_eq = 1 / somme(1/Ri), d'ou

            dR_eq/dRi = R_eq^2 / Ri^2
            delta_R_eq = R_eq^2 * sqrt( somme( (delta_Ri / Ri^2)^2 ) )

        Cette derniere expression etait deja correcte dans le code d'origine.

    CE QUI A CHANGE, DEFAUT #20
        L'expression precedente de delta_Ri additionnait sous une meme racine
        trois termes de dimensions differentes,

            (D^2/(eta L))^4 (L delta_eta)^2 ,  (eta delta_L)^2 ,
            16 (eta L delta_D / D)^2

        le tout multiplie par (pi/128) et par somme(1/Ri)^-2. Le premier terme
        valait environ 3.9e-17 contre 1012 pour les deux autres sur un cas
        courant, soit quatorze ordres de grandeur sous la resolution flottante
        de la somme : il ne contribuait aucun bit. La consequence n'etait donc
        pas une erreur d'arrondi mais une erreur d'echelle, delta_Ri portant
        la dimension de Ri^2 fois une longueur.

        HYPOTHESE, NON DEMONTREE : les deux derniers termes et le facteur 16
        correspondent exactement aux contributions de delta_L et de delta_D
        derivees ci-dessus, ce qui suggere que l'expression d'origine visait
        la meme propagation, avec un prefacteur (pi/128) inverse, un
        somme(1/Ri)^-2 apparemment repris de la propagation de R_eq, et un
        premier terme dont la forme n'est pas reconstituable. Cette lecture
        n'est pas verifiable : aucune trace de la derivation d'origine ne
        figure dans le depot. Elle n'est enoncee ici que pour expliquer
        pourquoi la formule ci-dessus n'est pas presentee comme une
        reconstruction fidele de l'intention des auteurs, mais comme une
        derivation nouvelle a partir de la definition de Ri.

    DEFAUT #12, INCHANGE
        Cette propagation est celle de la resistance CYLINDRIQUE. Elle est
        appliquee telle quelle en buse conique, ou Ri ne depend ni de eta ni
        de D de la meme facon, et ou delta_K et delta_n devraient intervenir.
        Le resultat n'a donc pas de sens en conique. Ce defaut est anterieur,
        il n'est pas traite ici : la branche conique est reecrite en phase 7,
        avec sa propre propagation.

    Inputs:
        R_eq (numeric): Equivalent hydraulic resistance. Unite dependante de
            la branche, voir calculateReq.
        Ri (array-like): Individual hydraulic resistance for each nozzle.
        alpha (int): Number of nozzles. [-]
        D (array-like): Nozzle diameter array (3, alpha), sortie, erreur,
            entree. [m]
        L (array-like): Nozzle length and its error. [m]
        eta (array-like): Apparent viscosity array. [Pa.s]
        deta (array-like): Error in apparent viscosity array. [Pa.s]

    Outputs:
        ReqError (numeric): Error in the equivalent hydraulic resistance,
            homogene a R_eq.
        dRi (array-like): Error in individual hydraulic resistance for each
            nozzle, homogene a Ri.

        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    Ri = np.asarray(Ri, dtype=float)
    eta = np.asarray(eta, dtype=float)
    deta = np.asarray(deta, dtype=float)

    incertitude_relative = np.sqrt((deta / eta) ** 2
                                   + (L[1] / L[0]) ** 2
                                   + (4 * D[1, :] / D[0, :]) ** 2)
    dRi = Ri * incertitude_relative

    ReqError = R_eq ** 2 * np.sqrt(np.sum((dRi / Ri ** 2) ** 2))

    return ReqError, dRi
