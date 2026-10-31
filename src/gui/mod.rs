//! Interface graphique.

mod theme;

use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::time::{Duration, Instant};

use eframe::egui;
use egui::{
    Align, Align2, Button, Color32, ColorImage, Context, CornerRadius, Frame, Key, Layout, Margin,
    Modal, Modifiers, Rect, Response, RichText, ScrollArea, Sense, Stroke, TextEdit, TextStyle,
    TextWrapMode, Ui, WidgetInfo, WidgetText, WidgetType, pos2, vec2,
};
use zeroize::Zeroizing;

use crate::IDLE_LOCK;
use crate::clipboard::SecretClipboard;
use crate::csv_io;
use crate::entry::{Entry, EntryFields};
use crate::error::{Error, Result};
use crate::generator::{DEFAULT_LENGTH, generate_password};
use crate::mcp::{self, McpServer};
use crate::store::{Store, validate_master_password, validate_username};
use crate::workspace::Workspace;
use theme::{icon, palette};

const TICK: Duration = Duration::from_secs(1);
const MESSAGE_LIFETIME: Duration = Duration::from_secs(6);
const LOGIN_CARD_WIDTH: f32 = 340.0;
const LOGO_SIZE: f32 = 40.0;
const MENU_WIDTH: f32 = 220.0;
const LIST_ROW_HEIGHT: f32 = 48.0;
const CONTROL_HEIGHT: f32 = 32.0;
// Bouton de verrouillage, libellé et champ de recherche.
const TITLE_RESERVED_WIDTH: f32 = 350.0;
const DETAIL_LABEL_WIDTH: f32 = 100.0;
// Marges de la carte (2 × 16) et bordure.
const DETAIL_CARD_CHROME: f32 = 34.0;
const DIALOG_WIDTH: f32 = 460.0;
const DIALOG_BUTTON_WIDTH: f32 = 130.0;
const EMPTY_STATE_BUTTON_WIDTH: f32 = 170.0;
const PASSWORD_TOOLS_WIDTH: f32 = 141.0;
// Bouton « Parcourir… », marges du champ et espacement.
const BROWSE_BUTTON_WIDTH: f32 = 116.0;
// Marges de la fenêtre, boutons, message d'erreur et question d'abandon.
const DIALOG_CHROME_HEIGHT: f32 = 150.0;
const SEARCH_ID: &str = "search";
const COPIED_PASSWORD: &str = "Mot de passe copié (effacé dans 30 s)";
const COPIED_USERNAME: &str = "Identifiant copié (effacé dans 30 s)";

const ICON_PNG: &[u8] = include_bytes!("../../assets/icon.png");

pub fn run(store: Store) -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("PG")
            .with_inner_size([1040.0, 680.0])
            .with_min_inner_size([640.0, 480.0])
            .with_icon(
                eframe::icon_data::from_png_bytes(ICON_PNG).expect("icône intégrée invalide"),
            ),
        ..Default::default()
    };
    eframe::run_native(
        "PG",
        options,
        Box::new(|creation| {
            theme::apply(&creation.egui_ctx);
            Ok(Box::new(GuiApp::new(store)))
        }),
    )
}

#[derive(Default)]
struct LoginForm {
    username: String,
    password: Zeroizing<String>,
    confirm: Zeroizing<String>,
    registering: bool,
    attempted: bool,
}

enum Dialog {
    Entry {
        id: Option<String>,
        fields: EntryFields,
        revealed: bool,
    },
    Delete {
        id: String,
        site: String,
    },
    ChangeMaster {
        current: Zeroizing<String>,
        new: Zeroizing<String>,
        confirm: Zeroizing<String>,
    },
    Import {
        path: String,
    },
    Export {
        path: String,
    },
}

impl Dialog {
    fn new_entry() -> Self {
        Self::Entry {
            id: None,
            fields: EntryFields::default(),
            revealed: false,
        }
    }

    fn import() -> Self {
        Self::Import {
            path: String::new(),
        }
    }

    fn delete(entry: &Entry) -> Self {
        Self::Delete {
            id: entry.id.clone(),
            site: entry.fields.url.clone(),
        }
    }
}

enum DialogAction {
    Keep,
    Close,
    Submit,
}

struct GuiApp {
    store: Store,
    clipboard: SecretClipboard,
    mcp: Option<McpServer>,
    workspace: Option<Workspace>,
    login: LoginForm,
    dialog: Option<Dialog>,
    search: String,
    revealed: bool,
    status: Option<(String, bool)>,
    status_expires: Option<Instant>,
    dialog_error: Option<String>,
    dialog_focused: bool,
    discard_prompt: bool,
    dialog_attempted: bool,
    file_picker: Option<Receiver<Option<PathBuf>>>,
    login_focus: bool,
    focus_search: bool,
    logo: Option<egui::TextureHandle>,
    last_activity: Instant,
}

impl GuiApp {
    fn new(store: Store) -> Self {
        // Au premier lancement, il n'y a rien à déverrouiller.
        let login = LoginForm {
            registering: !store.has_accounts().unwrap_or(true),
            ..LoginForm::default()
        };
        Self {
            store,
            clipboard: SecretClipboard::default(),
            mcp: None,
            workspace: None,
            login,
            dialog: None,
            search: String::new(),
            revealed: false,
            status: None,
            status_expires: None,
            dialog_error: None,
            dialog_focused: false,
            discard_prompt: false,
            dialog_attempted: false,
            file_picker: None,
            login_focus: true,
            focus_search: false,
            logo: None,
            last_activity: Instant::now(),
        }
    }

    fn set_info(&mut self, message: impl Into<String>) {
        self.status = Some((message.into(), false));
        self.status_expires = Some(Instant::now() + MESSAGE_LIFETIME);
    }

    fn set_error(&mut self, error: impl ToString) {
        self.status = Some((error.to_string(), true));
        self.status_expires = None;
    }

    fn lock(&mut self) {
        self.workspace = None;
        self.mcp = None;
        self.dialog = None;
        self.close_dialog();
        self.search.clear();
        self.revealed = false;
        self.status = None;
        self.login = LoginForm::default();
        self.login_focus = true;
        self.clipboard.clear();
    }

    fn ui(&mut self, ctx: &Context) {
        ctx.request_repaint_after(TICK);
        if self.clipboard.tick() {
            self.set_info("Presse-papiers effacé");
        }
        if self.status_expires.is_some_and(|at| Instant::now() >= at) {
            self.status = None;
            self.status_expires = None;
        }
        if ctx.input(|input| !input.events.is_empty()) {
            self.last_activity = Instant::now();
        }
        if self.workspace.is_some() && self.last_activity.elapsed() >= IDLE_LOCK {
            self.lock();
            self.set_info("Coffre verrouillé après 5 minutes d'inactivité");
            // L'utilisateur était absent : le message doit l'attendre.
            self.status_expires = None;
        }
        // Après le verrouillage, et sans compter comme une activité de l'utilisateur.
        if let Some(server) = &self.mcp {
            let clipboard = &mut self.clipboard;
            let notices =
                server.handle_pending(self.workspace.as_ref(), |text| clipboard.copy(text));
            for notice in notices {
                self.set_info(notice);
            }
        }

        if self.workspace.is_some() {
            self.vault_ui(ctx);
        } else {
            self.login_ui(ctx);
        }
    }

