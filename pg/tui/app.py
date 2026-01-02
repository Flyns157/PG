"""
Interface TUI (Text User Interface) pour le Gestionnaire de Mots de Passe.
Utilise Rich 14.2.0 et Textual 6.11.0 pour une interface moderne et reactive.
"""

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual import work
from textual.widgets import Header, Footer, Static, Input, Button, DataTable, Label
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual import events
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from datetime import datetime

from pg.data.models import User, Password
from pg.data.database import engine
from pg.services.password import similar_passwords
from sqlmodel import Session


class LoginScreen(Screen):
    """Ecran de connexion avec interface moderne"""

    CSS = """
    LoginScreen {
        align: center middle;
    }
    
    #login-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    
    #title {
        content-align: center;
        margin-bottom: 1;
    }
    
    .input-label {
        margin-bottom: 0;
        color: $text-muted;
    }
    
    #username-input, #password-input {
        margin-bottom: 1;
    }
    
    #error-message {
        color: $error;
        margin-bottom: 1;
    }
    
    .button-row {
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("enter", "submit_login", "Connexion", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Panel(
                Vertical(
                    Static(
                        Text(
                            " Gestionnaire de Mots de Passe ",
                            justify="center",
                            style="bold cyan",
                        ),
                        id="title",
                    ),
                    Static(
                        "Veuillez vous connecter pour acceder a vos mots de passe",
                        classes="input-label",
                    ),
                    Label("Nom d'utilisateur:", classes="input-label"),
                    Input(
                        id="username-input",
                        placeholder="Entrez votre nom d'utilisateur",
                    ),
                    Label("Mot de passe:", classes="input-label"),
                    Input(
                        id="password-input",
                        password=True,
                        placeholder="Entrez votre mot de passe",
                    ),
                    Static("", id="error-message"),
                    Horizontal(
                        Button("Connexion", id="login-btn", variant="primary"),
                        Button("Inscription", id="register-btn",
                               variant="default"),
                        classes="button-row",
                    ),
                ),
                title="[bold]AUTHENTIFICATION[/]",
                border_style="cyan",
                subtitle="[dim]Appuyez sur Ctrl+C pour quitter[/]",
            ),
            id="login-container",
        )

    def on_mount(self) -> None:
        self.query_one("#username-input").focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        error_widget = self.query_one("#error-message")
        error_widget.update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            self.action_submit_login()
        elif event.button.id == "register-btn":
            self.app.push_screen(RegisterScreen())

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()

    def action_submit_login(self):
        username = self.query_one("#username-input").value.strip()
        password = self.query_one("#password-input").value

        if not username or not password:
            self.show_error("Veuillez remplir tous les champs")
            return

        user = User.get_by_username(username)
        if user and user.verify_password(password):
            self.app.current_user = user
            self.app.push_screen(DashboardScreen(user))
        else:
            self.show_error("Nom d'utilisateur ou mot de passe incorrect")

    def show_error(self, message: str):
        error_widget = self.query_one("#error-message")
        error_widget.update(f"[error]✗ {message}[/]")

    def action_quit(self) -> None:
        self.app.exit()


class RegisterScreen(Screen):
    """Ecran d'inscription avec validation"""

    CSS = """
    RegisterScreen {
        align: center middle;
    }
    
    #register-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    
    #title {
        content-align: center;
        margin-bottom: 1;
    }
    
    .input-label {
        margin-bottom: 0;
        color: $text-muted;
    }
    
    #username-input, #password-input, #confirm-password-input {
        margin-bottom: 1;
    }
    
    #message {
        margin-bottom: 1;
    }
    
    .button-row {
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("enter", "submit_register", "Creer le compte", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Panel(
                Vertical(
                    Static(
                        Text(" CREER UN COMPTE ",
                             justify="center", style="bold cyan"),
                        id="title",
                    ),
                    Static(
                        "Enregistrez-vous pour commencer a gerer vos mots de passe",
                        classes="input-label",
                    ),
                    Label("Nom d'utilisateur:", classes="input-label"),
                    Input(
                        id="username-input",
                        placeholder="Choisissez un nom d'utilisateur",
                    ),
                    Label("Mot de passe:", classes="input-label"),
                    Input(
                        id="password-input",
                        password=True,
                        placeholder="Choisissez un mot de passe",
                    ),
                    Label("Confirmer le mot de passe:", classes="input-label"),
                    Input(
                        id="confirm-password-input",
                        password=True,
                        placeholder="Confirmez votre mot de passe",
                    ),
                    Static("", id="message"),
                    Horizontal(
                        Button("Creer le compte", id="create-btn",
                               variant="primary"),
                        Button("Retour", id="back-btn", variant="default"),
                        classes="button-row",
                    ),
                ),
                title="[bold]INSCRIPTION[/]",
                border_style="cyan",
                subtitle="[dim]Appuyez sur Ctrl+C pour quitter[/]",
            ),
            id="register-container",
        )

    def on_mount(self) -> None:
        self.query_one("#username-input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create-btn":
            self.action_submit_register()
        elif event.button.id == "back-btn":
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()

    def action_submit_register(self):
        username = self.query_one("#username-input").value.strip()
        password = self.query_one("#password-input").value
        confirm_password = self.query_one("#confirm-password-input").value
        message_widget = self.query_one("#message")

        if not username or not password or not confirm_password:
            message_widget.update(
                "[error]✗ Veuillez remplir tous les champs[/]")
            return

        if password != confirm_password:
            message_widget.update(
                "[error]✗ Les mots de passe ne correspondent pas[/]")
            return

        if len(password) < 8:
            message_widget.update(
                "[error]✗ Le mot de passe doit contenir au moins 8 caracteres[/]"
            )
            return

        try:
            user = User.create(
                username=username, password=password, hash_algorithm="sha256"
            )
            message_widget.update("[success]✓ Compte cree avec succes![/]")
            self.app.call_later(1.0, self.login_success, user)
        except Exception as e:
            message_widget.update(f"[error]✗ Erreur: {e}[/]")

    def login_success(self, user: User):
        self.app.current_user = user
        self.app.push_screen(DashboardScreen(user))

    def action_quit(self) -> None:
        self.app.exit()


class PasswordTable(DataTable):
    """Tableau personnalise pour l'affichage des mots de passe"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_passwords = False

    def on_mount(self) -> None:
        self.focus()

    def toggle_visibility(self):
        self.show_passwords = not self.show_passwords
        self.refresh()


