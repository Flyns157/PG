# pg.view.auth.py
from tkinter import Tk, messagebox
from tkinter.ttk import Entry, Button, Label, Frame

from ..data.models import User

from . import clear_screen


def create_login_screen(root: Tk):
    clear_screen(root)
    
    frame = Frame(root, padding=20)
    frame.pack(expand=True)
    
    Label(frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w")
    username_entry = Entry(frame)
    username_entry.grid(row=0, column=1, pady=5)
    
    Label(frame, text="Mot de passe:").grid(row=1, column=0, sticky="w")
    password_entry = Entry(frame, show="*")
    password_entry.grid(row=1, column=1, pady=5)
    
    Button(frame, text="Connexion", command=lambda: login(root, username_entry.get(), password_entry.get())).grid(row=2, column=0, columnspan=2, pady=10)
    Button(frame, text="Inscription", command=lambda: create_register_screen(root)).grid(row=3, column=0, columnspan=2, pady=5)

def create_register_screen(root: Tk):
    clear_screen(root)
    
    frame = Frame(root, padding=20)
    frame.pack(expand=True)
    
    Label(frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w")
    new_username_entry = Entry(frame)
    new_username_entry.grid(row=0, column=1, pady=5)
    
    Label(frame, text="Mot de passe:").grid(row=1, column=0, sticky="w")
    new_password_entry = Entry(frame, show="*")
    new_password_entry.grid(row=1, column=1, pady=5)
    
    Button(frame, text="Créer un compte", command=lambda: register(root, new_username_entry.get(), new_password_entry.get())).grid(row=2, column=0, columnspan=2, pady=10)
    Button(frame, text="Retour", command=lambda: create_login_screen(root)).grid(row=3, column=0, columnspan=2, pady=5)

def login(root: Tk, username: str, password: str):
    if (user := User.get_by_username(username)):
        if user.verify_password(password):
            from .home import create_home_screen
            create_home_screen(root, user)
        else:
            messagebox.showerror("Erreur", "Mot de passe incorrect")
    else:
        messagebox.showerror("Erreur", "Utilisateur inconnu")

def register(root: Tk, username: str, password: str):
    try:
        user = User.create(
            username=username,
            password=password,
            hash_algorithm="sha256"
        )
        messagebox.showinfo("Succès", "Compte créé avec succès")
        from .home import create_home_screen
        create_home_screen(root, user)
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")
    create_home_screen(root, user)
