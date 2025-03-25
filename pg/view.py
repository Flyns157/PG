from tkinter import ttk, messagebox
from sqlmodel import Session, select

from .utils.search_engine import similar_passwords

from .data.models import User, Password
from .data.database import engine


NOT_SPECIFIED = ""

class PasswordGestionApp:
    COLUMNS = ("URL", "Identifiant", "Mot de passe", "Email", "Téléphone", "Date de création", "Date de modification")

    def __init__(self, root):
        self.root = root
        self.root.title("Gestionnaire de mots de passe")
        self.root.geometry("600x400")
        
        self.create_login_screen()
    
    def create_login_screen(self):
        self.clear_screen()
        
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w")
        self.username_entry = ttk.Entry(frame)
        self.username_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Mot de passe:").grid(row=1, column=0, sticky="w")
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)
        
        ttk.Button(frame, text="Connexion", command=self.login).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(frame, text="Inscription", command=self.create_register_screen).grid(row=3, column=0, columnspan=2, pady=5)
    
    def create_register_screen(self):
        self.clear_screen()
        
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)
        
        ttk.Label(frame, text="Nom d'utilisateur:").grid(row=0, column=0, sticky="w")
        self.new_username_entry = ttk.Entry(frame)
        self.new_username_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Mot de passe:").grid(row=1, column=0, sticky="w")
        self.new_password_entry = ttk.Entry(frame, show="*")
        self.new_password_entry.grid(row=1, column=1, pady=5)
        
        ttk.Button(frame, text="Créer un compte", command=self.register).grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(frame, text="Retour", command=self.create_login_screen).grid(row=3, column=0, columnspan=2, pady=5)
    
    def login(self):
        if (user := User.get_by_username(self.username_entry.get())):
            if user.verify_password(self.password_entry.get()):
                self.create_main_screen(user)
            else:
                messagebox.showerror("Erreur", "Mot de passe incorrect")
        else:
            messagebox.showerror("Erreur", "Utilisateur inconnu")
    
    def register(self):
        try:
            user = User.create(
                username=self.new_username_entry.get(),
                password=self.new_password_entry.get(),
                hash_algorithm="sha256"
            )
            messagebox.showinfo("Succès", "Compte créé avec succès")
            self.create_main_screen(user)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")
        self.create_login_screen()
    
    def create_main_screen(self, user: User):
        self.clear_screen()
        
        menu = ttk.Frame(self.root)
        menu.pack(fill="x")
        
        ttk.Button(menu, text="Déconnexion", command=self.create_login_screen).pack(side="right", padx=5, pady=5)
        ttk.Button(menu, text="À propos", command=lambda: messagebox.showinfo("À propos", "Gestionnaire de mots de passe v1.0")).pack(side="right", padx=5, pady=5)
        
        ttk.Label(self.root, text=f"Bienvenue {user.username}", font=("Arial", 14)).pack(pady=10)
        
        search_frame = ttk.Frame(self.root)
        search_frame.pack(pady=5)
        
        ttk.Label(search_frame, text="Rechercher: ").pack(side="left")
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="OK", command=lambda: self.filter_passwords(user)).pack(side="left")
        
        self.tree = ttk.Treeview(self.root, columns=PasswordGestionApp.COLUMNS, show="headings")
        for col in PasswordGestionApp.COLUMNS:
            self.tree.heading(col, text=col)
        self.tree.pack(pady=10, fill="both", expand=True)
        
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=5)
        
        ttk.Button(button_frame, text="Ajouter un mot de passe", command=lambda: messagebox.showinfo("Ajout", "Fonctionnalité à implémenter")).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Exporter", command=lambda: messagebox.showinfo("Export", "Exportation en cours...")).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Afficher/Masquer mots de passe", command=self.toggle_password_visibility).pack(side="left", padx=5)
        
        self.load_passwords(user)
    
    def load_passwords(self, user: User):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        with Session(engine) as session:
            user = User.get_by_id(user.id, session=session)
            for pwd in user.passwords:
                self.tree.insert("", "end", values=(
                    pwd.url, 
                    pwd.key, 
                    pwd.password,
                    pwd.email or NOT_SPECIFIED,
                    pwd.phone or NOT_SPECIFIED,
                    pwd.date_added,
                    pwd.date_updated
                ))
    
    def filter_passwords(self, user: User):
        search_term = self.search_entry.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        

        try:
            with Session(engine) as session:
                user = User.get_by_id(user.id, session=session)
                listed_passwords = similar_passwords(user.passwords, search_term)
                if not listed_passwords:
                    messagebox.showinfo("Aucun résultat", f"Aucun mot de passe ne correspond à la recherche \"{search_term}\".")
                    return
                nearest_url = listed_passwords[0].url
                nearest_domaine_name=str(nearest_url).split("/")[2]
                statement = select(Password).where(Password.url.like(f'%{nearest_domaine_name}%') & Password.user_id == user.id)
                nearest_passwords = session.exec(statement).fetchall()

                for pwd in nearest_passwords:
                    self.tree.insert("", "end", values=(
                    pwd.url, 
                    pwd.key, 
                    pwd.password,
                    pwd.email or NOT_SPECIFIED,
                    pwd.phone or NOT_SPECIFIED,
                    pwd.date_added,
                    pwd.date_updated
                ))
        except ValueError as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass

    def toggle_password_visibility(self):
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if "●●●●●" in values:
                values[2]=Password.get_by_id(values)
                self.tree.item(item, values=(values[0], values[1], "motdepasse"))  # Remplacer par la vraie valeur
            else:
                self.tree.item(item, values=(values[0], values[1], "●●●●●"))
    

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
