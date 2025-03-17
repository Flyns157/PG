# pg.utils.visual.py
"""
Module de gestion de l'affichage
"""

import os
from .security import supported_algorithms


def clear_screen():
    """
    Nettoie l'écran
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    
def display_supported_algorithms():
    """
    Affiche la liste des algorithmes de hachage supportés
    """
    print("Algorithmes de hachage supportés:")
    for algo in supported_algorithms():
        print(f"- {algo}")
