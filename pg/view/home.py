# pg.view.home.py
from tkinter import Tk
from tkinter.ttk import Frame, Button, Label, Entry
from tkinter import messagebox

from ..data.models import User

from .auth import create_login_screen
from . import clear_screen
from .password import (
    add_password_tree,
    load_passwords,
    toggle_password_visibility,
    create_add_password_window,
    create_edit_password_window,
    delete_selected_password
)

NOT_IMPLEMENTED_YET = "Fonctionnalité à implémenter"

def create_home_screen(root: Tk, user: User):
    clear_screen(root=root)
    
    menu = Frame(root)
    menu.pack(fill="x")
    
    # TODO : déplacer les bouttons d'import et export ici

    Button(menu, text="Déconnexion", command=lambda: create_login_screen(root)).pack(side="right", padx=5, pady=5)
    Button(menu, text="À propos", command=lambda: messagebox.showinfo("À propos", "Gestionnaire de mots de passe v1.0")).pack(side="right", padx=5, pady=5)
    
    Label(root, text=f"Bienvenue {user.username}", font=("Arial", 14)).pack(pady=10)
    
    search_frame = Frame(root)
    search_frame.pack(pady=5)
    
    Label(search_frame, text="Rechercher: ").pack(side="left")
    search_entry = Entry(search_frame, width=40)
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
    
    Button(button_frame, text="Ajouter un mot de passe", command=lambda: create_add_password_window(root, user, tree)).pack(side="left", padx=5)
    Button(button_frame, text="Modifier le mot de passe", command=lambda: create_edit_password_window(root, user, tree)).pack(side="left", padx=5)
    Button(button_frame, text="Afficher/Masquer mot de passe", command=lambda: toggle_password_visibility(tree)).pack(side="left", padx=5)
    Button(button_frame, text="Supprimer le mot de passe", command=lambda: delete_selected_password(user, tree)).pack(side="left", padx=5)
    
    add_import_export_buttons(root, tree, user)


from tkinter import filedialog, messagebox
from tkinter.ttk import Treeview
from pathlib import Path
from sqlalchemy.orm import Session

from ..services.password import (
    export_passwords,
    import_passwords
)
from sqlmodel import Session
from ..data.database import engine


def add_import_export_buttons(root: Tk, tree: Treeview, user: User):
    button_frame = Frame(root)
    button_frame.pack(pady=5, fill="x")
    
    # Bouton d'export
    export_btn = Button(
        button_frame, 
        text="Exporter vers CSV",
        command=lambda: export_passwords_gui(root, user, tree)
    )
    export_btn.pack(side="left", padx=5)
    
    # Bouton d'import
    import_btn = Button(
        button_frame,
        text="Importer depuis CSV",
        command=lambda: import_passwords_gui(root, user, tree)
    )
    import_btn.pack(side="left", padx=5)

def export_passwords_gui(root: Tk, user: User, tree: Treeview):
    try:
        # Demander le chemin de sauvegarde
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv")],
            initialfile="passwords_export.csv"
        )
        
        if not file_path:  # Si l'utilisateur annule
            return
            
        file_path = Path(file_path)
        
        with Session(engine) as session:
            export_passwords(
                session=session,
                user=user,
                file_path=file_path
            )
        
        messagebox.showinfo(
            "Export réussi",
            f"Les mots de passe ont été exportés avec succès vers:\n{file_path}"
        )
        
        # Rafraîchir l'affichage
        load_passwords(
            tree=tree,
            user=user,
            limit=10000
        )
    except Exception as e:
        messagebox.showerror(
            "Erreur d'export",
            f"Une erreur est survenue lors de l'export:\n{str(e)}"
        )

def import_passwords_gui(root: Tk, user: User, tree: Treeview):
    try:
        # Demander le fichier à importer
        file_path = filedialog.askopenfilename(
            filetypes=[("Fichiers CSV", "*.csv")],
            title="Sélectionnez le fichier CSV à importer"
        )
        
        if not file_path:  # Si l'utilisateur annule
            return
            
        file_path = Path(file_path)
        
        # Confirmation avant import
        if not messagebox.askyesno(
            "Confirmation",
            "Êtes-vous sûr de vouloir importer ces mots de passe?\n"
            "Les doublons seront ignorés."
        ):
            return
            
        import_passwords(user, file_path)
        
        messagebox.showinfo(
            "Import réussi",
            "Les mots de passe ont été importés avec succès!"
        )
        
        # Rafraîchir l'affichage
        load_passwords(
            tree=tree,
            user=user,
            limit=10000
        )
    except Exception as e:
        messagebox.showerror(
            "Erreur d'import",
            f"Une erreur est survenue lors de l'import:\n{str(e)}"
        )