class DashboardScreen(Screen):
    """Ecran principal du gestionnaire de mots de passe"""

    current_user = reactive(None)

    def __init__(self, user: User):
        super().__init__()
        self.user = user
        self.passwords = []
        self.show_passwords = False

    CSS = """
    DashboardScreen {
        layout: grid;
        grid-size: 1fr;
        grid-rows: auto 1fr auto;
    }
    
    #header {
        height: auto;
        border-bottom: solid $primary;
        padding: 1;
    }
    
    #search-container {
        height: auto;
        margin: 1 0;
    }
    
    #passwords-container {
        height: 1fr;
        border: solid $secondary;
    }
    
    #footer {
        height: auto;
        border-top: solid $primary;
        padding: 1;
    }
    
    #search-input {
        border: tall $background;
    }
    
    .status-bar {
        color: $text-muted;
        font-size: 0.8em;
    }
    
    .header-title {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("f1", "add_password", "Ajouter"),
        Binding("f2", "edit_password", "Modifier"),
        Binding("f3", "delete_password", "Supprimer"),
        Binding("f4", "copy_password", "Copier"),
        Binding("f5", "toggle_passwords", "Afficher/Masquer"),
        Binding("ctrl+q", "logout", "Deconnexion", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
        Binding("escape", "pop_screen", "Retour", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Horizontal(
                    Static("🔐", id="app-icon"),
                    Static(id="welcome-text", classes="header-title"),
                    Static(id="clock", classes="status-bar"),
                    Static(
                        "│ Deconnexion", id="logout-btn", classes="status-bar clickable"
                    ),
                    id="header",
                ),
                id="top-header",
            ),
            Container(
                Horizontal(
                    Static("🔍 ", id="search-icon"),
                    Input(
                        placeholder="Rechercher un mot de passe...",
                        id="search-input",
                        width=50,
                    ),
                    Static("│", classes="status-bar"),
                    Button(
                        "Tout afficher",
                        id="show-all-btn",
                        variant="default",
                        size="small",
                    ),
                    Button(
                        "Effacer",
                        id="clear-search-btn",
                        variant="default",
                        size="small",
                    ),
                    id="search-container",
                ),
            ),
            Container(
                PasswordTable(
                    id="passwords-table",
                    show_header=True,
                    header_height=2,
                    cursor_type="row",
                ),
                id="passwords-container",
            ),
            Container(
                Horizontal(
                    Static(id="stats-text", classes="status-bar"),
                    Static("│", classes="status-bar"),
                    Static(
                        "F1: Ajouter │ F2: Modifier │ F3: Supprimer │ F4: Copier │ F5: Afficher/Masquer │ Ctrl+Q: Deconnexion",
                        classes="status-bar",
                    ),
                    id="footer",
                ),
            ),
            id="dashboard",
        )

    def on_mount(self) -> None:
        self.query_one("#welcome-text").update(
            f"Bienvenue, [bold cyan]{self.user.username}[/]"
        )
        self.load_passwords()
        self.update_stats()
        self.set_interval(1.0, self.update_clock)

    def update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.query_one("#clock").update(f"🕐 {now}")

    @work(thread=True)
    def load_passwords(self, query: str = None):
        try:
            with Session(engine) as session:
                user = session.get(User, self.user.id)
                if query:
                    passwords = similar_passwords(
                        session=session, user=user, query=query, limit=100
                    )
                else:
                    passwords = user.passwords[:100]

                self.passwords = passwords
                self.call_later(self._refresh_table, passwords)
        except Exception as e:
            self.notify(f"Erreur lors du chargement: {e}", severity="error")

    def _refresh_table(self, passwords):
        table = self.query_one("#passwords-table")
        table.clear()

        table.add_column("ID", width=4, hidden=True)
        table.add_column("URL", width=25)
        table.add_column("Identifiant", width=20)
        table.add_column("Mot de passe", width=15)
        table.add_column("Email", width=20)
        table.add_column("Telephone", width=12)
        table.add_column("Cree le", width=12)

        if not passwords:
            self.update_stats()
            return

        for pwd in passwords:
            display_password = "••••••••" if not self.show_passwords else pwd.password
            table.add_row(
                str(pwd.id),
                pwd.url[:25] if pwd.url else "",
                pwd.key[:20] if pwd.key else "",
                display_password[:15],
                (pwd.email or "")[:20],
                (pwd.phone or "")[:12],
                str(pwd.date_added)[:12] if pwd.date_added else "",
            )

        self.update_stats()

    def update_stats(self):
        stats = self.query_one("#stats-text")
        stats.update(f"📊 {len(self.passwords)} mot(s) de passe enregistre(s)")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            query = event.value.strip()
            if len(query) >= 2:
                self.load_passwords(query)
            elif query == "":
                self.load_passwords()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            query = event.value.strip()
            self.load_passwords(query)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "show-all-btn":
            self.load_passwords()
            self.query_one("#search-input").value = ""
        elif event.button.id == "clear-search-btn":
            self.query_one("#search-input").value = ""
            self.load_passwords()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()
        elif event.key == "ctrl+q":
            self.action_logout()

    def action_toggle_passwords(self):
        self.show_passwords = not self.show_passwords
        self._refresh_table(self.passwords)

    def action_copy_password(self):
        table = self.query_one("#passwords-table")
        cursor_row = table.cursor_row

        if cursor_row < len(self.passwords) and cursor_row >= 0:
            password = self.passwords[cursor_row]
            self.app.set_clipboard(password.password)
            self.notify(
                "✓ Mot de passe copie dans le presse-papier!", severity="success"
            )
        else:
            self.notify("Veuillez selectionner un mot de passe",
                        severity="warning")

    def action_add_password(self):
        self.app.push_screen(AddPasswordScreen(self.user))

    def action_edit_password(self):
        table = self.query_one("#passwords-table")
        cursor_row = table.cursor_row

        if cursor_row < len(self.passwords) and cursor_row >= 0:
            password = self.passwords[cursor_row]
            self.app.push_screen(EditPasswordScreen(self.user, password))
        else:
            self.notify(
                "Veuillez selectionner un mot de passe a modifier", severity="warning"
            )

    def action_delete_password(self):
        table = self.query_one("#passwords-table")
        cursor_row = table.cursor_row

        if cursor_row < len(self.passwords) and cursor_row >= 0:
            password = self.passwords[cursor_row]
            self.app.push_screen(DeleteConfirmScreen(self.user, password))
        else:
            self.notify(
                "Veuillez selectionner un mot de passe a supprimer", severity="warning"
            )

    def action_logout(self):
        self.app.current_user = None
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


class AddPasswordScreen(Screen):
    """Ecran d'ajout d'un nouveau mot de passe"""

    CSS = """
    AddPasswordScreen {
        align: center middle;
    }
    
    #add-container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    
    #title {
        content-align: center;
        margin-bottom: 1;
    }
    
    .input-label {
        margin-bottom: 0;
        color: $text-muted;
    }
    
    #message {
        margin-bottom: 1;
    }
    
    .button-row {
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annuler", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def __init__(self, user: User):
        super().__init__()
        self.user = user

    def compose(self) -> ComposeResult:
        yield Container(
            Panel(
                Vertical(
                    Static(
                        Text(
                            " AJOUTER UN MOT DE PASSE ",
                            justify="center",
                            style="bold cyan",
                        ),
                        id="title",
                    ),
                    Label("URL / Site web:", classes="input-label"),
                    Input(id="url-input", placeholder="https://exemple.com"),
                    Label("Description (optionnel):", classes="input-label"),
                    Input(id="description-input",
                          placeholder="Description du compte"),
                    Label("Identifiant:", classes="input-label"),
                    Input(id="key-input", placeholder="Nom d'utilisateur ou email"),
                    Label("Mot de passe:", classes="input-label"),
                    Input(
                        id="password-input", password=True, placeholder="Mot de passe"
                    ),
                    Horizontal(
                        Button(
                            "Generer",
                            id="generate-btn",
                            variant="default",
                            size="small",
                        ),
                        Button(
                            "Afficher", id="show-btn", variant="default", size="small"
                        ),
                    ),
                    Label("Adresse e-mail (optionnel):",
                          classes="input-label"),
                    Input(id="email-input", placeholder="email@exemple.com"),
                    Label("Telephone (optionnel):", classes="input-label"),
                    Input(id="phone-input", placeholder="+33 6 00 00 00 00"),
                    Static("", id="message"),
                    Horizontal(
                        Button("Enregistrer", id="save-btn",
                               variant="primary"),
                        Button("Annuler", id="cancel-btn",
                               variant="default"),
                        classes="button-row",
                    ),
                ),
                title="[bold]NOUVEAU MOT DE PASSE[/]",
                border_style="green",
            ),
            id="add-container",
        )

    def on_mount(self) -> None:
        self.query_one("#url-input").focus()
        self.show_password = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.save_password()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "generate-btn":
            self.generate_password()
        elif event.button.id == "show-btn":
            self.toggle_password()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()
        elif event.key == "escape":
            self.app.pop_screen()

    def toggle_password(self):
        password_input = self.query_one("#password-input")
        self.show_password = not self.show_password
        password_input.password = not self.show_password
        self.query_one("#show-btn").label = (
            "Masquer" if self.show_password else "Afficher"
        )

    def generate_password(self):
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%&*" for c in password)
            ):
                break

        self.query_one("#password-input").value = password

    def save_password(self):
        url = self.query_one("#url-input").value.strip()
        description = self.query_one(
            "#description-input").value.strip() or None
        key = self.query_one("#key-input").value.strip()
        password = self.query_one("#password-input").value
        email = self.query_one("#email-input").value.strip() or None
        phone = self.query_one("#phone-input").value.strip() or None
        message_widget = self.query_one("#message")

        if not url or not key or not password:
            message_widget.update(
                "[error]✗ Les champs URL, Identifiant et Mot de passe sont requis[/]"
            )
            return

        try:
            Password.create(
                user_id=self.user.id,
                url=url,
                description=description,
                key=key,
                password=password,
                email=email,
                phone=phone,
            )
            message_widget.update(
                "[success]✓ Mot de passe ajoute avec succes![/]")
            self.notify("Mot de passe ajoute avec succes!", severity="success")
            self.app.pop_screen()
            # Rafraichir le dashboard
            for screen in self.app.screen_stack:
                if isinstance(screen, DashboardScreen):
                    screen.load_passwords()
                    break
        except Exception as e:
            message_widget.update(f"[error]✗ Erreur: {e}[/]")

    def action_cancel(self):
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


