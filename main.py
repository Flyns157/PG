#!/usr/bin/env python3
"""
Point d'entrée principal pour l'interface TUI du Gestionnaire de Mots de Passe.

Ce script lance l'application avec l'interface utilisateur textuelle moderne
utilisant Rich et Textual.
"""

import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pg.tui.app import PasswordManagerApp


def main():
    """Point d'entrée de l'application TUI."""
    print("Initialisation du gestionnaire de mots de passe...")
    print("Lancement de l'interface TUI...")
    
    app = PasswordManagerApp()
    app.run()


if __name__ == "__main__":
    main()