    fn login_ui(&mut self, ctx: &Context) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.vertical_centered(|ui| {
                ui.add_space((ui.available_height() * 0.5 - 200.0).max(16.0));
                card(ui).inner_margin(Margin::same(24)).show(ui, |ui| {
                    ui.set_width(LOGIN_CARD_WIDTH);
                    ui.with_layout(Layout::top_down(Align::Min), |ui| {
                        self.login_form_ui(ui);
                    });
                });
            });
        });
    }

    fn login_form_ui(&mut self, ui: &mut Ui) {
        let registering = self.login.registering;
        let logo = self.logo.get_or_insert_with(|| load_logo(ui.ctx())).id();
        ui.horizontal(|ui| {
            ui.add(egui::Image::new((logo, vec2(LOGO_SIZE, LOGO_SIZE))));
            ui.label(RichText::new("PG").heading().size(28.0));
        });
        ui.label(
            RichText::new(if registering {
                "Créer un compte protégé par un mot de passe maître"
            } else {
                "Déverrouiller votre coffre"
            })
            .color(palette(ui).secondary),
        );
        ui.add_space(12.0);
        let mut submitted = false;
        // Les règles de création ne concernent pas la connexion à un compte existant.
        let [username_error, password_error, confirm_error] = if registering {
            registration_errors(&self.login)
        } else {
            [None, None, None]
        };
        let mut form = FormFields {
            attempted: self.login.attempted,
            focus: std::mem::take(&mut self.login_focus),
        };
        let username = text_input(ui, "Compte", &mut self.login.username);
        let username_entered = form.check(
            ui,
            &username,
            !self.login.username.is_empty(),
            username_error.as_deref(),
        );
        let password = secret_input(ui, "Mot de passe maître", &mut self.login.password);
        submitted |= form.check(
            ui,
            &password,
            !self.login.password.is_empty(),
            password_error.as_deref(),
        );
        if username_entered {
            if self.login.password.is_empty() {
                password.request_focus();
            } else {
                submitted = true;
            }
        }
        if registering {
            let confirm = secret_input(ui, "Confirmer", &mut self.login.confirm);
            submitted |= form.check(
                ui,
                &confirm,
                !self.login.confirm.is_empty(),
                confirm_error.as_deref(),
            );
        }
        ui.add_space(4.0);
        submitted |= primary_button(
            ui,
            if registering {
                "Créer le compte"
            } else {
                "Déverrouiller"
            },
            ui.available_width(),
        )
        .clicked();
        ui.vertical_centered(|ui| {
            let other = if registering {
                "J'ai déjà un compte"
            } else {
                "Créer un compte"
            };
            if ui.link(other).clicked() {
                self.login.registering = !registering;
                self.login.attempted = false;
                self.login_focus = true;
                self.status = None;
            }
        });
        if submitted {
            self.submit_login();
        }
        info_bar(ui, self.status.as_ref());
    }

    fn submit_login(&mut self) {
        if self.login.registering && registration_errors(&self.login).iter().any(Option::is_some) {
            self.login.attempted = true;
            self.login_focus = true;
            return;
        }
        let form = &self.login;
        let session = if form.registering {
            self.store.register(&form.username, &form.password)
        } else {
            self.store.login(&form.username, &form.password)
        };
        match session.and_then(|session| Workspace::open(&self.store, session)) {
            Ok(workspace) => {
                self.workspace = Some(workspace);
                self.login = LoginForm::default();
                self.status = None;
                self.last_activity = Instant::now();
                self.focus_search = true;
            }
            Err(error) => self.set_error(error),
        }
    }

    /// Le parcours principal se fait depuis la recherche : les raccourcis y restent actifs,
    /// sauf quand la touche a déjà un sens pour le texte saisi ou sélectionné.
    fn shortcuts(&mut self, ctx: &Context) {
        if self.dialog.is_some() || egui::Popup::is_any_open(ctx) {
            return;
        }
        let search_id = egui::Id::new(SEARCH_ID);
        let search_focused = ctx.memory(|memory| memory.has_focus(search_id));
        let search_selected = search_focused
            && TextEdit::load_state(ctx, search_id)
                .and_then(|state| state.cursor.char_range())
                .is_some_and(|range| !range.is_empty());
        let label_selected = egui::text_selection::LabelSelectionState::load(ctx).has_selection();
        let can_delete = !search_focused || self.search.is_empty();
        // egui-winit transforme Ctrl+C en `Event::Copy`, sans événement de touche.
        let copy_password = !search_selected
            && !label_selected
            && ctx.input(|input| {
                input
                    .events
                    .iter()
                    .any(|event| matches!(event, egui::Event::Copy))
            });
        let (copy_username, add, delete) = ctx.input_mut(|input| {
            (
                input.consume_key(Modifiers::COMMAND, Key::B),
                input.consume_key(Modifiers::COMMAND, Key::N),
                can_delete && input.consume_key(Modifiers::NONE, Key::Delete),
            )
        });
        if add {
            self.dialog = Some(Dialog::new_entry());
            return;
        }
        let Some(entry) = self
            .workspace
            .as_ref()
            .and_then(|workspace| workspace.selected())
            .cloned()
        else {
            return;
        };
        if copy_password {
            self.copy(&entry.fields.password, COPIED_PASSWORD);
        }
        if copy_username {
            self.copy(&entry.fields.username, COPIED_USERNAME);
        }
        if delete {
            self.dialog = Some(Dialog::delete(&entry));
        }
    }

    fn vault_ui(&mut self, ctx: &Context) {
        self.shortcuts(ctx);
        let pane = |top: i8, bottom: i8| {
            Frame::new()
                .fill(ctx.style().visuals.panel_fill)
                .inner_margin(Margin {
                    left: 16,
                    right: 16,
                    top,
                    bottom,
                })
        };
        egui::TopBottomPanel::top("toolbar")
            .frame(pane(12, 8))
            .show_separator_line(false)
            .show(ctx, |ui| self.toolbar_ui(ui));
        if self.status.is_some() {
            egui::TopBottomPanel::bottom("status")
                .frame(pane(0, 12))
                .show_separator_line(false)
                .show(ctx, |ui| info_bar(ui, self.status.as_ref()));
        }
        egui::SidePanel::left("entries")
            // La poignée, invisible sans ligne de séparation, serait une étape de tabulation vide.
            .resizable(false)
            .default_width(380.0)
            .frame(pane(0, 12))
            .show_separator_line(false)
            .show(ctx, |ui| self.list_ui(ui));
        egui::CentralPanel::default()
            .frame(pane(0, 12))
            .show(ctx, |ui| self.detail_ui(ui));
        self.dialog_ui(ctx);
    }

    fn toolbar_ui(&mut self, ui: &mut Ui) {
        let mut lock = false;
        ui.horizontal(|ui| {
            if let Some(workspace) = &mut self.workspace {
                ui.scope(|ui| {
                    // Un nom très long est tronqué plutôt que de pousser la recherche hors de la fenêtre.
                    ui.set_max_width((ui.available_width() - TITLE_RESERVED_WIDTH).max(80.0));
                    ui.add(
                        egui::Label::new(RichText::new(workspace.session.username()).heading())
                            .truncate(),
                    );
                });
                lock = icon_button(ui, icon::LOCK, "Verrouiller", "Verrouiller").clicked();
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    let search = ui
                        .add(
                            TextEdit::singleline(&mut self.search)
                                .id(egui::Id::new(SEARCH_ID))
                                .desired_width(220.0)
                                .margin(vec2(10.0, 6.0)),
                        )
                        .on_hover_text("Ctrl+F");
                    let label = ui.label("Recherche");
                    let search = search.labelled_by(label.id);
                    if self.dialog.is_none()
                        && (std::mem::take(&mut self.focus_search)
                            || ui.input_mut(|input| input.consume_key(Modifiers::COMMAND, Key::F)))
                    {
                        search.request_focus();
                    }
                    if search.changed() {
                        workspace.set_query(&self.search);
                        self.revealed = false;
                    }
                });
            }
        });
        if lock {
            self.lock();
            return;
        }
        card(ui).inner_margin(Margin::same(4)).show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.horizontal_wrapped(|ui| {
                ui.spacing_mut().item_spacing.x = 4.0;
                if primary_command_button(ui, icon::ADD, "Ajouter")
                    .on_hover_text("Ctrl+N")
                    .clicked()
                {
                    self.dialog = Some(Dialog::new_entry());
                }
                self.more_menu_ui(ui);
                let (state, active) = if self.mcp.is_some() {
                    ("Accès pour assistants IA : activé", true)
                } else {
                    ("Accès pour assistants IA : désactivé", false)
                };
                if command_button(ui, icon::CONNECT, state, active)
                    .on_hover_text("Active ou désactive le serveur MCP local")
                    .clicked()
                {
                    let ctx = ui.ctx().clone();
                    let waker = Box::new(move || ctx.request_repaint());
                    match mcp::toggle(&mut self.mcp, &mut self.clipboard, waker) {
                        Ok(message) => self.set_info(message),
                        Err(error) => self.set_error(error),
                    }
                }
                if let Some(server) = &self.mcp
                    && command_button(ui, icon::COPY, "Copier le jeton d'accès", false)
                        .on_hover_text(server.url())
                        .clicked()
                {
                    let message = mcp::copy_token(server, &mut self.clipboard);
                    self.set_info(message);
                }
            });
        });
    }

    fn more_menu_ui(&mut self, ui: &mut Ui) {
        let more = command_button(ui, icon::MORE, "Plus", false);
        // Le clavier entre dans le menu ; à la souris, le contour de focus serait du bruit.
        let opened_by_keyboard = more.clicked()
            && ui.input(|input| input.key_pressed(Key::Enter) || input.key_pressed(Key::Space));
        let frame = Frame::popup(ui.style()).inner_margin(Margin::same(4));
        egui::Popup::menu(&more).frame(frame).show(|ui| {
            ui.spacing_mut().item_spacing.y = 0.0;
            let import = menu_item(ui, icon::IMPORT, "Importer");
            if opened_by_keyboard {
                import.request_focus();
            }
            if import.clicked() {
                self.dialog = Some(Dialog::import());
            }
            if menu_item(ui, icon::EXPORT, "Exporter").clicked() {
                self.dialog = Some(Dialog::Export {
                    path: String::new(),
                });
            }
            if menu_item(ui, icon::KEY, "Mot de passe maître").clicked() {
                self.dialog = Some(Dialog::ChangeMaster {
                    current: Zeroizing::default(),
                    new: Zeroizing::default(),
                    confirm: Zeroizing::default(),
                });
            }
        });
    }

    fn list_ui(&mut self, ui: &mut Ui) {
        let Some(workspace) = &mut self.workspace else {
            return;
        };
        let previous = workspace.selected_position();
        if self.dialog.is_none() && !egui::Popup::is_any_open(ui.ctx()) {
            ui.input_mut(|input| {
                if input.consume_key(Modifiers::NONE, Key::ArrowUp) {
                    workspace.move_selection(-1);
                }
                if input.consume_key(Modifiers::NONE, Key::ArrowDown) {
                    workspace.move_selection(1);
                }
            });
        }
        let selected = workspace.selected_position();
        let moved = selected != previous;
        if moved {
            self.revealed = false;
        }
        let mut clicked = None;
        ui.label(
            RichText::new(entry_count(workspace.visible().count()))
                .small()
                .color(palette(ui).secondary),
        );
        ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            // Lignes jointives : toute la largeur est cliquable, sans trou entre deux entrées.
            ui.spacing_mut().item_spacing.y = 0.0;
            for (position, entry) in workspace.visible().enumerate() {
                let response = entry_row(
                    ui,
                    &entry.fields.url,
                    &entry.fields.username,
                    position == selected,
                );
                if response.clicked() {
                    clicked = Some(position);
                }
                if moved && position == selected {
                    response.scroll_to_me(None);
                }
            }
        });
        if let Some(position) = clicked {
            workspace.select(position);
            self.revealed = false;
        }
    }

    fn detail_ui(&mut self, ui: &mut Ui) {
        let Some(entry) = self
            .workspace
            .as_ref()
            .and_then(|workspace| workspace.selected())
            .cloned()
        else {
            self.empty_state_ui(ui);
            return;
        };
        let fields = &entry.fields;
        let revealed = self.revealed;
        ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    ui.spacing_mut().item_spacing.x = 4.0;
                    // Disposition de droite à gauche : le dernier ajouté s'affiche en premier.
                    if danger_command_button(ui, icon::DELETE, "Supprimer")
                        .on_hover_text("Suppr")
                        .clicked()
                    {
                        self.dialog = Some(Dialog::delete(&entry));
                    }
                    if command_button(ui, icon::EDIT, "Modifier", false).clicked() {
                        self.dialog = Some(Dialog::Entry {
                            id: Some(entry.id.clone()),
                            fields: fields.clone(),
                            revealed: false,
                        });
                    }
                    ui.with_layout(Layout::left_to_right(Align::Center), |ui| {
                        ui.add(egui::Label::new(RichText::new(&fields.url).heading()).truncate());
                    });
                });
            });
            ui.add_space(4.0);
            // La carte occupe toute la hauteur restante.
            let card_height = ui.available_height() - DETAIL_CARD_CHROME;
            card(ui).show(ui, |ui| {
                ui.set_width(ui.available_width());
                ui.set_min_height(card_height);
                ui.spacing_mut().item_spacing.y = 12.0;
                detail_line(
                    ui,
                    "Identifiant",
                    |ui| {
                        let copy = icon_button(
                            ui,
                            icon::COPY,
                            "Copier l'identifiant",
                            "Copier l'identifiant (Ctrl+B)",
                        );
                        if copy.clicked() {
                            self.copy(&fields.username, COPIED_USERNAME);
                        }
                    },
                    |ui| detail_value(ui, &fields.username),
                );
                detail_line(
                    ui,
                    "Mot de passe",
                    |ui| {
                        // Disposition de droite à gauche : le dernier ajouté s'affiche en premier.
                        let accent = palette(ui).accent;
                        let copy = icon_button_with(
                            ui,
                            icon::COPY,
                            "Copier le mot de passe",
                            "Copier le mot de passe (Ctrl+C)",
                            accent,
                        );
                        if copy.clicked() {
                            self.copy(&fields.password, COPIED_PASSWORD);
                        }
                        let (glyph, label) = reveal_control(revealed);
                        if icon_button(ui, glyph, label, label).clicked() {
                            self.revealed = !revealed;
                        }
                    },
                    |ui| {
                        ui.add(
                            egui::Label::new(
                                RichText::new(if revealed {
                                    fields.password.as_str()
                                } else {
                                    "••••••••"
                                })
                                .monospace(),
                            )
                            .wrap(),
                        );
                    },
                );
                for (label, value) in [
                    ("E-mail", fields.email.as_str()),
                    ("Téléphone", fields.phone.as_str()),
                    ("Notes", fields.notes.as_str()),
                    ("Créée le", &local_date(&entry.created_at)),
                    ("Modifiée le", &local_date(&entry.updated_at)),
                ] {
                    // Un champ vide n'apporte rien à l'écran de détail.
                    if !value.is_empty() {
                        detail_line(ui, label, |_| {}, |ui| detail_value(ui, value));
                    }
                }
            });
        });
    }

    fn empty_state_ui(&mut self, ui: &mut Ui) {
        let vault_is_empty = self
            .workspace
            .as_ref()
            .is_none_or(|workspace| workspace.all_entries().is_empty());
        let secondary = palette(ui).secondary;
        ui.add_space(48.0);
        ui.vertical_centered(|ui| {
            if !vault_is_empty {
                let message = format!("Aucun résultat pour « {} »", self.search.trim());
                ui.label(RichText::new(message).color(secondary));
                return;
            }
            ui.heading("Votre coffre est vide");
            ui.label(
                RichText::new("Ajoutez votre première entrée ou importez un fichier CSV.")
                    .color(secondary),
            );
            ui.add_space(8.0);
            if primary_button(ui, "Ajouter une entrée", EMPTY_STATE_BUTTON_WIDTH).clicked() {
                self.dialog = Some(Dialog::new_entry());
            }
            let import = ui.add_sized(
                vec2(EMPTY_STATE_BUTTON_WIDTH, CONTROL_HEIGHT),
                Button::new("Importer un CSV"),
            );
            if import.clicked() {
                self.dialog = Some(Dialog::import());
            }
        });
    }

    fn copy(&mut self, text: &str, message: &str) {
        match self.clipboard.copy(text) {
            Ok(()) => self.set_info(message),
            Err(error) => self.set_error(format!("Presse-papiers indisponible : {error}")),
        }
    }

    /// Une saisie en cours n'est jamais perdue sans confirmation : le clic hors du dialogue ne
    /// le ferme pas, et Échap demande confirmation si le formulaire a changé.
    fn dialog_ui(&mut self, ctx: &Context) {
        let Some(mut dialog) = self.dialog.take() else {
            return;
        };
        self.poll_file_picker(&mut dialog);
        let focus_first = !std::mem::replace(&mut self.dialog_focused, true);
        if ctx.input(|input| input.key_pressed(Key::Escape)) {
            if self.discard_prompt {
                self.discard_prompt = false;
                self.dialog_focused = false;
            } else if self.dialog_is_dirty(&dialog) {
                self.discard_prompt = true;
            } else {
                self.close_dialog();
                return;
            }
        }
        let error = self.dialog_error.clone();
        let discard_prompt = self.discard_prompt;
        let mut keep_editing = false;
        let attempted = self.dialog_attempted;
        let picking = self.file_picker.is_some();
        let mut browse = false;
        let modal = Modal::new(egui::Id::new("dialog")).show(ctx, |ui| {
            ui.set_width(DIALOG_WIDTH);
            let mut form = FormFields {
                attempted,
                focus: focus_first,
            };
            // Sur une petite fenêtre, le formulaire défile et les boutons restent visibles.
            let max_height = ui.ctx().screen_rect().height() - DIALOG_CHROME_HEIGHT;
            let mut action = ScrollArea::vertical()
                .max_height(max_height)
                .auto_shrink([false, true])
                .show(ui, |ui| {
                    dialog_content(ui, &mut dialog, &mut form, picking, &mut browse)
                })
                .inner;
            if let Some(error) = &error {
                ui.label(RichText::new(error).color(palette(ui).danger));
            }
            ui.add_space(8.0);
            if discard_prompt {
                ui.label("Abandonner les modifications ?");
            }
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                if discard_prompt {
                    if secondary_button(ui, "Continuer la saisie").clicked() {
                        keep_editing = true;
                    }
                    let danger = palette(ui).danger;
                    if filled_button(ui, "Abandonner", DIALOG_BUTTON_WIDTH, danger).clicked() {
                        action = DialogAction::Close;
                    }
                    return;
                }
                if secondary_button(ui, "Annuler").clicked() {
                    action = DialogAction::Close;
                }
                let submit = if matches!(dialog, Dialog::Delete { .. }) {
                    let danger = palette(ui).danger;
                    filled_button(ui, "Confirmer la suppression", DIALOG_BUTTON_WIDTH, danger)
                } else {
                    primary_button(ui, "Valider", DIALOG_BUTTON_WIDTH)
                };
                if submit.clicked() {
                    action = DialogAction::Submit;
                }
            });
            action
        });
        if keep_editing {
            self.discard_prompt = false;
            self.dialog_focused = false;
        }
        if browse {
            self.start_file_picker(ctx, &dialog);
        }
        match modal.inner {
            DialogAction::Keep => self.dialog = Some(dialog),
            DialogAction::Submit if !dialog_is_valid(&dialog) => {
                self.dialog_error = None;
                self.dialog_attempted = true;
                self.dialog_focused = false;
                self.dialog = Some(dialog);
            }
            DialogAction::Close => self.close_dialog(),
            DialogAction::Submit => match self.submit_dialog(&dialog) {
                Ok(message) => {
                    self.close_dialog();
                    self.set_info(message);
                }
                Err(error) => {
                    self.dialog_error = Some(error.to_string());
                    self.dialog_attempted = false;
                    self.dialog_focused = false;
                    self.discard_prompt = false;
                    self.dialog = Some(dialog);
                }
            },
        }
    }

    fn close_dialog(&mut self) {
        self.dialog_error = None;
        self.dialog_focused = false;
        self.discard_prompt = false;
        self.dialog_attempted = false;
        self.file_picker = None;
        self.focus_search = true;
    }

    /// La fenêtre de Windows tourne à part : l'interface continue de vivre, verrouillage
    /// automatique compris. Son résultat est ignoré si le dialogue a été fermé entre-temps.
    fn start_file_picker(&mut self, ctx: &Context, dialog: &Dialog) {
        let saving = matches!(dialog, Dialog::Export { .. });
        let (sender, receiver) = mpsc::channel();
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            let picker = rfd::FileDialog::new().add_filter("CSV", &["csv"]);
            let path = if saving {
                picker.set_file_name("pg-export.csv").save_file()
            } else {
                picker.pick_file()
            };
            let _ = sender.send(path);
            ctx.request_repaint();
        });
        self.file_picker = Some(receiver);
    }

    fn poll_file_picker(&mut self, dialog: &mut Dialog) {
        let Some(receiver) = &self.file_picker else {
            return;
        };
        match receiver.try_recv() {
            Err(TryRecvError::Empty) => {}
            Err(TryRecvError::Disconnected) => self.file_picker = None,
            Ok(picked) => {
                self.file_picker = None;
                if let (Some(picked), Dialog::Import { path } | Dialog::Export { path }) =
                    (picked, dialog)
                {
                    *path = picked.to_string_lossy().into_owned();
                }
            }
        }
    }

    fn dialog_is_dirty(&self, dialog: &Dialog) -> bool {
        match dialog {
            Dialog::Entry { id, fields, .. } => {
                let original = self
                    .workspace
                    .as_ref()
                    .and_then(|workspace| {
                        workspace
                            .all_entries()
                            .iter()
                            .find(|entry| Some(&entry.id) == id.as_ref())
                    })
                    .map(|entry| entry.fields.clone())
                    .unwrap_or_default();
                *fields != original
            }
            Dialog::Delete { .. } => false,
            Dialog::ChangeMaster {
                current,
                new,
                confirm,
            } => !(current.is_empty() && new.is_empty() && confirm.is_empty()),
            Dialog::Import { path } | Dialog::Export { path } => !path.is_empty(),
        }
    }

    fn submit_dialog(&mut self, dialog: &Dialog) -> Result<String> {
        let Some(workspace) = &mut self.workspace else {
            return Err(Error::InvalidCredentials);
        };
        let session = &workspace.session;
        let mut saved_id = None;
        let message = match dialog {
            Dialog::Entry { id, fields, .. } => {
                let entry = match id {
                    Some(id) => self.store.update(session, id, fields.clone())?,
                    None => self.store.add(session, fields.clone())?,
                };
                saved_id = Some(entry.id.clone());
                format!("Entrée enregistrée : {}", entry.fields.url)
            }
            Dialog::Delete { id, .. } => {
                self.store.delete(session, id)?;
                "Entrée supprimée".to_owned()
            }
            Dialog::ChangeMaster {
                current,
                new,
                confirm,
            } => {
                if **new != **confirm {
                    return Err(mismatch());
                }
                self.store.change_master_password(session, current, new)?;
                "Mot de passe maître modifié".to_owned()
            }
            Dialog::Import { path } => {
                let report = self
                    .store
                    .import(session, csv_io::import_from_file(Path::new(path))?)?;
                format!(
                    "{} entrée(s) importée(s), {} doublon(s) ignoré(s)",
                    report.imported, report.duplicates
                )
            }
            Dialog::Export { path } => {
                if Path::new(path).exists() {
                    return Err(Error::Validation(
                        "Ce fichier existe déjà : choisissez un autre nom".to_owned(),
                    ));
                }
                csv_io::export_to_file(workspace.all_entries(), Path::new(path))?;
                format!("Export EN CLAIR écrit dans {path}")
            }
        };
        workspace.reload(&self.store)?;
        if let Some(id) = saved_id {
            workspace.select_id(&id);
        }
        self.revealed = false;
        Ok(message)
    }
}

