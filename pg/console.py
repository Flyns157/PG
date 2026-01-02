# pg/console.py
"""
Textual-based TUI interface for Password Manager.
Modern, interactive terminal user interface using Textual 6.x
"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.events import Click
from textual.reactive import reactive, var
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)
from textual import work

from sqlmodel import Session, select

from .data.models import User, Password
from .data.database import engine
from .services.password import similar_passwords

from datetime import datetime


#===============================================================================
# STYLES GLOBAUX - Design moderne et cohérent
#===============================================================================

MODERN_DARK_CSS = """
/* ================================================
   THÈME SOMBRE MODERNE - Password Manager TUI
   ================================================ */

/* Couleurs de base */
Screen {
    background: #0f0f23;
}

Container {
    background: #1a1a2e;
}

/* Boutons modernisés */
Button {
    height: 3;
    border: none;
    transition: background 0.3s, transform 0.1s;
}

Button:hover {
    text-style: bold;
}

Button:focus {
    outline: solid $primary;
}


Button.variant-success {
    color: white;
}

Button.variant-success:hover {
}

Button.variant-error {
    color: white;
}

Button.variant-error:hover {
}

Button.variant-warning {
    color: white;
}

Button.variant-default {
    background: #2d2d44;
    color: #e0e0e0;
}

Button.variant-default:hover {
    background: #3d3d5c;
}

/* Inputs modernisés */
Input {
    height: 3;
    border: solid #3d3d5c;
    background: #0f0f23;
    color: #e0e0e0;
    padding: 0 1;
    transition: border 0.3s, box-shadow 0.3s;
}

Input:focus {
    border: solid #667eea;
}

/* Labels et textes */
Label {
    color: #e0e0e0;
}

.header-title {
    color: #667eea;
    text-style: bold;
    text-align: center;
}

.section-title {
    color: #764ba2;
    text-style: bold;
    text-align: left;
}

.help-text {
    color: #888;
    text-style: italic;
}

.error-text {
    color: #ff6b6b;
    text-style: bold;
}

.success-text {
    color: #38ef7d;
    text-style: bold;
}

.info-text {
    color: #4ecdc4;
}

/* DataTable modernisé */
DataTable {
    border: solid #3d3d5c;
    background: #0f0f23;
}

/* Header et Footer */
Header {
    color: #667eea;
    text-style: bold;
}

Footer {
    background: #0f0f23;
    color: #666;
    text-style: italic;
}

/* Modals */
ModalScreen {
    background: rgba(15, 15, 35, 0.95);
}

/* TextArea */
TextArea {
    border: solid #3d3d5c;
    background: #0f0f23;
    color: #e0e0e0;
    padding: 1;
}

TextArea:focus {
    border: solid #667eea;
}

/* Éléments de la sidebar */
#sidebar {
    border-right: solid #667eea;
}

#sidebar-container {
    padding: 1;
}

#user-section {
    border: solid #667eea;
    padding: 1;
    margin-bottom: 1;
}

#search-section {
    border-bottom: solid #3d3d5c;
    padding: 1;
}

.nav-button {
    width: 100%;
    height: auto;
    margin-bottom: 0;
    content-align: left middle;
}

.separator {
    height: 1;
    background: #3d3d5c;
    margin: 1 0;
}

/* Containers principaux */
.main-container {
    layout: grid;
    grid-size: 5 1;
}

.sidebar-panel {
    column-span: 1;
    width: 32;
    dock: left;
}

.content-panel {
    column-span: 4;
}

/* Status bar */
#status-bar {
    height: 2;
    background: #0f0f23;
    color: #888;
    padding: 0 1;
    text-align: left;
}

/* Badges et indicateurs */
.badge {
    background: #667eea;
    color: white;
    padding: 0 1;
}

.badge-success {
    background: #38ef7d;
    color: #0f0f23;
}

.badge-error {
    background: #ff6b6b;
    color: white;
}

/* Scrollbar personnalisée */
VerticalScroll {
    background: #1a1a2e;
}

