import numpy as np
import pandas as pd
import os
import sys
import tkinter as tk
from tkinter import filedialog

# FICHIER MORT, meme raison que main_iterP.py : il importe un paquet 'MEPM'
# inexistant. Le chemin absolu Windows qui figurait ici a ete retire en
# phase 6.

from MEPM import calculateQ, calculatePrequired, calculateReq, calculateReqError, calculateSR, calculateVisco, validateReynolds, generateVreal 
from tools import printTableInConsole

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

def read_material(file, material):
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
    return rho, w, f, n, K, eta_inf, eta_0, tau_0, lambda_, a

def generate_p(*args):
    # Placeholder for generateP function logic
    pass

def generate_vreal(*args):
    # Placeholder for generateVreal function logic
    pass

def print_table_in_console(data):
    for i, val in enumerate(data):
        print(f"Value {i + 1}: {val}")

def open_material_file():
    """
    Opens a file explorer window to select the material database file (Excel).

    Returns:
        tuple: A tuple containing the selected file path or None if cancelled,
               and a list of material sheet names (if a file was chosen).
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    filepath = filedialog.askopenfilename(filetypes=[("Excel files", "*.xls"), ("Excel files", "*.xlsx")])
    if filepath:
        workbook = pd.ExcelFile(filepath)
        sheet_names = workbook.sheet_names
        return filepath, sheet_names
    else:
        return None, None

# Main script
def main(args):
    print("Using Velocity-driven library")

    # Check if a file path is provided via command line
    if len(args) > 1:
        file = args[1]
    else:
        file, sheet_names = open_material_file()
        if not file:
            print("User selected Cancel")
            return

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

    # Add the rest of your main script logic here

if __name__ == "__main__":
    main(sys.argv)