impl eframe::App for GuiApp {
    fn update(&mut self, ctx: &Context, _frame: &mut eframe::Frame) {
        self.ui(ctx);
    }
}

/// État partagé par les champs d'un formulaire : focus initial et affichage des erreurs.
struct FormFields {
    attempted: bool,
    focus: bool,
}

impl FormFields {
    /// Une erreur s'affiche après une tentative de validation, ou quand on quitte un champ rempli
    /// pour ne pas interrompre la saisie. Après une tentative, le focus va à la première erreur.
    /// Renvoie vrai si la touche Entrée vient de valider le champ.
    fn check(
        &mut self,
        ui: &mut Ui,
        response: &Response,
        filled: bool,
        error: Option<&str>,
    ) -> bool {
        if self.focus && (!self.attempted || error.is_some()) {
            response.request_focus();
            self.focus = false;
        }
        if let Some(error) = error
            && (self.attempted || (filled && !response.has_focus()))
        {
            ui.label(RichText::new(error).small().color(palette(ui).danger));
        }
        entered(response)
    }
}

fn master_errors(current: &str, new: &str, confirm: &str) -> [Option<String>; 3] {
    [
        current
            .is_empty()
            .then(|| "Le mot de passe actuel est obligatoire".to_owned()),
        validate_master_password(new)
            .err()
            .map(|error| error.to_string()),
        (new != confirm).then(|| mismatch().to_string()),
    ]
}

