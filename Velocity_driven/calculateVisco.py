import numpy as np

from Velocity_driven.modeles import (
    BINGHAM, CARREAU, HERSCHEL_BULKLEY, HERSCHEL_BULKLEY_ETENDU,
    LOI_DE_PUISSANCE, NEWTONIEN, SISKO, valide_modele)

# Cles attendues du dictionnaire d'incertitudes, et unite de chacune.
CLES_INCERTITUDES = ("K", "n", "eta_inf", "eta_0", "tau_0", "lambda", "a")


def calculateVisco(SR, n, K, eta_inf, eta_0, tau_0, lmbda, a, modele,
                   incertitudes, debug_mode=False, dSR=None):
    """
    calculateVisco is the function used to obtain the apparent viscosity inside every nozzle, depending on the material's behavior law.

    Unites : SI strict. Toutes les grandeurs de cette fonction sont deja en
    SI dans la base de materiaux, aucune conversion n'a lieu ici.

    CHOIX EXPLICITE DU MODELE, phase 5. La loi rheologique etait auparavant
    DEVINEE par une cascade de `if` testant quels parametres valaient zero.
    Un parametre laisse a zero par oubli changeait silencieusement la loi
    appliquee. Le modele est desormais un argument obligatoire. La cascade
    subsiste dans Velocity_driven.modeles.deduire_modele_historique, isolee et
    reservee a la lecture de l'ancienne base materials.xls.

    INCERTITUDES, regle 5 de CLAUDE.md. Elles ne sont plus des constantes du
    code : ce sont des proprietes du materiau et de son ajustement, fournies
    par la base par l'intermediaire du dictionnaire `incertitudes`. Une
    incertitude absente vaut zero, ce qui annule sa contribution.

    Inputs:
        SR (array-like): Shear rate. [1/s]
        n (numeric): Viscosity index. [-]
        K (numeric): Consistency index. [Pa.s^n]
        eta_inf (numeric): Infinite viscosity. [Pa.s]
        eta_0 (numeric): Rest-state viscosity. [Pa.s]
        tau_0 (numeric): Creep factor. [Pa]
        lmbda (numeric): Relaxation time. [s]
        a (numeric): Carreau model exponent. [-]
        modele (str): loi rheologique, l'une de Velocity_driven.modeles.MODELES.
        incertitudes (dict): incertitudes sur les parametres du materiau, aux
            cles CLES_INCERTITUDES, chacune dans l'unite du parametre
            correspondant. Une cle absente vaut zero.
        debug_mode (bool): Flag to print debug information
        dSR (array-like): Error in shear rate array. [1/s]
            Obligatoire. Provient de calculateSR. DEFAUT #14 corrige en
            phase 5 : cet argument etait ecrase par une constante en dur, ce
            qui annulait la propagation de l'incertitude sur le cisaillement.

    Outputs:
        eta (array-like): Apparent viscosity array. [Pa.s]
        deta (array-like): Error in apparent viscosity array. [Pa.s]
        
        Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
            %Date: June 13, 2020 - February 13, 2024
    """
    valide_modele(modele)
    incertitudes = dict(incertitudes or {})
    inconnues = set(incertitudes) - set(CLES_INCERTITUDES)
    if inconnues:
        raise ValueError(f"Incertitudes inconnues : {sorted(inconnues)}. "
                         f"Cles admises : {list(CLES_INCERTITUDES)}.")

    dK = incertitudes.get("K", 0.0)
    dn = incertitudes.get("n", 0.0)
    # DEFAUT #14 corrige : l'incertitude sur le taux de cisaillement, propagee
    # depuis calculateSR, est desormais UTILISEE. Elle etait ecrasee ici par
    # une constante en dur de 1e-4, ce qui la reduisait a zero en pratique.
    if dSR is None:
        raise ValueError(
            "dSR est obligatoire : l'incertitude sur le taux de cisaillement "
            "doit etre propagee depuis calculateSR, elle n'a pas de valeur "
            "par defaut defendable.")
    dSR = np.asarray(dSR, dtype=float)
    deta_inf = incertitudes.get("eta_inf", 0.0)
    deta_0 = incertitudes.get("eta_0", 0.0)
    dlambda = incertitudes.get("lambda", 0.0)
    da = incertitudes.get("a", 0.0)
    dtau_0 = incertitudes.get("tau_0", 0.0)

    # Ensure SR does not contain zero to avoid log(0) issues
    if np.any(SR == 0):
        raise ValueError('SR contains zero values, which will cause issues with logarithm calculations.')

    if isinstance(SR, np.ndarray) and isinstance(n, (int, float)) and isinstance(K, (int, float)) \
            and isinstance(eta_inf, (int, float)) and isinstance(eta_0, (int, float)) \
            and isinstance(tau_0, (int, float)) and isinstance(lmbda, (int, float)) \
            and isinstance(a, (int, float)):

        # Sisko model
        if modele == SISKO:
            eta = K * SR ** (n - 1) + eta_inf  
            deta = np.sqrt((SR ** (n - 1) * dK) ** 2 + (K * (n - 1) * SR ** (n - 2) * dSR) ** 2 + (K * SR ** (n - 1) * np.log(SR) * dn) ** 2 + deta_inf ** 2)
            if debug_mode:
                print('Sisko model is used')

        # Newtonian model
        elif modele == NEWTONIEN:
            eta = eta_inf * np.ones(SR.shape)  
            deta = deta_inf * np.ones(SR.shape)
            if debug_mode:
                print('Newtonian model is used')

        # Pure power law model
        elif modele == LOI_DE_PUISSANCE:
            eta = K * SR ** (n - 1)  
            deta = np.sqrt((SR ** (n - 1) * dK) ** 2 + (K * (n - 1) * SR ** (n - 2) * dSR) ** 2 + (K * SR ** (n - 1) * np.log(SR) * dn) ** 2)
            if debug_mode:
                print('Ostwald-de-Waele model (pure power law) is used')

        # Carreau model
        elif modele == CARREAU:
            eta = eta_inf + (eta_0 - eta_inf) * (1 + (lmbda * SR) ** a) ** ((n - 1) / a)  
            ratio = 1 + (lmbda * SR) ** a
            deta1 = ((1 - ratio ** ((n - 1) / a)) * deta_inf) ** 2
            deta2 = (ratio ** ((n - 1) / a) * deta_0) ** 2
            deta3 = ((eta_0 - eta_inf) * ratio ** ((n - 1 - a) / a) * (n - 1) * (lmbda * SR) ** (a - 1) * SR * dlambda) ** 2
            deta4 = ((eta_0 - eta_inf) * ratio ** ((n - 1 - a) / a) * (n - 1) * (lmbda * SR) ** (a - 1) * lmbda * dSR) ** 2
            deta5 = ((eta_0 - eta_inf) * (n - 1) * ratio / a * ((lmbda * SR) ** a * (np.log(lmbda * SR)) / (1 + (lmbda * SR) ** a) - np.log(ratio) / a) * da) ** 2
            deta = np.sqrt(deta1 + deta2 + deta3 + deta4 + deta5)
            if debug_mode:
                print('Carreau model is used')

        # Bingham model
        elif modele == BINGHAM:
            eta = tau_0 / SR + eta_inf  
            deta = np.sqrt((dtau_0 / SR) ** 2 + (tau_0 * dSR / SR ** 2) ** 2 + (deta_inf) ** 2)
            if debug_mode:
                print('Bingham model is used')

        # Herschell-Bulkley extended model
        elif modele == HERSCHEL_BULKLEY_ETENDU:
            eta = tau_0 / SR + K * SR ** (n - 1) + eta_inf
            # DEFAUT #15 corrige. Derivees partielles de
            #   eta = tau_0/SR + K SR^(n-1) + eta_inf
            #   d/d tau_0  = 1/SR
            #   d/dK       = SR^(n-1)
            #   d/d eta_inf= 1
            #   d/dSR      = -tau_0/SR^2 + K (n-1) SR^(n-2)
            #   d/dn       = K SR^(n-1) ln(SR)
            # L'expression precedente n'elevait pas au carre les deux derniers
            # termes, utilisait SR^(n-1) au lieu de SR^(n-2) dans la derivee en
            # SR, et additionnait -tau_0/SR^2 et K(n-1)SR^(n-2) avec des signes
            # opposes aux leurs, ce qui les faisait se compenser au lieu de
            # s'ajouter. Elle rendait NaN des que SR etait inferieur a 1.
            d_dSR = -tau_0 / SR ** 2 + K * (n - 1) * SR ** (n - 2)
            deta = np.sqrt((dtau_0 / SR) ** 2
                           + (SR ** (n - 1) * dK) ** 2
                           + deta_inf ** 2
                           + (d_dSR * dSR) ** 2
                           + (K * SR ** (n - 1) * np.log(SR) * dn) ** 2)
            if debug_mode:
                print('Herschell-Bulkley extended model is used')

        # Herschell-Bulkley model
        elif modele == HERSCHEL_BULKLEY:
            eta = tau_0 / SR + K * SR ** (n - 1)
            # DEFAUT #15 corrige, meme correction que la branche etendue
            # ci-dessus, sans le terme en eta_inf.
            d_dSR = -tau_0 / SR ** 2 + K * (n - 1) * SR ** (n - 2)
            deta = np.sqrt((dtau_0 / SR) ** 2
                           + (SR ** (n - 1) * dK) ** 2
                           + (d_dSR * dSR) ** 2
                           + (K * SR ** (n - 1) * np.log(SR) * dn) ** 2)
            if debug_mode:
                print('Herschell-Bulkley model is used')
        else:
            raise ValueError(f'No model was found for your material: {modele!r}')

        return eta, deta

    else:
        raise ValueError('Inputs SR, n, K, eta_inf, eta_0, tau_0, lmbda, and a must be numeric.')
