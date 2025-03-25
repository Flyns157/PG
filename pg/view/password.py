# pg.view.password.py
from tkinter import Tk, Toplevel, Text, Scrollbar
from tkinter.ttk import Treeview, Frame, Label, Entry, Button
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

    tree.tag_configure("description", foreground="gray", font=("Arial", 10, "italic"))
    tree.bind("<<TreeviewSelect>>", lambda event: update_description(tree))
    return tree

def update_description(tree: Treeview):
    selected_item = tree.selection()
    if not selected_item:
        return
    
    item_id = selected_item[0]
    item_values = tree.item(item_id, "values")

    if not item_values or len(item_values) == 0:
        return
    
    password_id = item_values[0]
    if not password_id:
        return
    
    password = Password.get_by_id(password_id) 

    if password is None:
        messagebox.showerror("Erreur", "Impossible de récupérer les détails du mot de passe.")
        return

    # Supprimer toute ligne de description existante
    for child in tree.get_children():
        if tree.item(child, "tags") == ("description",):
            tree.delete(child)

    description_text = password.description if password.description else "Aucune description disponible"

    tree.insert(
        "", 
        tree.index(item_id) + 1,  # Position après l'élément sélectionné
        values=("", description_text),  # Première colonne vide pour alignement
        tags=("description",)  # Tag pour identifier la ligne
    )

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

def create_add_password_window(root: Tk, user: User, tree):
    add_window = Toplevel(root)
    add_window.title("Ajouter un mot de passe")
    add_window.geometry("400x410")
    
    Label(add_window, text="Site web:").pack()
    url_entry = Entry(add_window, width=50)
    url_entry.pack()
    
    Label(add_window, text="Description (optionnel):").pack()
    description_frame = Frame(add_window)
    description_frame.pack()
    description_text = Text(description_frame, height=4, width=40)
    description_text.pack(side="left", fill="both", expand=True)
    description_scroll = Scrollbar(description_frame, command=description_text.yview)
    description_scroll.pack(side="right", fill="y")
    description_text.config(yscrollcommand=description_scroll.set)
    
    Label(add_window, text="Identifiant:").pack()
    key_entry = Entry(add_window, width=50)
    key_entry.pack()
    
    Label(add_window, text="Mot de passe:").pack()
    password_entry = Entry(add_window, show="*", width=50)
    password_entry.pack()
    
    Label(add_window, text="Adresse e-mail (optionnel):").pack()
    email_entry = Entry(add_window, width=50)
    email_entry.pack()
    
    Label(add_window, text="Numéro de téléphone (optionnel):").pack()
    phone_entry = Entry(add_window, width=50)
    phone_entry.pack()
    
    def save_password():
        try:
            Password.create(
                user_id=user.id,
                url=url_entry.get(),
                description=description_text.get("1.0", "end").strip() or None,
                key=key_entry.get(),
                password=password_entry.get(),
                email=email_entry.get() or None,
                phone=phone_entry.get() or None
            )
            messagebox.showinfo("Succès", "Mot de passe ajouté avec succès")
            add_window.destroy()
            load_passwords(user=user, tree=tree, limit=10000)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")
    
    Button(add_window, text="Enregistrer", command=save_password).pack(pady=10)
    Button(add_window, text="Annuler", command=add_window.destroy).pack()

def create_edit_password_window(root: Tk, user: User, tree):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Avertissement", "Veuillez sélectionner un mot de passe à modifier.")
        return
    
    password_id = tree.item(selected_item, "values")[0]
    password = Password.get_by_id(password_id)
    if password is None or password.user_id != user.id:
        messagebox.showerror("Erreur", "Mot de passe introuvable ou non autorisé.")
        return
    
    edit_window = Toplevel(root)
    edit_window.title("Modifier un mot de passe")
    edit_window.geometry("400x400")
    
    Label(edit_window, text="Nouvelle description:").pack()
    description_text = Text(edit_window, height=4, width=40)
    description_text.insert("1.0", password.description or "")
    description_text.pack()
    
    Label(edit_window, text="Nouvelle clé:").pack()
    key_entry = Entry(edit_window)
    key_entry.insert(0, password.key)
    key_entry.pack()
    
    Label(edit_window, text="Nouveau mot de passe:").pack()
    password_entry = Entry(edit_window, show="*")
    password_entry.pack()
    
    def update_password():
        try:
            password.update(
                description=description_text.get("1.0", "end").strip() or None,
                key=key_entry.get(),
                password=password_entry.get() or None
            )
            messagebox.showinfo("Succès", "Mot de passe modifié avec succès")
            edit_window.destroy()
            load_passwords(user=user, tree=tree, limit=10000)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")
    
    Button(edit_window, text="Enregistrer", command=update_password).pack(pady=10)
    Button(edit_window, text="Annuler", command=edit_window.destroy).pack()

def delete_selected_password(user: User, tree: Treeview):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Suppression", "Veuillez sélectionner un mot de passe à supprimer.")
        return
    
    password_id = tree.item(selected_item, "values")[0]
    confirmation = messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce mot de passe ?")
    
    if confirmation:
        try:
            Password.delete_by_id(password_id)
            messagebox.showinfo("Succès", "Mot de passe supprimé avec succès")
            load_passwords(user=user, tree=tree, limit=10000)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")