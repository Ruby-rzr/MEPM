# Iteration de la vitesse reelle, pour la phase 8

`Velocity_driven/generateVreal.py` a ete retire en phase 6 comme code mort : il
etait NON IMPORTABLE, sa premiere ligne etant `from MEPM import ...` alors
qu'aucun paquet `MEPM` n'existe dans le depot. Ses seuls appelants,
`main_iterP.py` et `main_iterP_2.py`, sont eux-memes casses pour la meme raison.

Il portait cependant la logique d'iteration des equations 4.7 et 4.8 de la these
de J.-F. Chauvette (2023), necessaire en phase 8 pour resoudre le cas des buses
non identiques : imposer Delta_P, recalculer Q_i = Delta_P / R_i, et iterer
jusqu'a une variation relative inferieure a 1e-4.

Son contenu est reproduit ici VERBATIM, pour memoire. Ce n'est pas du code, il
ne s'execute pas, et il porte au moins un defaut connu.

## Defaut connu de cette version

Le facteur de Weissenberg-Rabinowitsch y est applique DEUX FOIS DE PLUS que
necessaire : `SR_temp *= rabi` apres un `calculateSR` qui l'applique deja, et
`Ri *= rabi` apres un `calculateReq` qui l'applique deja. Voir le piege decrit
en tete de CLAUDE.md. Toute reutilisation doit repartir des equations, pas de ce
fichier.

## Contenu au moment du retrait

```python
from MEPM import calculateQ, calculatePrequired, calculateReq, calculateReqError, calculateSR, calculateVisco, validateReynolds
from tools import printTableInConsole
import numpy as np
import os
import sys

mepm_path = r"C:\Users\anirb\OneDrive\Desktop\Additive Nozzle Manufacturing\CODE FOR MEPM"
sys.path.append(mepm_path)


def generate_V_real(P, dP, Q, rho, v, D, L, n, K, eta_0, eta_inf, tau_0, lambda_, a, P_amb, debug_mode):
    print('\n-----------------------True Velocity calculation -----------------------')
    print(f'Desired nozzle exit speed (mm/s) = {v: .2f}')
    print(f'Real applied pressure (Pa) = {P:.0f}\n')

    Q_real = np.zeros(D.shape[1])
    eta_real = np.zeros(D.shape[1])
    Q_theo = np.zeros(D.shape[1])
    dQ_crit = 10**-4

    rabi = (3+(1/n))/4

    for i in range(D.shape[1]):
        variation_Q = dQ_crit+1
        nbIter = 0
        Q_guess = Q[i]

        if debug_mode:
            print(f'<strong>Nozzle #{i+1} -----------------------</strong>')
            print(f'Starting Q_guess (mm³/s) = {Q_guess:.4f}')

        while variation_Q >= dQ_crit:
            nbIter += 1
            if debug_mode:
                print(f'Iteration Velocity #{nbIter}')

            SR_temp = calculateSR.calculateSR(Q_guess, D[:, i], 0)
            SR_temp *= rabi
            eta_temp, deta_temp = calculateVisco.calculateVisco(
                SR_temp, n, K, eta_inf, eta_0, tau_0, lambda_, a, debug_mode, 0)
            _, Ri = calculateReq.calculateReq(eta_temp, L[0], D[:, i])
            Ri *= rabi
            _, dRi = calculateReqError.calculateReqError(
                0, Ri, 1, D[:, i], L[0], eta_temp, deta_temp)
            Q_temp = (P - P_amb)/Ri
            dQ_temp = (dP/Ri)**2 + ((P - P_amb)*dRi/Ri**2)**2
            variation_Q = abs(Q_temp - Q_guess) / Q_guess
            Q_guess = Q_temp

            if debug_mode:
                print(f'Q_temp_{nbIter} (mm³/s) = {Q_temp:.4f}')
                print(f'dQ_{nbIter} = {variation_Q:.8f}')

        Q_real[i] = Q_temp
        Q_theo[i] = (np.pi * n / (3 * n + 1)) * (D[0, i] / 2)**((1 + 3 * n) / n) * \
            ((P - P_amb + rho * 9.81 * L[0] / 1000) / (2 * K * L[0]))**(1/n)
        Q_guess_error = dQ_temp
        eta_real = eta_temp

    v_real = Q_real/(0.25*np.pi*D[0, :]**2)
    dv_real = ((Q_guess_error / (np.pi * 4 * D[0, :]**2))**2) + (
        (D[1, :] * Q_temp) / (np.pi * 4 * D[0, :]**3))**3

    print('Real nozzle exit velocities (mm/s):')
    printTableInConsole.print_table_in_console(v_real)

    print('Real nozzle exit flow rates (mm³/s):')
    printTableInConsole.print_table_in_console(Q_real)

    _, Re = validateReynolds(rho, v_real, D, eta_real, debug_mode)
    if debug_mode:
        print('Reynold numbers:')
        printTableInConsole.print_table_in_console(Re)

    return v_real, Q_real, dv_real, Q_theo
```