fn registration_errors(form: &LoginForm) -> [Option<String>; 3] {
    [
        validate_username(&form.username)
            .err()
            .map(|error| error.to_string()),
        validate_master_password(&form.password)
            .err()
            .map(|error| error.to_string()),
        (*form.password != *form.confirm).then(|| mismatch().to_string()),
    ]
}

fn path_error(path: &str) -> Option<&'static str> {
    path.trim().is_empty().then_some("Indiquez un fichier")
}

fn dialog_is_valid(dialog: &Dialog) -> bool {
    match dialog {
        Dialog::Entry { fields, .. } => fields.validate().is_ok(),
        Dialog::Delete { .. } => true,
        Dialog::ChangeMaster {
            current,
            new,
            confirm,
        } => master_errors(current, new, confirm)
            .iter()
            .all(Option::is_none),
        Dialog::Import { path } | Dialog::Export { path } => path_error(path).is_none(),
    }
}

fn dialog_content(
    ui: &mut Ui,
    dialog: &mut Dialog,
    form: &mut FormFields,
    picking: bool,
    browse: &mut bool,
) -> DialogAction {
    let mut submitted = false;
    match dialog {
        Dialog::Entry {
            id,
            fields,
            revealed,
        } => {
            ui.heading(if id.is_some() {
                "Modifier l'entrée"
            } else {
                "Nouvelle entrée"
            });
            ui.add_space(4.0);
            let error = fields.url_error();
            let site = required_input(ui, "Site", &mut fields.url);
            submitted |= form.check(ui, &site, !fields.url.is_empty(), error);
            let error = fields.username_error();
            let username = required_input(ui, "Identifiant", &mut fields.username);
            submitted |= form.check(ui, &username, !fields.username.is_empty(), error);
            let label = field_label(ui, "Mot de passe", true);
            let password = ui
                .horizontal(|ui| {
                    let password = ui
                        .add(
                            TextEdit::singleline(&mut fields.password)
                                .password(!*revealed)
                                .desired_width(ui.available_width() - PASSWORD_TOOLS_WIDTH)
                                .margin(vec2(10.0, 6.0)),
                        )
                        .labelled_by(label.id);
                    let (glyph, reveal_label) = reveal_control(*revealed);
                    if icon_button(ui, glyph, reveal_label, reveal_label).clicked() {
                        *revealed = !*revealed;
                    }
                    if ui.button("Générer").clicked() {
                        fields.password = generate_password(DEFAULT_LENGTH);
                        *revealed = true;
                    }
                    password
                })
                .inner;
            let error = fields.password_error();
            submitted |= form.check(ui, &password, !fields.password.is_empty(), error);
            let error = fields.email_error();
            let email = text_input(ui, "E-mail", &mut fields.email);
            submitted |= form.check(ui, &email, !fields.email.is_empty(), error);
            submitted |= entered(&text_input(ui, "Téléphone", &mut fields.phone));
            submitted |= entered(&text_input(ui, "Notes", &mut fields.notes));
            ui.label(
                RichText::new("* Champ obligatoire")
                    .small()
                    .color(palette(ui).secondary),
            );
        }
        Dialog::Delete { site, .. } => {
            ui.heading("Supprimer l'entrée");
            ui.label(format!("Supprimer définitivement {site} ?"));
        }
        Dialog::ChangeMaster {
            current,
            new,
            confirm,
        } => {
            ui.heading("Changer le mot de passe maître");
            ui.add_space(4.0);
            let [current_error, new_error, confirm_error] = master_errors(current, new, confirm);
            let field = secret_input(ui, "Actuel", current);
            submitted |= form.check(ui, &field, !current.is_empty(), current_error.as_deref());
            let field = secret_input(ui, "Nouveau", new);
            submitted |= form.check(ui, &field, !new.is_empty(), new_error.as_deref());
            let field = secret_input(ui, "Confirmer", confirm);
            submitted |= form.check(ui, &field, !confirm.is_empty(), confirm_error.as_deref());
        }
        Dialog::Import { path } => {
            ui.heading("Importer un CSV");
            ui.add_space(4.0);
            let error = path_error(path);
            let file = path_input(ui, path, picking, browse);
            submitted |= form.check(ui, &file, !path.is_empty(), error);
        }
        Dialog::Export { path } => {
            ui.heading("Exporter en CSV");
            ui.label(
                RichText::new(
                    "L'export est EN CLAIR : tout lecteur du fichier verra les mots de passe.",
                )
                .color(palette(ui).warning),
            );
            let error = path_error(path);
            let file = path_input(ui, path, picking, browse);
            submitted |= form.check(ui, &file, !path.is_empty(), error);
        }
    }
    if submitted {
        DialogAction::Submit
    } else {
        DialogAction::Keep
    }
}

fn reveal_control(revealed: bool) -> (char, &'static str) {
    if revealed {
        (icon::HIDE, "Masquer")
    } else {
        (icon::SHOW, "Afficher")
    }
}