/* Footer hints */
Footer {
    dock: bottom;
    height: 1;
}
"""


#===============================================================================
# ÉCRAN DE CONNEXION
#===============================================================================

class LoginScreen(Screen):
    """Écran de connexion avec design moderne et animations fluides"""
    
    CSS = MODERN_DARK_CSS + """
    LoginScreen {
        align: center middle;
        background: #0f0f23;
    }
    
    #login-container {
        width: 50;
        height: auto;
        max-height: 85;
        border: solid #667eea;
        padding: 3;
    }
    
    #logo-section {
        text-align: center;
        margin-bottom: 2;
    }
    
    #logo-icon {
        margin-bottom: 1;
    }
    
    #title {
        text-align: center;
        color: #e0e0e0;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #subtitle {
        text-align: center;
        color: #888;
        margin-bottom: 2;
    }
    
    #error-message {
        color: #ff6b6b;
        text-align: center;
        margin-bottom: 1;
        padding: 1;
        background: rgba(255, 107, 107, 1);
        display: none;
    }
    
    .input-group {
        margin-bottom: 1;
    }
    
    .input-icon {
        width: 3;
        color: #667eea;
    }
    
    #login-button {
        margin-top: 2;
        height: 4;
    }
    
    #register-button {
        margin-top: 1;
        height: 3;
    }
    
    #footer-text {
        text-align: center;
        color: #666;
        margin-top: 2;
    }
    
    #footer-text > Link {
        color: #667eea;
        text-style: underline;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Container(
            Grid(
                # Logo et titre
                Label("🔐", id="logo-icon"),
                Label("Gestionnaire de Mots de Passe", id="title"),
                Label("Entrez vos identifiants pour accéder à vos mots de passe", id="subtitle"),
                
                # Message d'erreur
                Label("", id="error-message"),
                
                # Champs de formulaire
                Input(
                    placeholder="👤 Nom d'utilisateur",
                    id="username",
                    validate_on=["changed"]
                ),
                Input(
                    placeholder="🔒 Mot de passe",
                    id="password",
                    password=True,
                    validate_on=["changed"]
                ),
                
                # Boutons d'action
                Button("✅ Se connecter", id="login-button", variant="primary", classes="action-button"),
                Button("📝 Créer un compte", id="register-button", variant="default"),
                
                # Pied de page
                Label("Nouveau ? Cliquez sur 'Créer un compte' pour commencer", id="footer-text"),
                
                classes="login-grid",
            ),
            id="login-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-button":
            self.login()
        elif event.button.id == "register-button":
            self.app.push_screen(RegisterScreen())
    
    def login(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        error_label = self.query_one("#error-message", Label)
        
        if not username:
            self.show_error("Veuillez entrer votre nom d'utilisateur")
            return
        
        if not password:
            self.show_error("Veuillez entrer votre mot de passe")
            return
        
        user = User.get_by_username(username)
        if user and user.verify_password(password):
            self.app.current_user = user
            self.app.notify(f"Bienvenue, {user.username} !", severity="success", duration=2)
            self.app.push_screen(DashboardScreen())
        else:
            self.show_error("Nom d'utilisateur ou mot de passe incorrect")
    
    def show_error(self, message: str) -> None:
        error_label = self.query_one("#error-message", Label)
        error_label.update(message)
        error_label.display = True
        # Animation de secousse
        container = self.query_one("#login-container", Container)
        container.styles.animation = "shake 0.3s ease-in-out"
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Hide error message when user starts typing"""
        error_label = self.query_one("#error-message", Label)
        error_label.display = False


#===============================================================================
# ÉCRAN D'INSCRIPTION
#===============================================================================

class RegisterScreen(Screen):
    """Écran d'inscription avec validation en temps réel"""
    
    CSS = MODERN_DARK_CSS + """
    RegisterScreen {
        align: center middle;
        background: #0f0f23;
    }
    
    #register-container {
        width: 52;
        height: auto;
        max-height: 90;
        border: solid #764ba2;
        padding: 3;
    }
    
    #title {
        text-align: center;
        color: #e0e0e0;
        text-style: bold;
        margin-bottom: 2;
    }
    
    #error-message {
        color: #ff6b6b;
        text-align: center;
        margin-bottom: 1;
        padding: 1;
        background: rgba(255, 107, 107, 0.1);
        display: none;
    }
    
    #success-message {
        color: #38ef7d;
        text-align: center;
        margin-bottom: 1;
        padding: 1;
        background: rgba(56, 239, 125, 0.1);
        display: none;
    }
    
    #password-requirements {
        color: #888;
        margin-bottom: 1;
        padding: 1;
        border-left: solid #667eea;
        background: rgba(102, 126, 234, 0.05);
    }
    
    #register-button {
        margin-top: 2;
        height: 4;
    }
    
    #back-button {
        margin-top: 1;
        height: 3;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Container(
            Grid(
                Label("📝 Création de compte", id="title"),
                Label("", id="error-message"),
                Label("", id="success-message"),
                Input(placeholder="👤 Nom d'utilisateur", id="username"),
                Input(placeholder="🔒 Mot de passe", id="password", password=True),
                Input(placeholder="🔒 Confirmer le mot de passe", id="password-confirm", password=True),
                Static(
                    "📋 Requirements:\n• Au moins 8 caractères\n• Minuscules et majuscules\n• Chiffres recommandés",
                    id="password-requirements"
                ),
                Button("✅ Créer le compte", id="register-button", variant="primary"),
                Button("⬅️ Retour", id="back-button", variant="default"),
                classes="register-grid",
            ),
            id="register-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "register-button":
            self.register()
        elif event.button.id == "back-button":
            self.app.pop_screen()
    
    def register(self) -> None:
        username = self.query_one("#username", Input).value.strip()
        password = self.query_one("#password", Input).value
        password_confirm = self.query_one("#password-confirm", Input).value
        error_label = self.query_one("#error-message", Label)
        success_label = self.query_one("#success-message", Label)
        
        error_label.display = False
        success_label.display = False
        
        if not username:
            self.show_error("Veuillez entrer un nom d'utilisateur")
            return
        
        if not password:
            self.show_error("Veuillez entrer un mot de passe")
            return
        
        if len(password) < 8:
            self.show_error("Le mot de passe doit contenir au moins 8 caractères")
            return
        
        if password != password_confirm:
            self.show_error("Les mots de passe ne correspondent pas")
            return
        
        if User.get_by_username(username):
            self.show_error("Ce nom d'utilisateur existe déjà")
            return
        
        try:
            user = User.create(
                username=username,
                password=password,
                hash_algorithm="sha256"
            )
            success_label.update("✅ Compte créé avec succès! Redirection...")
            success_label.display = True
            self.app.notify("Bienvenue dans Password Gestion!", severity="success", duration=3)
            
            def redirect():
                self.app.pop_screen()
            
            self.call_later(redirect)
            
        except Exception as e:
            self.show_error(f"Erreur lors de la création: {str(e)}")
    
    def show_error(self, message: str) -> None:
        error_label = self.query_one("#error-message", Label)
        error_label.update(message)
        error_label.display = True
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Hide messages when user modifies input"""
        error_label = self.query_one("#error-message", Label)
        success_label = self.query_one("#success-message", Label)
        error_label.display = False
        success_label.display = False


#===============================================================================
# MODALES DE GESTION DES MOTS DE PASSE
#===============================================================================

class PasswordModal(ModalScreen):
    """Modale moderne pour ajouter/modifier un mot de passe"""
    
    CSS = MODERN_DARK_CSS + """
    PasswordModal {
        align: center middle;
    }
    
    #modal-container {
        width: 60;
        height: auto;
        max-height: 90;
        border: solid #667eea;
        padding: 2;
    }
    
    #modal-title {
        text-align: center;
        color: #667eea;
        text-style: bold;
        margin-bottom: 2;
    }
    
    #description-field {
        height: 6;
    }
    
    #action-buttons {
        margin-top: 2;
    }
    
    #save-button {
        width: 100%;
        height: 4;
    }
    
    #cancel-button {
        width: 100%;
        margin-top: 1;
    }
    
    .field-required {
        color: #ff6b6b;
        text-style: bold;
    }
    
    .field-optional {
        color: #888;
    }
    """
    
    def __init__(self, title: str, password_id: int = None, user: User = None):
        super().__init__()
        self.title_text = title
        self.password_id = password_id
        self.user = user
        self.existing_password = None
        
        if password_id:
            self.existing_password = Password.get_by_id(password_id)
    
    def compose(self) -> ComposeResult:
        existing = self.existing_password
        
        yield Container(
            Grid(
                Label(self.title_text, id="modal-title"),
                Input(placeholder="🌐 URL / Service (obligatoire)", id="url", 
                      value=existing.url if existing else ""),
                Input(placeholder="👤 Identifiant (obligatoire)", id="key", 
                      value=existing.key if existing else ""),
                Input(placeholder="🔒 Mot de passe (obligatoire)", id="password-field", 
                      password=True, value=existing.password if existing else ""),
                Input(placeholder="📧 Email (optionnel)", id="email", 
                      value=existing.email if existing and existing.email else ""),
                Input(placeholder="📱 Téléphone (optionnel)", id="phone", 
                      value=existing.phone if existing and existing.phone else ""),
                TextArea(placeholder="📝 Description (optionnel)", id="description", 
                        text=existing.description if existing and existing.description else ""),
                Button("💾 Enregistrer", id="save-button", variant="primary"),
                Button("❌ Annuler", id="cancel-button", variant="default"),
                classes="modal-grid",
            ),
            id="modal-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            self.save_password()
        elif event.button.id == "cancel-button":
            self.dismiss()
    
    def save_password(self) -> None:
        url = self.query_one("#url", Input).value.strip()
        key = self.query_one("#key", Input).value.strip()
        password = self.query_one("#password-field", Input).value
        email = self.query_one("#email", Input).value.strip() or None
        phone = self.query_one("#phone", Input).value.strip() or None
        description = self.query_one("#description", TextArea).value.strip() or None
        
        if not url:
            self.app.notify("⚠️ L'URL/Service est obligatoire", severity="warning")
            return
        
        if not key:
            self.app.notify("⚠️ L'identifiant est obligatoire", severity="warning")
            return
        
        if not password:
            self.app.notify("⚠️ Le mot de passe est obligatoire", severity="warning")
            return
        
        try:
            if self.password_id:
                self.existing_password.update(
                    url=url,
                    key=key,
                    password=password,
                    email=email,
                    phone=phone,
                    description=description
                )
                self.app.notify("✅ Mot de passe modifié!", severity="success")
            else:
                Password.create(
                    user_id=self.user.id,
                    url=url,
                    key=key,
                    password=password,
                    email=email,
                    phone=phone,
                    description=description
                )
                self.app.notify("✅ Mot de passe créé!", severity="success")
            
            self.dismiss(True)
            
        except Exception as e:
            self.app.notify(f"❌ Erreur: {str(e)}", severity="error")


class ConfirmModal(ModalScreen):
    """Modale de confirmation moderne"""
    
    CSS = MODERN_DARK_CSS + """
    ConfirmModal {
        align: center middle;
    }
    
    #modal-container {
        width: 50;
        height: auto;
        border: solid #f5576c;
        padding: 2;
    }
    
    #confirm-message {
        text-align: center;
        color: #e0e0e0;
        margin-bottom: 2;
    }
    
    #warning-icon {
        text-align: center;
        margin-bottom: 1;
    }
    
    #buttons {
        margin-top: 1;
    }
    
    #confirm-button {
        width: 100%;
        height: 4;
    }
    
    #cancel-button {
        width: 100%;
        margin-top: 1;
    }
    """
    
    def __init__(self, message: str, warning: bool = True):
        super().__init__()
        self.message = message
        self.show_warning = warning
    
    def compose(self) -> ComposeResult:
        warning_icon = "⚠️" if self.show_warning else "❓"
        
        yield Container(
            Grid(
                Label(warning_icon, id="warning-icon"),
                Label(self.message, id="confirm-message"),
                Button("🗑️ Confirmer la suppression", id="confirm-button", variant="error"),
                Button("⬅️ Annuler", id="cancel-button", variant="default"),
                id="modal-container",
            ),
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-button":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ImportExportModal(ModalScreen):
    """Modale pour import/export avec design moderne"""
    
    CSS = MODERN_DARK_CSS + """
    ImportExportModal {
        align: center middle;
    }
    
    #modal-container {
        width: 58;
        height: auto;
        border: solid #4ecdc4;
        padding: 2;
    }
    
    #modal-title {
        text-align: center;
        color: #4ecdc4;
        text-style: bold;
        margin-bottom: 2;
    }
    
    #file-path {
        width: 100%;
    }
    
    #help-text {
        margin-bottom: 1;
        padding: 1;
        background: rgba(78, 205, 196, 0.1);
    }
    
    #status-message {
        text-align: center;
        margin-top: 1;
        padding: 1;
    }
    
    #confirm-button {
        width: 100%;
        height: 4;
        margin-top: 1;
    }
    
    #cancel-button {
        width: 100%;
        margin-top: 1;
    }
    """
    
    def __init__(self, mode: str = "export", user: User = None):
        super().__init__()
        self.mode = mode
        self.user = user
    
    def compose(self) -> ComposeResult:
        mode_label = "📤 Exportation vers CSV" if self.mode == "export" else "📥 Importation depuis CSV"
        help_text = "Format: URL, Identifiant, Mot de passe, Email, Téléphone, Description"
        
        yield Container(
            Grid(
                Label(mode_label, id="modal-title"),
                Input(placeholder="📁 Chemin du fichier...", id="file-path"),
                Static(help_text, id="help-text", classes="help-text"),
                Label("", id="status-message"),
                Button("✅ Valider", id="confirm-button", variant="success" if self.mode == "export" else "primary"),
                Button("❌ Annuler", id="cancel-button", variant="default"),
                classes="import-export-grid",
            ),
            id="modal-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-button":
            self.process_action()
        elif event.button.id == "cancel-button":
            self.dismiss()
    
    def process_action(self) -> None:
        file_path = self.query_one("#file-path", Input).value.strip()
        status_label = self.query_one("#status-message", Label)
        
        if not file_path:
            status_label.update("⚠️ Veuillez spécifier un chemin de fichier")
            status_label.classes = "error-text"
            return
        
        if self.mode == "export":
            try:
                from .services.password import export_passwords
                from pathlib import Path
                
                file_path = Path(file_path)
                with Session(engine) as session:
                    export_passwords(
                        session=session,
                        user=self.user,
                        file_path=file_path
                    )
                
                status_label.update(f"✅ Exporté vers: {file_path}")
                status_label.classes = "success-text"
                self.app.notify(f"Mots de passe exportés vers {file_path}", severity="success")
                self.call_later(lambda: self.dismiss())
                
            except Exception as e:
                status_label.update(f"❌ Erreur: {str(e)}")
                status_label.classes = "error-text"
        
        else:  # import
            try:
                from .services.password import import_passwords
                from pathlib import Path
                
                file_path = Path(file_path)
                if not file_path.exists():
                    status_label.update("❌ Fichier introuvable")
                    status_label.classes = "error-text"
                    return
                
                import_passwords(self.user, file_path)
                
                status_label.update("✅ Importé avec succès!")
                status_label.classes = "success-text"
                self.app.notify("Mots de passe importés!", severity="success")
                self.call_later(lambda: self.dismiss())
                
            except Exception as e:
                status_label.update(f"❌ Erreur: {str(e)}")
                status_label.classes = "error-text"


#===============================================================================
# ÉCRAN PRINCIPAL - DASHBOARD
#===============================================================================

class DashboardScreen(Screen):
    """Tableau de bord principal avec sidebar et tableau de données"""
    
    CSS = MODERN_DARK_CSS + """
    DashboardScreen {
        layout: grid;
        grid-size: 5 1;
    }
    
    #sidebar {
        column-span: 1;
        width: 30;
        border-right: solid #667eea;
    }
    
    #sidebar-container {
        padding: 1;
    }
    
    #user-section {
        border: solid #667eea;
        padding: 1;
        margin-bottom: 1;
    }
    
    #user-avatar {
        text-align: center;
        margin-bottom: 1;
    }
    
    #user-name {
        text-align: center;
        color: #667eea;
        text-style: bold;
    }
    
    #search-section {
        border-bottom: solid #3d3d5c;
        padding: 1;
    }
    
    #search-input {
        width: 100%;
    }
    
    #quick-actions {
        padding: 1;
        border-bottom: solid #3d3d5c;
    }
    
    #quick-actions-title {
        color: #888;
        margin-bottom: 1;
        text-transform: uppercase;
        text-style: bold;
    }
    
    #main-content {
        column-span: 4;
        padding: 1;
    }
    
    #header-section {
        margin-bottom: 1;
    }
    
    #table-section {
        height: 1fr;
    }
    
    .nav-button {
        width: 100%;
        height: auto;
        margin-bottom: 0;
        padding: 1 1;
        text-align: left;
    }
    
    .nav-button:hover {
        background: rgba(102, 126, 234, 0.15);
    }
    
    #table-info {
        color: #888;
        margin-bottom: 1;
    }
    
    #empty-state {
        align: center middle;
        height: 100%;
        color: #666;
        text-align: center;
    }
    
    #empty-icon {
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        ("a", "add_password", "Ajouter"),
        ("e", "edit_password", "Modifier"),
        ("d", "delete_password", "Supprimer"),
        ("r", "toggle_visibility", "Afficher/Masquer"),
        ("f", "focus_search", "Rechercher"),
        ("q", "quit", "Quitter"),
        ("l", "logout", "Déconnexion"),
        ("ctrl+f", "focus_search", "Rechercher"),
        ("escape", "pop_screen", "Retour"),
    ]
    
    def __init__(self):
        super().__init__()
        self.search_query = ""
        self.show_passwords = False
        self.user = None
    
    def compose(self) -> ComposeResult:
        # Sidebar
        yield Container(
            Container(
                Label("👤", id="user-avatar"),
                Label("Utilisateur", id="user-name"),
                id="user-section",
            ),
            Container(
                Input(placeholder="🔍 Rechercher...", id="search-input"),
                id="search-section",
            ),
            Container(
                Label("Actions rapides", id="quick-actions-title"),
                Button("➕ Ajouter", id="btn-add", variant="primary", classes="nav-button"),
                Button("✏️ Modifier", id="btn-edit", classes="nav-button"),
                Button("🗑️ Supprimer", id="btn-delete", variant="error", classes="nav-button"),
                Button("👁️ Afficher/Masquer", id="btn-toggle", classes="nav-button"),
                Label("", classes="separator"),
                Label("Gestion des données", id="quick-actions-title"),
                Button("📤 Exporter", id="btn-export", classes="nav-button"),
                Button("📥 Importer", id="btn-import", classes="nav-button"),
                Label("", classes="separator"),
                Button("🚪 Déconnexion", id="btn-logout", variant="error", classes="nav-button"),
            ),
            id="sidebar-container",
        ),
        id="sidebar",
        
        # Main content
        yield Container(
            Header(show_clock=True),
            Container(
                Label("Vos mots de passe", id="table-info"),
                DataTable(
                    zebra_stripes=True,
                    cursor_type="row",
                    show_cursor=True,
                    id="passwords-table",
                ),
                id="table-section",
            ),
            Static("Appuyez sur F1 pour l'aide", id="footer-hint", classes="help-text"),
            id="main-content",
        )
        
        yield Footer()
    
    def on_mount(self) -> None:
        self.user = self.app.current_user
        
        # Setup user info
        user_label = self.query_one("#user-name", Label)
        user_label.update(f"@{self.user.username}")
        
        # Setup table
        table = self.query_one("#passwords-table", DataTable)
        table.add_columns(
            "ID",
            "🌐 URL / Service",
            "👤 Identifiant",
            "🔒 Mot de passe",
            "📧 Email",
            "📱 Téléphone",
            "📅 Création",
            "🔄 Modification"
        )
        table.sort("ID")
        
        # Load passwords
        self.load_passwords()
        
        # Focus search
        self.query_one("#search-input", Input).focus()
    
    @work(thread=True)
    def load_passwords(self, query: str = None) -> None:
        table = self.query_one("#passwords-table", DataTable)
        info_label = self.query_one("#table-info", Label)
        
        info_label.update("Chargement...")
        
        with Session(engine) as session:
            user = session.get(User, self.user.id)
            passwords = similar_passwords(
                session=session,
                user=user,
                query=query,
                limit=10000
            ) if query else list(user.passwords)
            
            total_count = len(user.passwords)
            self.app.call_from_thread(self.populate_table, passwords, total_count)
    
    def populate_table(self, passwords: list, total_count: int = 0) -> None:
        table = self.query_one("#passwords-table", DataTable)
        table.clear()
        
        mask = "••••••" if not self.show_passwords else None
        
        for pwd in passwords:
            table.add_row(
                str(pwd.id),
                pwd.url[:30] + ("..." if len(pwd.url) > 30 else ""),
                pwd.key,
                pwd.password if self.show_passwords else mask,
                (pwd.email[:20] + "..." if len(pwd.email) > 20 else pwd.email) if pwd.email else "-",
                pwd.phone or "-",
                pwd.date_added.strftime("%Y-%m-%d") if pwd.date_added else "-",
                pwd.date_updated.strftime("%Y-%m-%d") if pwd.date_updated else "-",
            )
        
        info_label = self.query_one("#table-info", Label)
        shown = len(passwords)
        total = total_count or shown
        status = "affichés" if self.show_passwords else "masqués"
        info_label.update(f"📊 {shown}/{total} mot(s) de passe ({status})")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_query = event.value
            self.load_passwords(self.search_query)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        
        if button_id == "btn-add":
            self.action_add_password()
        elif button_id == "btn-edit":
            self.action_edit_password()
        elif button_id == "btn-delete":
            self.action_delete_password()
        elif button_id == "btn-toggle":
            self.action_toggle_visibility()
        elif button_id == "btn-export":
            self.action_export()
        elif button_id == "btn-import":
            self.action_import()
        elif button_id == "btn-logout":
            self.action_logout()
    
    def action_add_password(self) -> None:
        self.push_screen(PasswordModal("➕ Ajouter un mot de passe", user=self.user), 
                        self.on_password_modal_closed)
    
    def action_edit_password(self) -> None:
        table = self.query_one("#passwords-table", DataTable)
        selected = table.cursor_row
        
        if selected is None:
            self.app.notify("⚠️ Veuillez sélectionner un mot de passe", severity="warning")
            return
        
        try:
            row = table.get_row_at(selected)
            password_id = int(row[0])
            self.push_screen(PasswordModal("✏️ Modifier le mot de passe", 
                                         password_id=password_id), 
                           self.on_password_modal_closed)
        except (ValueError, IndexError):
            self.app.notify("❌ Erreur lors de la sélection", severity="error")
    
    def action_delete_password(self) -> None:
        table = self.query_one("#passwords-table", DataTable)
        selected = table.cursor_row
        
        if selected is None:
            self.app.notify("⚠️ Veuillez sélectionner un mot de passe", severity="warning")
            return
        
        try:
            row = table.get_row_at(selected)
            password_id = int(row[0])
            
            def confirm_delete():
                try:
                    Password.delete_by_id(password_id)
                    self.app.notify("🗑️ Mot de passe supprimé", severity="success")
                    self.load_passwords(self.search_query)
                except Exception as e:
                    self.app.notify(f"❌ Erreur: {str(e)}", severity="error")
            
            self.push_screen(
                ConfirmModal("Supprimer ce mot de passe ?"),
                lambda result: confirm_delete() if result else None
            )
        except (ValueError, IndexError):
            self.app.notify("❌ Erreur lors de la sélection", severity="error")
    
    def action_toggle_visibility(self) -> None:
        self.show_passwords = not self.show_passwords
        self.load_passwords(self.search_query)
        status = "affichés" if self.show_passwords else "masqués"
        self.app.notify(f"🔒 Mots de passe {status}", severity="information")
    
    def action_export(self) -> None:
        self.push_screen(ImportExportModal(mode="export", user=self.user))
    
    def action_import(self) -> None:
        self.push_screen(ImportExportModal(mode="import", user=self.user))
    
    def action_logout(self) -> None:
        self.app.current_user = None
        self.app.notify("👋 Déconnexion réussie", severity="information")
        self.app.pop_screen()
    
    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()
    
    def on_password_modal_closed(self, result) -> None:
        if result:
            self.load_passwords(self.search_query)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection for quick copy"""
        pass  # Ready for future clipboard feature


#===============================================================================
# APPLICATION PRINCIPALE
#===============================================================================

class PasswordManagerApp(App):
    """Application principale du Gestionnaire de Mots de Passe"""
    
    CSS = MODERN_DARK_CSS
    
    BINDINGS = [
        ("F1", "show_help", "Aide"),
        ("F5", "refresh", "Rafraîchir"),
        ("ctrl+q", "quit", "Quitter"),
        ("escape", "pop_screen", "Retour"),
    ]
    
    current_user = None
    
    def on_mount(self) -> None:
        self.push_screen(LoginScreen())
    
    def action_show_help(self) -> None:
        """Affiche l'aide"""
        help_text = """
🎯 Raccourcis clavier:
• A / Ctrl+A : Ajouter un mot de passe
• E : Modifier le mot de passe sélectionné
• D : Supprimer le mot de passe sélectionné
• R : Afficher/Masquer les mots de passe
• F / Ctrl+F : Champ de recherche
• F1 : Afficher cette aide
• F5 : Rafraîchir la liste
• Q / Ctrl+Q : Quitter
• L : Déconnexion
        
💡 Conseil: Utilisez les flèches ↑↓ pour naviguer dans le tableau
        """
        self.push_screen(HelpScreen(help_text))
    
    def action_refresh(self) -> None:
        """Rafraîchir les données"""
        self.notify("🔄 Rafraîchissement...", severity="information")
        for screen in self.screen_stack:
            if hasattr(screen, 'load_passwords'):
                screen.load_passwords(getattr(screen, 'search_query', ''))
                break
    
    def action_copy_password(self) -> None:
        """Copier le mot de passe sélectionné"""
        table = self.query_one(DataTable)
        selected = table.cursor_row
        
        if selected is None:
            self.notify("⚠️ Sélectionnez un mot de passe", severity="warning")
            return
        
        row = table.get_row_at(selected)
        password = row[3]
        
        if password and password != "••••••":
            self.clipboard = password
            self.app.notify("📋 Mot de passe copié!", severity="success")
        else:
            self.notify("⚠️ Impossible de copier (masqué)", severity="warning")


class HelpScreen(ModalScreen):
    """Écran d'aide modal"""
    
    CSS = MODERN_DARK_CSS + """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 55;
        height: auto;
        border: solid #4ecdc4;
        padding: 2;
    }
    
    #help-title {
        text-align: center;
        color: #4ecdc4;
        text-style: bold;
        margin-bottom: 2;
    }
    
    #help-content {
        color: #e0e0e0;
        white-space: pre-wrap;
        line-height: 1.6;
    }
    
    #close-button {
        width: 100%;
        margin-top: 2;
    }
    """
    
    def __init__(self, content: str):
        super().__init__()
        self.content = content
    
    def compose(self) -> ComposeResult:
        yield Container(
            Grid(
                Label("❓ Aide et Raccourcis", id="help-title"),
                Static(self.content, id="help-content"),
                Button("Fermer (ESC)", id="close-button", variant="primary"),
                classes="help-grid",
            ),
            id="help-container",
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
    
    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()


def run_tui():
    """Lancer l'interface TUI Textual"""
    app = PasswordManagerApp()
    app.run()
