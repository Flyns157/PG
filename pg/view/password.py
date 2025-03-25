# pg.views.password.py
from tkinter import Tk
from tkinter.ttk import Treeview
from tkinter import messagebox
from sqlmodel import Session

from ..services.password import similar_passwords

from ..data.models import User, Password
from ..data.database import engine

MASKED_PASSWORD = "●●●●●"

NOT_SPECIFIED = ""

COLUMNS = ("ID", "URL", "Identifiant", "Mot de passe", "Email", "Téléphone", "Date de création", "Date de modification")

def add_password_tree(root: Tk) -> Treeview:
    tree = Treeview(root, columns=COLUMNS, show="headings")
    for col in COLUMNS:
        tree.heading(col, text=col)
    tree.pack(pady=10, fill="both", expand=True)
    return tree


def load_passwords(tree: Treeview, user: User, query: str=None, limit: int=15, decrypted_passwords: bool=False):
    for row in tree.get_children():
        tree.delete(row)
    
    with Session(engine) as session:
        user = session.get(User, user.id)
        pwds = similar_passwords(
            session=session,
            user=user,
            query=query,
            limit=limit
        ) if query else user.passwords[:limit]
        if query and not pwds:
            messagebox.showinfo("Aucun résultat", f"Aucun mot de passe ne correspond à la recherche \"{query}\".")
        else:
            for pwd in pwds:
                tree.insert("", "end", values=(
                    pwd.id,
                    pwd.url, 
                    pwd.key, 
                    pwd.password if decrypted_passwords else MASKED_PASSWORD,
                    pwd.email or NOT_SPECIFIED,
                    pwd.phone or NOT_SPECIFIED,
                    pwd.date_added,
                    pwd.date_updated
                ))

def toggle_password_visibility(tree: Treeview):
    row        = tree.focus()
    values     = tree.item(row)["values"]
    new_values = list(values)
    
    if values[3] == MASKED_PASSWORD:
        new_values[3] = Password.get_by_id(values[0]).password
    else:
        new_values[3]  = MASKED_PASSWORD

    tree.item(row, values=tuple(new_values))