fn load_logo(ctx: &Context) -> egui::TextureHandle {
    let icon = eframe::icon_data::from_png_bytes(ICON_PNG).expect("icône intégrée invalide");
    let size = [icon.width as usize, icon.height as usize];
    ctx.load_texture(
        "logo",
        ColorImage::from_rgba_unmultiplied(size, &icon.rgba),
        egui::TextureOptions::LINEAR,
    )
}

fn entry_count(count: usize) -> String {
    let plural = if count > 1 { "s" } else { "" };
    format!("{count} entrée{plural}")
}

fn card(ui: &Ui) -> Frame {
    let colors = palette(ui);
    Frame::new()
        .fill(colors.card)
        .stroke(Stroke::new(1.0_f32, colors.stroke))
        .corner_radius(CornerRadius::same(8))
        .inner_margin(Margin::same(16))
}

fn primary_button(ui: &mut Ui, label: &str, width: f32) -> Response {
    let accent = palette(ui).accent;
    filled_button(ui, label, width, accent)
}

fn filled_button(ui: &mut Ui, label: &str, width: f32, fill: Color32) -> Response {
    let on_fill = palette(ui).on_accent;
    ui.add_sized(
        vec2(width, CONTROL_HEIGHT),
        Button::new(RichText::new(label).color(on_fill))
            .fill(fill)
            .stroke(Stroke::NONE),
    )
}

fn secondary_button(ui: &mut Ui, label: &str) -> Response {
    ui.add_sized(
        vec2(DIALOG_BUTTON_WIDTH, CONTROL_HEIGHT),
        Button::new(label),
    )
}

#[derive(Clone, Copy)]
struct CommandColors {
    rest: Option<Color32>,
    hover: Color32,
    pressed: Color32,
    glyph: Color32,
    text: Color32,
    min_width: f32,
}

/// Bouton de barre de commandes : icône et texte, sans fond tant qu'il n'est pas survolé.
/// L'accent signale seulement un état actif.
fn command_button(ui: &mut Ui, glyph: char, label: &str, active: bool) -> Response {
    let colors = palette(ui);
    let foreground = if active { colors.accent } else { colors.text };
    let look = CommandColors {
        rest: active.then_some(colors.hover),
        hover: colors.hover,
        pressed: colors.pressed,
        glyph: foreground,
        text: foreground,
        min_width: 0.0,
    };
    styled_command_button(ui, glyph, label, look)
}

fn danger_command_button(ui: &mut Ui, glyph: char, label: &str) -> Response {
    let colors = palette(ui);
    let look = CommandColors {
        rest: None,
        hover: colors.hover,
        pressed: colors.pressed,
        glyph: colors.danger,
        text: colors.text,
        min_width: 0.0,
    };
    styled_command_button(ui, glyph, label, look)
}

fn primary_command_button(ui: &mut Ui, glyph: char, label: &str) -> Response {
    let colors = palette(ui);
    let look = CommandColors {
        rest: Some(colors.accent),
        hover: colors.accent.gamma_multiply(0.9),
        pressed: colors.accent.gamma_multiply(0.8),
        glyph: colors.on_accent,
        text: colors.on_accent,
        min_width: 0.0,
    };
    styled_command_button(ui, glyph, label, look)
}

fn menu_item(ui: &mut Ui, glyph: char, label: &str) -> Response {
    let colors = palette(ui);
    let look = CommandColors {
        rest: None,
        hover: colors.hover,
        pressed: colors.pressed,
        glyph: colors.text,
        text: colors.text,
        min_width: MENU_WIDTH,
    };
    styled_command_button(ui, glyph, label, look)
}

fn styled_command_button(ui: &mut Ui, glyph: char, label: &str, look: CommandColors) -> Response {
    let icon_font = theme::icon_font(ui, 16.0);
    let text = WidgetText::from(label).into_galley(
        ui,
        Some(TextWrapMode::Extend),
        f32::INFINITY,
        TextStyle::Button,
    );
    let icon_width = if icon_font.is_some() { 24.0 } else { 0.0 };
    let width = (text.size().x + icon_width + 20.0).max(look.min_width);
    let size = vec2(width, CONTROL_HEIGHT);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    response.widget_info(|| WidgetInfo::labeled(WidgetType::Button, ui.is_enabled(), label));
    if ui.is_rect_visible(rect) {
        let fill = if response.is_pointer_button_down_on() {
            Some(look.pressed)
        } else if response.hovered() {
            Some(look.hover)
        } else {
            look.rest
        };
        if let Some(fill) = fill {
            ui.painter().rect_filled(rect, 4.0, fill);
        }
        paint_focus(ui, &response, rect);
        let center_y = rect.center().y;
        if let Some(font) = icon_font {
            ui.painter().text(
                pos2(rect.left() + 10.0, center_y),
                Align2::LEFT_CENTER,
                glyph,
                font,
                look.glyph,
            );
        }
        let position = pos2(
            rect.left() + 10.0 + icon_width,
            center_y - text.size().y / 2.0,
        );
        ui.painter().galley(position, text, look.text);
    }
    response
}

/// Bouton réduit à son icône : le libellé reste dans l'infobulle et pour les lecteurs d'écran.
fn icon_button(ui: &mut Ui, glyph: char, label: &str, tooltip: &str) -> Response {
    let color = palette(ui).text;
    icon_button_with(ui, glyph, label, tooltip, color)
}

fn icon_button_with(
    ui: &mut Ui,
    glyph: char,
    label: &str,
    tooltip: &str,
    color: Color32,
) -> Response {
    let colors = palette(ui);
    let Some(font) = theme::icon_font(ui, 16.0) else {
        // Sans police d'icônes, le texte reste le seul moyen d'identifier le bouton.
        return ui.button(label).on_hover_text(tooltip);
    };
    let size = vec2(CONTROL_HEIGHT, CONTROL_HEIGHT);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    response.widget_info(|| WidgetInfo::labeled(WidgetType::Button, ui.is_enabled(), label));
    if ui.is_rect_visible(rect) {
        if response.is_pointer_button_down_on() {
            ui.painter().rect_filled(rect, 4.0, colors.pressed);
        } else if response.hovered() {
            ui.painter().rect_filled(rect, 4.0, colors.hover);
        }
        paint_focus(ui, &response, rect);
        ui.painter()
            .text(rect.center(), Align2::CENTER_CENTER, glyph, font, color);
    }
    response.on_hover_text(tooltip)
}

/// Ligne de liste à la manière d'un volet de navigation : une barre d'accent marque la sélection.
fn entry_row(ui: &mut Ui, site: &str, username: &str, selected: bool) -> Response {
    let colors = palette(ui);
    let size = vec2(ui.available_width(), LIST_ROW_HEIGHT);
    // Hors de l'ordre de tabulation : les flèches parcourent la liste, quelle qu'en soit la taille.
    let (rect, response) = ui.allocate_exact_size(size, Sense::CLICK);
    response.widget_info(|| {
        WidgetInfo::selected(
            WidgetType::SelectableLabel,
            ui.is_enabled(),
            selected,
            format!("{site} ({username})"),
        )
    });
    if ui.is_rect_visible(rect) {
        let inner = rect.shrink2(vec2(0.0, 2.0));
        if selected || response.hovered() {
            ui.painter().rect_filled(inner, 4.0, colors.hover);
        }
        if selected {
            let bar =
                Rect::from_center_size(pos2(inner.left() + 1.5, inner.center().y), vec2(3.0, 18.0));
            ui.painter().rect_filled(bar, 2.0, colors.accent);
        }
        paint_focus(ui, &response, inner);
        let width = inner.width() - 24.0;
        let left = inner.left() + 12.0;
        let line = |text: &str, style: TextStyle| {
            WidgetText::from(text).into_galley(ui, Some(TextWrapMode::Truncate), width, style)
        };
        ui.painter().galley(
            pos2(left, inner.top() + 5.0),
            line(site, TextStyle::Body),
            colors.text,
        );
        ui.painter().galley(
            pos2(left, inner.top() + 24.0),
            line(username, TextStyle::Small),
            colors.secondary,
        );
    }
    response
}

fn paint_focus(ui: &Ui, response: &Response, rect: Rect) {
    if response.has_focus() {
        ui.painter().rect_stroke(
            rect,
            4.0,
            Stroke::new(2.0_f32, palette(ui).text),
            egui::StrokeKind::Inside,
        );
    }
}

fn field_label(ui: &mut Ui, label: &str, required: bool) -> Response {
    ui.scope(|ui| {
        // Sans cela, la ligne aurait la hauteur d'un contrôle et s'éloignerait de son champ.
        ui.spacing_mut().interact_size.y = 0.0;
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = 2.0;
            let response = ui.label(label);
            if required {
                ui.label(RichText::new("*").color(palette(ui).danger));
            }
            response
        })
        .inner
    })
    .inner
}

fn required_input(ui: &mut Ui, label: &str, value: &mut String) -> Response {
    let label = field_label(ui, label, true);
    ui.add(
        TextEdit::singleline(value)
            .desired_width(f32::INFINITY)
            .margin(vec2(10.0, 6.0)),
    )
    .labelled_by(label.id)
}

fn path_input(ui: &mut Ui, path: &mut String, picking: bool, browse: &mut bool) -> Response {
    let label = ui.label("Fichier");
    ui.horizontal(|ui| {
        let response = ui
            .add(
                TextEdit::singleline(path)
                    .desired_width(ui.available_width() - BROWSE_BUTTON_WIDTH)
                    .margin(vec2(10.0, 6.0)),
            )
            .labelled_by(label.id);
        if ui
            .add_enabled(!picking, Button::new("Parcourir…"))
            .clicked()
        {
            *browse = true;
        }
        response
    })
    .inner
}

