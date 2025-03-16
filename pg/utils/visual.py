# pg.utils.visual.py
import os
from .security import supported_algorithms

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
    
def display_supported_algorithms():
    print("Algorithmes de hachage supportés:")
    for algo in supported_algorithms():
        print(f"- {algo}")