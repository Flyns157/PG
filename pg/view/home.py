from tkinter import Tk
from tkinter.ttk import Frame, Button, Label, Entry
from tkinter import messagebox

from ..data.models import User

from .auth import create_login_screen
from . import clear_screen
from .password import add_password_tree, load_passwords, toggle_password_visibility


NOT_IMPLEMENTED_YET = "Fonctionnalité à implémenter"

def create_home_screen(root: Tk, user: User):
    clear_screen(root=root)
    
    menu = Frame(root)
    menu.pack(fill="x")
    
    Button(menu, text="Importer/Exporter", command=lambda: messagebox.showinfo("Import/Export", NOT_IMPLEMENTED_YET)).pack(side="left", padx=5, pady=5)
    Button(menu, text="Déconnexion", command=lambda: create_login_screen(root)).pack(side="right", padx=5, pady=5)
    Button(menu, text="À propos", command=lambda: messagebox.showinfo("À propos", "Gestionnaire de mots de passe v1.0")).pack(side="right", padx=5, pady=5)
    
    Label(root, text=f"Bienvenue {user.username}", font=("Arial", 14)).pack(pady=10)
    
    search_frame = Frame(root)
    search_frame.pack(pady=5)
    
    Label(search_frame, text="Rechercher: ").pack(side="left")
    search_entry = Entry(search_frame)
    search_entry.pack(side="left", padx=5)

    tree = add_password_tree(root)
    load_passwords(
        user=user,
        tree=tree,
        limit=10000
    )

    Button(search_frame, text="OK", command=lambda: load_passwords(
        user=user,
        tree=tree,
        query=search_entry.get().strip(),
        limit=10000
    )).pack(side="left")
    
    
    button_frame = Frame(root)
    button_frame.pack(pady=5)
    
    Button(button_frame, text="Ajouter un mot de passe", command=lambda: messagebox.showinfo("Ajout", NOT_IMPLEMENTED_YET)).pack(side="left", padx=5)
    Button(button_frame, text="Modifier le mot de passe", command=lambda: messagebox.showinfo("Modification", NOT_IMPLEMENTED_YET)).pack(side="left", padx=5)
    Button(button_frame, text="Afficher/Masquer mot de passe", command=lambda: toggle_password_visibility(tree)).pack(side="left", padx=5)