fn text_input(ui: &mut Ui, label: &str, value: &mut String) -> Response {
    let label = ui.label(label);
    ui.add(
        TextEdit::singleline(value)
            .desired_width(f32::INFINITY)
            .margin(vec2(10.0, 6.0)),
    )
    .labelled_by(label.id)
}

fn secret_input(ui: &mut Ui, label: &str, value: &mut Zeroizing<String>) -> Response {
    let label = ui.label(label);
    ui.add(
        TextEdit::singleline(&mut **value)
            .password(true)
            .desired_width(f32::INFINITY)
            .margin(vec2(10.0, 6.0)),
    )
    .labelled_by(label.id)
}

/// Vrai si la touche Entrée vient de valider le champ.
fn entered(response: &Response) -> bool {
    response.lost_focus() && response.ctx.input(|input| input.key_pressed(Key::Enter))
}

fn field_name(ui: &mut Ui, label: &str) {
    ui.label(RichText::new(label).color(palette(ui).secondary));
}

/// Ligne de la fiche : nom du champ, valeur, puis boutons alignés en fin de ligne.
fn detail_line(
    ui: &mut Ui,
    label: &str,
    buttons: impl FnOnce(&mut Ui),
    value: impl FnOnce(&mut Ui),
) {
    ui.horizontal(|ui| {
        ui.allocate_ui_with_layout(
            vec2(DETAIL_LABEL_WIDTH, CONTROL_HEIGHT),
            Layout::left_to_right(Align::Center),
            |ui| {
                ui.set_min_width(DETAIL_LABEL_WIDTH);
                field_name(ui, label);
            },
        );
        ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
            buttons(ui);
            ui.with_layout(Layout::left_to_right(Align::Center), value);
        });
    });
}

fn detail_value(ui: &mut Ui, value: &str) {
    ui.add(egui::Label::new(value).wrap());
}

/// Bandeau de message à la manière d'une barre d'information Windows.
fn info_bar(ui: &mut Ui, status: Option<&(String, bool)>) {
    let Some((message, is_error)) = status else {
        return;
    };
    let colors = palette(ui);
    let (fill, accent, glyph) = if *is_error {
        (colors.danger_background, colors.danger, icon::ERROR)
    } else {
        (colors.success_background, colors.success, icon::SUCCESS)
    };
    Frame::new()
        .fill(fill)
        .corner_radius(CornerRadius::same(4))
        .inner_margin(Margin::symmetric(12, 8))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.horizontal_wrapped(|ui| {
                if let Some(font) = theme::icon_font(ui, 16.0) {
                    ui.label(RichText::new(glyph).font(font).color(accent));
                }
                ui.label(message);
            });
        });
}

fn local_date(date: &chrono::DateTime<chrono::Utc>) -> String {
    date.with_timezone(&chrono::Local)
        .format("%d/%m/%Y %H:%M")
        .to_string()
}

fn mismatch() -> Error {
    Error::Validation("Les deux mots de passe diffèrent".to_owned())
}

