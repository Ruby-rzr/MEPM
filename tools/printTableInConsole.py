import pandas as pd


def printTableInConsole(data):
    """Affiche un tableau de valeurs dans la console.

    Fonction d'AFFICHAGE, appelee uniquement en mode debogage. Elle ne
    participe a aucun calcul.

    Args:
        data (array-like): valeurs a afficher, dans l'unite de la grandeur
            annoncee par l'appelant.
    """
    # Constructing the DataFrame
    df = pd.DataFrame(data)

    # Displaying the DataFrame
    print(df)