class EditPasswordScreen(Screen):
    """Ecran de modification d'un mot de passe"""

    CSS = """
    EditPasswordScreen {
        align: center middle;
    }
    
    #edit-container {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    
    #title {
        content-align: center;
        margin-bottom: 1;
    }
    
    .input-label {
        margin-bottom: 0;
        color: $text-muted;
    }
    
    #message {
        margin-bottom: 1;
    }
    
    .button-row {
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annuler", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def __init__(self, user: User, password: Password):
        super().__init__()
        self.user = user
        self.password = password

    def compose(self) -> ComposeResult:
        yield Container(
            Panel(
                Vertical(
                    Static(
                        Text(
                            " MODIFIER UN MOT DE PASSE ",
                            justify="center",
                            style="bold cyan",
                        ),
                        id="title",
                    ),
                    Static(f"URL: {self.password.url}", classes="input-label"),
                    Label("Nouvelle description:", classes="input-label"),
                    Input(
                        id="description-input",
                        value=self.password.description or "",
                        placeholder="Description du compte",
                    ),
                    Label("Nouvelle cle:", classes="input-label"),
                    Input(
                        id="key-input",
                        value=self.password.key or "",
                        placeholder="Nom d'utilisateur",
                    ),
                    Label("Nouveau mot de passe:", classes="input-label"),
                    Input(
                        id="password-input",
                        password=True,
                        value=self.password.password or "",
                        placeholder="Mot de passe",
                    ),
                    Horizontal(
                        Button(
                            "Generer",
                            id="generate-btn",
                            variant="default",
                            size="small",
                        ),
                        Button(
                            "Afficher", id="show-btn", variant="default", size="small"
                        ),
                    ),
                    Static("", id="message"),
                    Horizontal(
                        Button("Enregistrer", id="save-btn",
                               variant="primary"),
                        Button("Annuler", id="cancel-btn",
                               variant="default"),
                        classes="button-row",
                    ),
                ),
                title="[bold]MODIFICATION[/]",
                border_style="yellow",
            ),
            id="edit-container",
        )

    def on_mount(self) -> None:
        self.show_password = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.save_password()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "generate-btn":
            self.generate_password()
        elif event.button.id == "show-btn":
            self.toggle_password()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()
        elif event.key == "escape":
            self.app.pop_screen()

    def toggle_password(self):
        password_input = self.query_one("#password-input")
        self.show_password = not self.show_password
        password_input.password = not self.show_password
        self.query_one("#show-btn").label = (
            "Masquer" if self.show_password else "Afficher"
        )

    def generate_password(self):
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(16))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%&*" for c in password)
            ):
                break

        self.query_one("#password-input").value = password

    def save_password(self):
        description = self.query_one(
            "#description-input").value.strip() or None
        key = self.query_one("#key-input").value.strip()
        password = self.query_one("#password-input").value
        message_widget = self.query_one("#message")

        if not key or not password:
            message_widget.update(
                "[error]✗ Les champs Cle et Mot de passe sont requis[/]"
            )
            return

        try:
            self.password.update(description=description,
                                 key=key, password=password)
            message_widget.update(
                "[success]✓ Mot de passe modifie avec succes![/]")
            self.notify("Mot de passe modifie avec succes!",
                        severity="success")
            self.app.pop_screen()
            # Rafraichir le dashboard
            for screen in self.screen_stack:
                if isinstance(screen, DashboardScreen):
                    screen.load_passwords()
                    break
        except Exception as e:
            message_widget.update(f"[error]✗ Erreur: {e}[/]")

    def action_cancel(self):
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


class DeleteConfirmScreen(Screen):
    """Ecran de confirmation de suppression"""

    CSS = """
    DeleteConfirmScreen {
        align: center middle;
    }
    
    #confirm-container {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 2;
    }
    
    #warning-icon {
        content-align: center;
        margin-bottom: 1;
    }
    
    .button-row {
        margin-top: 1;
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annuler", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def __init__(self, user: User, password: Password):
        super().__init__()
        self.user = user
        self.password = password

    def compose(self) -> ComposeResult:
        yield Container(
            Panel(
                Vertical(
                    Static("⚠️", id="warning-icon", style="bold yellow"),
                    Static(
                        "Etes-vous sur de vouloir supprimer ce mot de passe ?",
                        justify="center",
                    ),
                    Static(
                        f"[bold]URL:[/] {self.password.url}", justify="center"),
                    Static(
                        f"[bold]Identifiant:[/] {self.password.key}", justify="center"
                    ),
                    Static("", justify="center"),
                    Static(
                        "Cette action est irreversible.",
                        style="italic",
                        justify="center",
                    ),
                    Horizontal(
                        Button("Supprimer", id="confirm-btn", variant="error"),
                        Button("Annuler", id="cancel-btn",
                               variant="default"),
                        classes="button-row",
                    ),
                ),
                title="[bold]CONFIRMATION DE SUPPRESSION[/]",
                border_style="red",
            ),
            id="confirm-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-btn":
            try:
                Password.delete_by_id(self.password.id)
                self.notify("Mot de passe supprime avec succes!",
                            severity="success")
                self.app.pop_screen()
                # Rafraichir le dashboard
                for screen in self.app.screen_stack:
                    if isinstance(screen, DashboardScreen):
                        screen.load_passwords()
                        break
            except Exception as e:
                self.notify(
                    f"Erreur lors de la suppression: {e}", severity="error")
        else:
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()
        elif event.key == "escape":
            self.app.pop_screen()

    def action_cancel(self):
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


class AboutScreen(Screen):
    """Ecran A propos"""

    CSS = """
    AboutScreen {
        align: center middle;
    }
    
    #about-container {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Fermer", show=False),
        Binding("ctrl+c", "quit", "Quitter", show=False),
    ]

    def compose(self) -> ComposeResult:
        from pg import __version__, __author__, __email__, __license__, __project_page__

        yield Container(
            Panel(
                Vertical(
                    Static(
                        "🔐 GESTIONNAIRE DE MOTS DE PASSE",
                        justify="center",
                        style="bold cyan",
                    ),
                    Static(f"Version: {__version__}", justify="center"),
                    Static("", justify="center"),
                    Static(
                        "Application securisee de gestion de mots de passe",
                        justify="center",
                        style="italic",
                    ),
                    Static("", justify="center"),
                    Static(f"Developpe par: {__author__}", justify="center"),
                    Static(f"Email: {__email__}", justify="center"),
                    Static(
                        f"Page du projet: {__project_page__}", justify="center"),
                    Static(f"Licence: {__license__}", justify="center"),
                    Horizontal(
                        Button("Fermer", id="close-btn", variant="primary"),
                        classes="button-row",
                    ),
                ),
                title="[bold]A PROPOS[/]",
                border_style="cyan",
            ),
            id="about-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            self.app.pop_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+c":
            self.app.exit()
        elif event.key == "escape":
            self.app.pop_screen()

    def action_close(self):
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()


class PasswordManagerApp(App):
    """Application principale du gestionnaire de mots de passe TUI"""

    CSS = """
    Screen {
        background: #1a1a2e;
        color: #eaeaea;
    }
    
    Panel {
        border: solid #3b82f6;
    }
    
    Button {
        margin: 1;
        padding: 0 2;
    }
    
    Button:focus {
        border: tall #f59e0b;
    }
    
    Input {
        border: tall #374151;
        background: #1f2937;
        color: #eaeaea;
    }
    
    Input:focus {
        border: tall #3b82f6;
        background: #374151;
    }
    
    DataTable {
        border: solid #374151;
        background: #1f2937;
    }
    
    Label {
        color: #9ca3af;
    }
    
    .status-bar {
        color: #6b7280;
    }
    
    .clickable:hover {
        color: #3b82f6;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quitter"),
        ("ctrl+q", "logout", "Deconnexion"),
        ("f1", "add_password", "Ajouter"),
        ("f5", "toggle_passwords", "Afficher/Masquer"),
    ]

    current_user = reactive(None)

    def __init__(self):
        super().__init__()
        self.current_user = None
        self.title = " Gestionnaire de Mots de Passe "

    def on_mount(self) -> None:
        self.push_screen(LoginScreen())

    def action_quit(self) -> None:
        self.exit()

    def action_logout(self) -> None:
        self.current_user = None
        for _ in range(len(self.screen_stack) - 1):
            self.pop_screen()

    def action_add_password(self):
        for screen in self.screen_stack:
            if isinstance(screen, DashboardScreen):
                screen.action_add_password()
                break

    def action_toggle_passwords(self):
        for screen in self.screen_stack:
            if isinstance(screen, DashboardScreen):
                screen.action_toggle_passwords()
                break


if __name__ == "__main__":
    app = PasswordManagerApp()
    app.run()