#[cfg(test)]
impl GuiApp {
    fn entries(&self) -> &[crate::entry::Entry] {
        self.workspace
            .as_ref()
            .map_or(&[], |workspace| workspace.all_entries())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::FAST_KDF;
    use egui::accesskit::Role;
    use egui_kittest::Harness;
    use egui_kittest::kittest::Queryable;

    const MASTER: &str = "correct horse battery";

    #[test]
    fn embedded_icon_is_a_valid_image() {
        let icon = eframe::icon_data::from_png_bytes(ICON_PNG).unwrap();
        assert_eq!((icon.width, icon.height), (57, 57));
    }

    fn harness<'a>() -> Harness<'a, GuiApp> {
        let store = Store::open_in_memory().unwrap().with_kdf(FAST_KDF);
        let harness = Harness::new_state(|ctx, app: &mut GuiApp| app.ui(ctx), GuiApp::new(store));
        theme::apply(&harness.ctx);
        harness
    }

    fn type_into(harness: &mut Harness<'_, GuiApp>, label: &str, text: &str) {
        let role = if label.starts_with("Mot de passe") || label == "Confirmer" {
            Role::PasswordInput
        } else {
            Role::TextInput
        };
        harness.get_by_role_and_label(role, label).click();
        harness.step();
        harness.get_by_role_and_label(role, label).type_text(text);
        harness.step();
    }

    fn click(harness: &mut Harness<'_, GuiApp>, label: &str) {
        harness.get_by_label(label).click();
        // Laisse au dialogue modal le temps de finir de se fermer et de libérer les clics.
        harness.run_steps(30);
    }

    fn registered<'a>() -> Harness<'a, GuiApp> {
        let mut harness = harness();
        harness.step();
        type_into(&mut harness, "Compte", "alice");
        type_into(&mut harness, "Mot de passe maître", MASTER);
        type_into(&mut harness, "Confirmer", MASTER);
        click(&mut harness, "Créer le compte");
        assert!(
            harness.state().workspace.is_some(),
            "compte non créé : {:?}",
            harness.state().status
        );
        harness
    }

    fn add_entry(harness: &mut Harness<'_, GuiApp>, site: &str, password: &str) {
        click(harness, "Ajouter");
        type_into(harness, "Site", site);
        type_into(harness, "Identifiant", "moi");
        type_into(harness, "Mot de passe", password);
        click(harness, "Valider");
        assert!(
            harness.state().dialog.is_none(),
            "dialogue resté ouvert : {:?}",
            harness.state().dialog_error
        );
    }

    #[test]
    fn wrong_password_is_rejected() {
        let mut harness = registered();
        click(&mut harness, "Verrouiller");
        assert!(harness.state().workspace.is_none());
        type_into(&mut harness, "Compte", "alice");
        type_into(&mut harness, "Mot de passe maître", "mauvais mot de passe");
        click(&mut harness, "Déverrouiller");
        assert!(harness.state().workspace.is_none());
        assert!(
            harness
                .query_by_label("Compte ou mot de passe incorrect")
                .is_some()
        );
    }

    #[test]
    fn registration_rejects_a_mismatched_confirmation() {
        let mut harness = harness();
        harness.step();
        type_into(&mut harness, "Compte", "alice");
        type_into(&mut harness, "Mot de passe maître", MASTER);
        type_into(&mut harness, "Confirmer", "autre chose");
        click(&mut harness, "Créer le compte");
        assert!(harness.state().workspace.is_none());
        assert!(
            harness
                .query_by_label("Les deux mots de passe diffèrent")
                .is_some()
        );
    }

    #[test]
    fn password_stays_hidden_until_revealed() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "secret-visible");
        assert!(harness.query_by_label("secret-visible").is_none());
        click(&mut harness, "Afficher");
        assert!(harness.query_by_label("secret-visible").is_some());
        click(&mut harness, "Masquer");
        assert!(harness.query_by_label("secret-visible").is_none());
    }

    #[test]
    fn invalid_entry_keeps_the_dialog_open() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "Site", "https://a.example");
        click(&mut harness, "Valider");
        assert!(harness.state().dialog.is_some());
        assert!(
            harness
                .query_by_label("L'identifiant est obligatoire")
                .is_some()
        );
        assert!(harness.state().entries().is_empty());
    }

    fn selected_position(harness: &Harness<'_, GuiApp>) -> usize {
        harness
            .state()
            .workspace
            .as_ref()
            .unwrap()
            .selected_position()
    }

    #[test]
    fn arrow_keys_move_the_selection_and_stop_at_the_ends() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        add_entry(&mut harness, "https://b.example", "p2");
        click(&mut harness, "https://a.example (moi)");
        click(&mut harness, "https://b.example (moi)");
        let start = selected_position(&harness);
        let (toward_other, away) = if start == 0 {
            (Key::ArrowDown, Key::ArrowUp)
        } else {
            (Key::ArrowUp, Key::ArrowDown)
        };

        harness.key_press(away);
        harness.run_steps(3);
        assert_eq!(selected_position(&harness), start);

        harness.state_mut().revealed = true;
        harness.key_press(toward_other);
        harness.run_steps(3);
        assert_ne!(selected_position(&harness), start);
        assert!(!harness.state().revealed);
    }

    #[test]
    fn arrow_keys_do_nothing_while_a_dialog_is_open() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        add_entry(&mut harness, "https://b.example", "p2");
        click(&mut harness, "https://a.example (moi)");
        let start = selected_position(&harness);
        click(&mut harness, "Ajouter");
        harness.key_press(Key::ArrowDown);
        harness.key_press(Key::ArrowUp);
        harness.run_steps(3);
        assert_eq!(selected_position(&harness), start);
    }

    #[test]
    fn ctrl_f_focuses_the_search_field() {
        let mut harness = registered();
        add_entry(&mut harness, "https://github.example", "p1");
        add_entry(&mut harness, "https://impots.example", "p2");
        harness.key_press_modifiers(Modifiers::COMMAND, Key::F);
        harness.run_steps(3);
        harness
            .input_mut()
            .events
            .push(egui::Event::Text("impots".to_owned()));
        harness.run_steps(3);
        assert!(
            harness
                .query_by_label("https://github.example (moi)")
                .is_none()
        );
    }

    #[test]
    fn mcp_calls_are_answered_by_the_interface_loop() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "s3cret-du-coffre");
        let server = McpServer::start_on(0, Box::new(|| {})).unwrap();
        let (url, token) = (server.url().to_owned(), server.token().to_owned());
        harness.state_mut().mcp = Some(server);
        let client = std::thread::spawn(move || {
            let body = r#"{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_entries","arguments":{}}}"#;
            mcp::post(&url, &token, body)
        });
        while !client.is_finished() {
            harness.step();
        }
        let (status, body) = client.join().unwrap();
        assert_eq!(status, 200);
        assert!(body.contains("https://a.example"));
        assert!(!body.contains("s3cret-du-coffre"));
    }

    #[test]
    fn list_row_fills_the_panel_width() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        add_entry(&mut harness, "https://b.example", "p2");
        let first = harness.get_by_label("https://a.example (moi)").rect();
        let second = harness.get_by_label("https://b.example (moi)").rect();
        assert!(first.width() > 300.0, "largeur : {}", first.width());
        // Les lignes sont jointives, quel que soit leur ordre d'affichage.
        let gap = (second.min.y - first.max.y)
            .abs()
            .min((first.min.y - second.max.y).abs());
        assert!(gap < 1.0, "écart : {gap}");
    }

    #[test]
    fn copy_buttons_are_icons_aligned_at_the_end_of_their_lines() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        let username = harness.get_by_label("Copier l'identifiant").rect();
        let password = harness.get_by_label("Copier le mot de passe").rect();
        let reveal = harness.get_by_label("Afficher").rect();
        assert_eq!(username.max.x, password.max.x);
        assert!(reveal.max.x <= password.min.x);
        assert_eq!(reveal.center().y, password.center().y);
        assert!(username.center().y < password.center().y);
        assert!(password.width() <= CONTROL_HEIGHT);
    }

    #[test]
    fn edit_and_delete_are_at_the_end_of_the_name_line() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        let name = harness.get_by_label("https://a.example").rect();
        let edit = harness.get_by_label("Modifier").rect();
        let delete = harness.get_by_label("Supprimer").rect();
        let copy = harness.get_by_label("Copier l'identifiant").rect();
        assert_eq!(edit.center().y, delete.center().y);
        assert!((name.center().y - edit.center().y).abs() < 2.0);
        assert!(edit.max.x <= delete.min.x);
        assert_eq!(delete.max.x.round(), (copy.max.x + 17.0).round());
    }

    #[test]
    fn account_name_is_next_to_the_lock_button() {
        let harness = registered();
        let name = harness.get_by_label("alice").rect();
        let lock = harness.get_by_label("Verrouiller").rect();
        assert!(name.max.x <= lock.min.x);
        assert!((name.center().y - lock.center().y).abs() < 2.0);
        assert!(lock.max.y <= harness.get_by_label("Ajouter").rect().min.y);
    }

    #[test]
    fn entry_count_is_above_the_list_and_left_aligned() {
        let mut harness = registered();
        assert!(harness.query_by_label("0 entrée").is_some());
        add_entry(&mut harness, "https://a.example", "p1");
        assert!(harness.query_by_label("1 entrée").is_some());
        add_entry(&mut harness, "https://b.example", "p2");
        let count = harness.get_by_label("2 entrées").rect();
        let add = harness.get_by_label("Ajouter").rect();
        assert!(count.min.y >= add.max.y);
        assert!(count.min.x < add.min.x);
    }

    fn press_outside_the_dialog(harness: &mut Harness<'_, GuiApp>) {
        let pos = pos2(5.0, 5.0);
        harness
            .input_mut()
            .events
            .push(egui::Event::PointerMoved(pos));
        harness.run_steps(2);
        for pressed in [true, false] {
            harness.input_mut().events.push(egui::Event::PointerButton {
                pos,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: Modifiers::NONE,
            });
            harness.run_steps(2);
        }
    }

    fn dialog_site(harness: &Harness<'_, GuiApp>) -> String {
        match &harness.state().dialog {
            Some(Dialog::Entry { fields, .. }) => fields.url.clone(),
            _ => panic!("formulaire d'entrée fermé"),
        }
    }

    #[test]
    fn first_launch_opens_account_creation_and_later_launches_the_login() {
        let mut harness = harness();
        harness.step();
        assert!(harness.query_by_label("Créer le compte").is_some());
        type_into(&mut harness, "Compte", "alice");
        type_into(&mut harness, "Mot de passe maître", MASTER);
        type_into(&mut harness, "Confirmer", MASTER);
        click(&mut harness, "Créer le compte");
        click(&mut harness, "Verrouiller");
        assert!(harness.query_by_label("Déverrouiller").is_some());
    }

    #[test]
    fn enter_in_the_login_name_moves_to_an_empty_password() {
        let mut harness = registered();
        click(&mut harness, "Verrouiller");
        type_into(&mut harness, "Compte", "alice");
        harness.key_press(Key::Enter);
        harness.run_steps(3);
        assert!(harness.state().status.is_none());
        harness
            .input_mut()
            .events
            .push(egui::Event::Text(MASTER.to_owned()));
        harness.run_steps(3);
        harness.key_press(Key::Enter);
        harness.run_steps(3);
        assert!(harness.state().workspace.is_some());
    }

    #[test]
    fn a_dialog_opens_with_its_first_field_focused() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        harness
            .input_mut()
            .events
            .push(egui::Event::Text("https://a.example".to_owned()));
        harness.run_steps(3);
        assert_eq!(dialog_site(&harness), "https://a.example");
    }

    #[test]
    fn enter_in_a_text_field_submits_the_dialog() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "Site", "https://a.example");
        type_into(&mut harness, "Identifiant", "alice");
        harness
            .get_by_role_and_label(Role::PasswordInput, "Mot de passe")
            .click();
        harness.step();
        harness
            .get_by_role_and_label(Role::PasswordInput, "Mot de passe")
            .type_text("p1");
        harness.step();
        harness.key_press(Key::Enter);
        harness.run_steps(30);
        assert!(harness.state().dialog.is_none());
        assert_eq!(harness.state().entries().len(), 1);
    }

    #[test]
    fn enter_does_not_confirm_a_deletion() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        click(&mut harness, "Supprimer");
        harness.key_press(Key::Enter);
        harness.run_steps(5);
        assert!(harness.state().dialog.is_some());
        assert_eq!(harness.state().entries().len(), 1);
    }

    #[test]
    fn clicking_outside_a_dialog_keeps_the_typed_data() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "Site", "https://a.example");
        press_outside_the_dialog(&mut harness);
        assert_eq!(dialog_site(&harness), "https://a.example");
    }

    #[test]
    fn escape_closes_an_untouched_dialog() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        harness.key_press(Key::Escape);
        harness.run_steps(30);
        assert!(harness.state().dialog.is_none());
    }

    #[test]
    fn escape_asks_before_discarding_changes() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "Site", "https://a.example");
        harness.key_press(Key::Escape);
        harness.run_steps(3);
        assert_eq!(dialog_site(&harness), "https://a.example");
        click(&mut harness, "Continuer la saisie");
        assert_eq!(dialog_site(&harness), "https://a.example");
        assert!(harness.query_by_label("Abandonner").is_none());
        harness.key_press(Key::Escape);
        harness.run_steps(3);
        click(&mut harness, "Abandonner");
        assert!(harness.state().dialog.is_none());
    }

    #[test]
    fn locking_forgets_a_pending_discard_prompt() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "Site", "https://a.example");
        harness.key_press(Key::Escape);
        harness.run_steps(3);
        assert!(harness.state().discard_prompt);
        harness.state_mut().lock();
        assert!(!harness.state().discard_prompt);
    }

    #[test]
    fn escape_on_an_unchanged_edit_closes_it() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        click(&mut harness, "Modifier");
        harness.key_press(Key::Escape);
        harness.run_steps(30);
        assert!(harness.state().dialog.is_none());
    }

    #[test]
    fn information_messages_expire_but_errors_stay() {
        let mut harness = registered();
        harness.state_mut().set_info("Fait");
        harness.step();
        assert!(harness.query_by_label("Fait").is_some());
        harness.state_mut().status_expires = Some(Instant::now());
        harness.step();
        assert!(harness.state().status.is_none());
        harness.state_mut().set_error("Échec");
        assert!(harness.state().status_expires.is_none());
    }

    #[test]
    fn empty_vault_offers_to_add_or_import() {
        let mut harness = registered();
        assert!(harness.query_by_label("Votre coffre est vide").is_some());
        click(&mut harness, "Importer un CSV");
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Import { .. })
        ));
        click(&mut harness, "Annuler");
        click(&mut harness, "Ajouter une entrée");
        assert!(matches!(harness.state().dialog, Some(Dialog::Entry { .. })));
    }

    #[test]
    fn search_without_result_names_the_query() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        type_into(&mut harness, "Recherche", "zzz");
        harness.run_steps(3);
        assert!(
            harness
                .query_by_label("Aucun résultat pour « zzz »")
                .is_some()
        );
        assert!(harness.query_by_label("Votre coffre est vide").is_none());
    }

    fn type_text(harness: &mut Harness<'_, GuiApp>, text: &str) {
        harness
            .input_mut()
            .events
            .push(egui::Event::Text(text.to_owned()));
        harness.run_steps(3);
    }

    fn press_copy(harness: &mut Harness<'_, GuiApp>) {
        harness.input_mut().events.push(egui::Event::Copy);
        harness.run_steps(3);
    }

    fn copied(harness: &Harness<'_, GuiApp>) -> Option<String> {
        harness.state().clipboard.copied_text().map(str::to_owned)
    }

    #[test]
    fn unlocking_focuses_the_search() {
        let mut harness = registered();
        type_text(&mut harness, "git");
        assert_eq!(harness.state().search, "git");
    }

    #[test]
    fn closing_a_dialog_returns_to_the_search() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        click(&mut harness, "Annuler");
        type_text(&mut harness, "git");
        assert_eq!(harness.state().search, "git");
    }

    #[test]
    fn arrow_keys_keep_the_focus_in_the_search() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        add_entry(&mut harness, "https://b.example", "p2");
        harness.key_press(Key::ArrowDown);
        harness.run_steps(3);
        type_text(&mut harness, "a");
        assert_eq!(harness.state().search, "a");
    }

    #[test]
    fn copy_shortcut_copies_the_password_from_the_search() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        type_text(&mut harness, "a");
        press_copy(&mut harness);
        assert_eq!(copied(&harness).as_deref(), Some("p1"));
    }

    #[test]
    fn copy_shortcut_leaves_a_search_selection_alone() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        type_text(&mut harness, "a");
        let id = egui::Id::new(SEARCH_ID);
        let ctx = harness.ctx.clone();
        let mut state = TextEdit::load_state(&ctx, id).unwrap();
        state
            .cursor
            .set_char_range(Some(egui::text::CCursorRange::two(
                egui::text::CCursor::new(0),
                egui::text::CCursor::new(1),
            )));
        TextEdit::store_state(&ctx, id, state);
        press_copy(&mut harness);
        assert_eq!(copied(&harness), None);
    }

    #[test]
    fn username_shortcut_copies_the_username() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        harness.key_press_modifiers(Modifiers::COMMAND, Key::B);
        harness.run_steps(3);
        let username = harness.state().entries()[0].fields.username.clone();
        assert_eq!(copied(&harness), Some(username));
    }

    #[test]
    fn shortcuts_are_off_while_a_dialog_is_open() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        click(&mut harness, "Ajouter");
        press_copy(&mut harness);
        assert_eq!(copied(&harness), None);
    }

    #[test]
    fn add_shortcut_opens_the_form() {
        let mut harness = registered();
        harness.key_press_modifiers(Modifiers::COMMAND, Key::N);
        harness.run_steps(3);
        assert!(matches!(harness.state().dialog, Some(Dialog::Entry { .. })));
    }

    #[test]
    fn delete_key_asks_for_confirmation_unless_it_edits_the_search() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        type_text(&mut harness, "a");
        harness.key_press(Key::Delete);
        harness.run_steps(3);
        assert!(harness.state().dialog.is_none());
        harness.key_press(Key::Backspace);
        harness.run_steps(3);
        assert_eq!(harness.state().search, "");
        harness.key_press(Key::Delete);
        harness.run_steps(3);
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Delete { .. })
        ));
        assert_eq!(harness.state().entries().len(), 1);
    }

    #[test]
    fn list_rows_are_not_tab_stops() {
        let mut harness = registered();
        for site in [
            "https://a.example",
            "https://b.example",
            "https://c.example",
        ] {
            add_entry(&mut harness, site, "p1");
        }
        // Depuis la recherche : Ajouter, Plus, accès pour assistants IA, Supprimer.
        for _ in 0..4 {
            harness.key_press(Key::Tab);
            harness.run_steps(2);
        }
        harness.key_press(Key::Enter);
        harness.run_steps(5);
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Delete { .. })
        ));
    }

    #[test]
    fn picked_file_fills_the_path_field() {
        let mut harness = registered();
        open_menu_item(&mut harness, "Importer");
        let (sender, receiver) = mpsc::channel();
        harness.state_mut().file_picker = Some(receiver);
        sender.send(Some(PathBuf::from("mots.csv"))).unwrap();
        harness.run_steps(3);
        assert!(harness.state().file_picker.is_none());
        assert!(matches!(
            &harness.state().dialog,
            Some(Dialog::Import { path }) if path == "mots.csv"
        ));
    }

    #[test]
    fn empty_form_shows_every_required_error_at_once() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        assert!(harness.query_by_label("Le site est obligatoire").is_none());
        click(&mut harness, "Valider");
        for error in [
            "Le site est obligatoire",
            "L'identifiant est obligatoire",
            "Le mot de passe est obligatoire",
        ] {
            assert!(harness.query_by_label(error).is_some(), "{error}");
        }
        assert!(harness.state().entries().is_empty());
    }

    #[test]
    fn invalid_email_appears_after_leaving_the_field() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        type_into(&mut harness, "E-mail", "pas-un-mail");
        harness.run_steps(2);
        assert!(
            harness
                .query_by_label("L'adresse e-mail est invalide")
                .is_none()
        );
        harness
            .get_by_role_and_label(Role::TextInput, "Notes")
            .click();
        harness.run_steps(3);
        assert!(
            harness
                .query_by_label("L'adresse e-mail est invalide")
                .is_some()
        );
    }

    #[test]
    fn registration_shows_rules_under_the_fields() {
        let mut harness = harness();
        harness.step();
        click(&mut harness, "Créer le compte");
        assert!(
            harness
                .query_by_label("Le nom du compte doit faire de 3 à 50 caractères")
                .is_some()
        );
        assert!(harness.state().workspace.is_none());
    }

    #[test]
    fn export_refuses_an_existing_file_with_a_clear_message() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("deja.csv");
        std::fs::write(&path, "contenu").unwrap();
        let mut harness = registered();
        open_menu_item(&mut harness, "Exporter");
        type_into(&mut harness, "Fichier", path.to_str().unwrap());
        click(&mut harness, "Valider");
        assert!(
            harness
                .query_by_label("Ce fichier existe déjà : choisissez un autre nom")
                .is_some()
        );
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "contenu");
    }

    fn open_menu_item(harness: &mut Harness<'_, GuiApp>, item: &str) {
        click(harness, "Plus");
        click(harness, item);
    }

    #[test]
    fn rare_actions_are_in_the_more_menu() {
        let mut harness = registered();
        assert!(harness.query_by_label("Importer").is_none());
        assert!(harness.query_by_label("Exporter").is_none());
        click(&mut harness, "Plus");
        assert!(harness.query_by_label("Importer").is_some());
        assert!(harness.query_by_label("Mot de passe maître").is_some());
        click(&mut harness, "Exporter");
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Export { .. })
        ));
    }

    #[test]
    fn open_menu_keeps_the_keyboard_from_the_shortcuts() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        add_entry(&mut harness, "https://b.example", "p2");
        let selected = selected_position(&harness);
        click(&mut harness, "Plus");
        harness.key_press(Key::ArrowDown);
        harness.key_press(Key::Delete);
        harness.run_steps(3);
        assert_eq!(selected_position(&harness), selected);
        assert!(harness.state().dialog.is_none());
    }

    #[test]
    fn keyboard_reaches_the_menu_items() {
        let mut harness = registered();
        // Depuis la recherche : Ajouter, puis Plus.
        for _ in 0..2 {
            harness.key_press(Key::Tab);
            harness.run_steps(2);
        }
        harness.key_press(Key::Enter);
        harness.run_steps(5);
        assert!(harness.query_by_label("Importer").is_some());
        harness.key_press(Key::Enter);
        harness.run_steps(5);
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Import { .. })
        ));
    }

    #[test]
    fn ai_access_button_states_its_state_in_words() {
        let harness = registered();
        assert!(
            harness
                .query_by_label("Accès pour assistants IA : désactivé")
                .is_some()
        );
    }

    #[test]
    fn entry_form_reveals_the_password_with_the_same_control() {
        let mut harness = registered();
        click(&mut harness, "Ajouter");
        click(&mut harness, "Afficher");
        assert!(matches!(
            harness.state().dialog,
            Some(Dialog::Entry { revealed: true, .. })
        ));
        assert!(harness.query_by_label("Masquer").is_some());
    }

    #[test]
    fn login_screen_shows_the_logo() {
        let mut harness = harness();
        harness.step();
        assert!(harness.state().logo.is_some());
    }

    #[test]
    fn search_filters_the_list() {
        let mut harness = registered();
        add_entry(&mut harness, "https://github.example", "p1");
        add_entry(&mut harness, "https://impots.example", "p2");
        type_into(&mut harness, "Recherche", "impots");
        assert!(
            harness
                .query_by_label("https://impots.example (moi)")
                .is_some()
        );
        assert!(
            harness
                .query_by_label("https://github.example (moi)")
                .is_none()
        );
    }

    #[test]
    fn delete_requires_confirmation() {
        let mut harness = registered();
        add_entry(&mut harness, "https://a.example", "p1");
        click(&mut harness, "Supprimer");
        click(&mut harness, "Annuler");
        assert_eq!(harness.state().entries().len(), 1);
        click(&mut harness, "Supprimer");
        click(&mut harness, "Confirmer la suppression");
        assert!(harness.state().entries().is_empty());
    }

    #[test]
    fn locking_stops_the_mcp_server() {
        let mut harness = registered();
        harness.state_mut().mcp = Some(McpServer::start_on(0, Box::new(|| {})).unwrap());
        click(&mut harness, "Verrouiller");
        assert!(harness.state().mcp.is_none());
    }

    #[test]
    fn idle_timeout_locks_the_vault() {
        let mut harness = registered();
        harness.state_mut().last_activity = Instant::now() - IDLE_LOCK;
        harness.step();
        assert!(harness.state().workspace.is_none());
    }
}
