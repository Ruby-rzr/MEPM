#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
  FICHIER MORT, NON IMPORTABLE, NON EXECUTABLE
=============================================================================

Il importe un paquet `MEPM` qui N'EXISTE PAS dans ce depot. Toute tentative
d'import leve ModuleNotFoundError des la premiere ligne utile. Il n'est
couvert par AUCUN test et ne participe a AUCUN calcul.

POURQUOI IL EST CONSERVE
Il porte la BOUCLE D'ITERATION SUR LA PRESSION, dont la phase 8 aura besoin :
imposer Delta_P, recalculer Q_i, iterer jusqu'a une variation relative
inferieure a 1e-4.

    while variation_P >= dP_crit:
        ...
        variation_P = abs(P_temp - P_guess) / P_guess
        P_guess = P_temp

couplee a generateVreal, qui resout le cas des buses non identiques. Voir
notes/iteration_vitesse_reelle_phase_8.md, qui conserve generateVreal et
signale son defaut : il applique le facteur de Rabinowitsch deux fois de plus
que necessaire.

La phase 8 doit repartir des equations 4.7 et 4.8 de Chauvette 2023, pas de ce
fichier.

Auteurs du code d'origine : Jean-Francois Chauvette, David Brzeski, Anirban,
Raphael Plante.
"""
import numpy as np
import pandas as pd
import os
import sys
import openpyxl
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog
import xlrd

from MEPM import generateP, generateVreal, calculateQ, calculatePrequired, calculateReq, calculateReqError, calculateSR, calculateVisco, validateReynolds, generateVreal 
from tools import printTableInConsole, readMaterial

def valid_user_input(prompt, is_array=False):
    while True:
        try:
            user_input = input(prompt)
            if is_array:
                return np.array([float(i) for i in user_input.strip('[]').split(',')])
            else:
                return float(user_input)
        except ValueError:
            print("Invalid input. Please try again.")

"""def read_material(file, material):
    df = pd.read_excel(file, sheet_name=material)
    rho = df['rho'].values[0]
    w = df['w'].values[0]
    f = df['f'].values[0]
    n = df['n'].values[0]
    K = df['K'].values[0]
    eta_inf = df['eta_inf'].values[0]
    eta_0 = df['eta_0'].values[0]
    tau_0 = df['tau_0'].values[0]
    lambda_ = df['lambda'].values[0]
    a = df['a'].values[0]
    return rho, w, f, n, K, eta_inf, eta_0, tau_0, lambda_, a """

def read_material(file, material):
    df = pd.read_excel(file, sheet_name=material, header=None)
    print("Data in the sheet:\n", df)

    # Define the required parameters

    required_parameters = ['rho', 'w', 'f', 'n', 'K', 'eta_inf', 'eta_0', 'tau_0', 'lambda', 'a']
    
    # Extract the values for the required parameters
    params = {}
    for param in required_parameters:
        try:
            params[param] = df[df[0] == param].iloc[0, 1]
        except IndexError:
            raise ValueError(f"Missing parameter '{param}' in the sheet '{material}'")
    
    return (params['rho'], params['w'], params['f'], params['n'], params['K'], params['eta_inf'],
            params['eta_0'], params['tau_0'], params['lambda'], params['a'])


# def generateP(*args):
#     Placeholder for generateP function logic
#    pass

# def generateVreal(*args):
#     # Placeholder for generateVreal function logic
#     pass

def printTableInConsole(data):
    for i, val in enumerate(data):
        print(f"Value {i + 1}: {val}")

# Main script
def main():
    print("Using Velocity-driven library")

    # Add paths (not required in Python, typically handled by imports)

    # Initializing variables
    debug_mode = False  # To print in the console all the intermediate values for calculation
    dP_crit = 10**-4  # Error margin for Pressure calculation

    # Opening the material database file
    file = input("Enter the material database file to open: ")
    if not os.path.isfile(file):
        print("User selected Cancel")
        return
    else:
        print(f"User selected {file}")
        matFile = file

        # List of all the materials included in the database (sheets in the excel file)
        sheets = pd.ExcelFile(matFile).sheet_names
        print("Available materials: ")
        print(sheets)

        # Retrieve the user specified material's infos
        choices = list(map(str, range(1, len(sheets) + 1)))
        sheet_num = valid_user_input("Choose a material number: ")
        material = sheets[int(sheet_num) - 1]
        rho, w, f, n, K, eta_inf, eta_0, tau_0, lambda_, a = read_material(matFile, material)

        print(f"User selected {material}")

        # Script call for testing purposes (auto-completion of alpha, D, L, P_amb, and v values).
        # Placeholder for validation_infos call

        P_amb = 101325  # Ambient pressure [Pa]

        D = np.array([[0.257193333, 0.25623, 0.25612, 0.256406667, 0.25561, 0.25561, 0.25612, 0.255536667, 0.255376667,
                     0.25357, 0.25459, 0.25561, 0.2551, 0.25663, 0.25459, 0.2551, 0.25255, 0.25408, 0.25357, 0.25459,
                     0.25816, 0.25459, 0.25663, 0.25765, 0.25714, 0.25459],
                     [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001,
                      0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001]])
        D[0,6] = 0.9*D[0,6]
        D_avg = np.array([[0.25] * len(D), [0.01] * len(D)])
        D_current = D_avg

        L = np.array([6.5, 0.01])  # Nozzle length and error

        # Desired printing speed [mm/s]
        v = np.array([50, 100, 150, 200, 250])

        # Request the printing head informations
        # D_real = valid_user_input("Enter the array ([a,b,c,...]) of measured nozzle inner diameter (mm): ", is_array=True)
        # L_real = valid_user_input("Enter the array ([a,b,c,...]) of measured nozzle length (mm): ", is_array=True)
        # P_amb = valid_user_input("Enter the ambient pressure (Pa): ")

        # Request a printing velocity
        # v = valid_user_input("Enter an array of nominal desired extrusion velocity for the nozzles (mm/s): ", is_array=True)

        # Preallocation
        # D = D_real
        # L = L_real
        P = np.zeros(len(v))
        eta = np.zeros((len(v), len(D)))
        SR = np.zeros((len(v), len(D)))
        Q = np.zeros((len(v), len(D)))
        v_all = np.zeros((len(v), len(D)))
        Q_all = np.zeros((len(v), len(D)))
        Q_theo = np.zeros((len(v), len(D)))
        Errv_real = np.zeros((len(v), len(D)))
        dRi = np.zeros((len(v), len(D)))
        dP = np.zeros(len(v))
        deta = np.zeros((len(v), len(D)))
        dSR = np.zeros((len(v), len(D)))

        # Compute overall P for desired nozzle exit speed and retrieve viscosity/shear rate data
        # for each P/v

        # Constants
        P_amb = 101325  # Ambient pressure [Pa]

        D = np.array([[0.257193333, 0.25623, 0.25612, 0.256406667, 0.25561, 0.25561, 0.25612, 0.255536667, 0.255376667,
                     0.25357, 0.25459, 0.25561, 0.2551, 0.25663, 0.25459, 0.2551, 0.25255, 0.25408, 0.25357, 0.25459,
                     0.25816, 0.25459, 0.25663, 0.25765, 0.25714, 0.25459],
                     [0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001,
                      0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001]])
        D[0,6] = 0.9*D[0,6]
        D_avg = np.array([[0.25] * len(D), [0.01] * len(D)])
        D_current = D_avg

        L = np.array([6.5, 0.01])  # Nozzle length and error

        # Desired printing speed [mm/s]
        v = np.array([50, 100, 150, 200, 250])

        variation_P = dP_crit + 1
        nbIter = 0  # Number of iteration needed for convergence
        P_guess = 0

        print("=" * 86)
        while variation_P >= dP_crit:
            nbIter += 1
            if debug_mode:
                print(f"Iteration Pressure #{nbIter}")

            for i in range(len(v)):
                newP, newEta, newSR, newQ, newdEta, newdP, newdRi, newdSR = generateP.generateP(rho, v[i], D_current, L, n, K, eta_0, eta_inf, tau_0, lambda_, a, P_amb, debug_mode)
                if np.isnan(newP):
                    raise ValueError("Pressure could not be computed due to invalid Reynolds number")
                else:
                    P[i] = newP
                    eta[i, :] = newEta
                    SR[i, :] = newSR
                    Q[i, :] = newQ
                    dP[i] = newdP
                    dRi[i, :] = newdRi
                    deta[i, :] = newdEta
                    dSR[i, :] = newdSR
            P_temp = P

            # Compute true velocity and flow for nozzle true applied pressure
            # for each P/v combination
            for i in range(len(v)):
                v_real, Q_real, dv_real, q_long = generateVreal.generate_V_real(P[i], dP[i], Q[i, :], rho, v[i], D, L, n, K, eta_0, eta_inf, tau_0, lambda_, a, P_amb, debug_mode)
                v_all[i, :] = v_real
                Q_all[i, :] = Q_real
                Errv_real[i, :] = dv_real
                Q_theo[i, :] = q_long

            variation_P = abs(P_temp - P_guess) / P_guess  # Delta P with previous guess
            P_guess = P_temp  # New Q guess
            D_current = D

            if debug_mode:
                print(f"Q_temp_{nbIter} = {P_temp:.4f}")
                print(f"dQ_{nbIter} = {variation_P:.8f}")

        print("\n-------------------- Filament diameter calculation --------------------------\n")
        v_travel = v  # ./9
        for j in range(len(v_travel)):
            print(f"Filament diameters for v travel = {v_travel[j]:.2f} mm/s")
            D_fila = np.sqrt(4 * Q_all[j, :] / (np.pi * v_travel[j]))
            printTableInConsole.print_table_in_console(D_fila)

        # Graphs ------------------------------------
        P = P / 1000  # convert Pa to kPa and plot
        dP = dP / 1000  # convert Pa to kPa and plot
        plot_mode = 'default'

        # Plot and compare with literature values to validate the model
        # Nozzle #1 is plotted here
        # compare_plot_pv(v, P, v, P_lit, [0, 0], [0, 0], dP, plot_mode)
        # i = 5
        # compare_plot_visco(SR[:, i], eta[:, i], SR_lit, eta_lit, [0, 0], [0, 0], deta[:, i], dSR[:, i], plot_mode, i)

        # Bar plot per applied pressure/desired velocity combination for comparison between nozzle exit velocities
        # Velocity #1 is plotted here
        # i = 5
        # compare_bar_plot_v(v_all[i, :], v[i], Errv_real[i, :], plot_mode, i)

if __name__ == "__main__":
    main()