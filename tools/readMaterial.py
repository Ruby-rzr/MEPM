import pandas as pd

# ---------------------------------------------------------------------------
# Incertitudes de l'ANCIENNE base, materials.xls.
#
# materials.xls ne porte aucune colonne d'incertitude. Ces valeurs etaient
# ecrites en dur dans calculateVisco. Elles sont conservees ici, a l'identique,
# parce qu'elles font partie de l'artefact gele : les references historiques ne
# seraient plus reproductibles sans elles.
#
# Elles ne sont derivees d'aucune equation et leur provenance n'est pas etablie
# dans ce depot. La nouvelle base, materiaux.xlsx, porte une colonne
# d'incertitude par parametre, ces grandeurs etant des proprietes du materiau
# et de son ajustement, non du code.
INCERTITUDES_HISTORIQUES = {
    "K": 0.1,        # [Pa.s^n]
    "n": 0.0001,     # [-]
    "eta_inf": 0.0,  # [Pa.s]
    "eta_0": 0.0,    # [Pa.s]
    "tau_0": 0.0,    # [Pa]
    "lambda": 0.0,   # [s]
    "a": 0.0,        # [-]
}


def readMaterial(file, sheet):
    """Lit les proprietes d'un materiau dans une feuille de materials.xls.

    Lecture POSITIONNELLE : la valeur de chaque propriete est prise dans la
    colonne B, a une ligne fixe. C'est le format historique, hérite du
    xlsread(file, sheet, 'A1:C10') de la version MATLAB. materials.xls est un
    artefact gele, ce lecteur ne doit pas evoluer avec lui.

    DEFAUT #10, corrige en phase 5. Les lignes mP et R ont ete ajoutees au
    format apres coup, sans mettre a jour les feuilles existantes. Douze
    feuilles sur dix-neuf n'ont que dix lignes, et la lecture levait une
    IndexError sur chacune. Elles sont desormais lues, mP et R valant zero
    quand la ligne est absente, ce qui envoie ces materiaux sur la branche
    analytique. Une valeur vide, lue comme NaN, est traitee de la meme facon :
    l'ancien code la laissait passer, et 'if R != 0' etant vrai pour un NaN,
    la resistance devenait NaN sans le moindre message.

    Args:
        file (str): chemin du classeur Excel.
        sheet (str): nom de la feuille, c'est a dire du materiau.

    Returns:
        tuple: (rho, w, f, n, k, eta_inf, eta_0, tau_0, lmbda, a, mP, R)
            rho [kg/m^3], w [wt.%], f [vol.%], n [-], k [Pa.s^n],
            eta_inf [Pa.s], eta_0 [Pa.s], tau_0 [Pa], lmbda [s], a [-],
            mP [-], R [unite indeterminee, voir calculatePrequired].

    Author: David Brzeski, Jean-François Chauvette, Raphaël Plante
    """
    # Read data from Excel file into DataFrame
    df = pd.read_excel(file, sheet_name=sheet, header=None, usecols="B")

    def valeur(ligne, defaut=0.0):
        """Valeur de la colonne B a cette ligne, ou 'defaut' si absente ou vide."""
        if ligne >= len(df):
            return defaut
        brute = df.iloc[ligne, 0]
        return defaut if pd.isna(brute) else brute

    # Extract material properties from DataFrame
    rho = df.iloc[0, 0]
    w = df.iloc[1, 0]
    f = df.iloc[2, 0]
    n = df.iloc[3, 0]
    k = df.iloc[4, 0]
    eta_inf = df.iloc[5, 0]
    eta_0 = df.iloc[6, 0]
    tau_0 = df.iloc[7, 0]
    lmbda = df.iloc[8, 0]
    a = df.iloc[9, 0]
    mP = valeur(10)
    R = valeur(11)

    return rho, w, f, n, k, eta_inf, eta_0, tau_0, lmbda, a, mP, R

