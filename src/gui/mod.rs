//! Interface graphique.

mod theme;

use std::path::Path;
use std::time::{Duration, Instant};

use eframe::egui;
use egui::{
    Align, Align2, Button, Context, CornerRadius, Frame, Key, Layout, Margin, Modal, Modifiers,
    Rect, Response, RichText, ScrollArea, Sense, Stroke, TextEdit, TextStyle, TextWrapMode, Ui,
    WidgetInfo, WidgetText, WidgetType, pos2, vec2,
};
use zeroize::Zeroizing;

use crate::IDLE_LOCK;
use crate::clipboard::SecretClipboard;
use crate::csv_io;
use crate::entry::EntryFields;
use crate::error::{Error, Result};
use crate::generator::{DEFAULT_LENGTH, generate_password};
use crate::mcp::{self, McpServer};
use crate::store::Store;
use crate::workspace::Workspace;
use theme::{icon, palette};

const TICK: Duration = Duration::from_secs(1);
const LOGIN_CARD_WIDTH: f32 = 340.0;
const LIST_ROW_HEIGHT: f32 = 48.0;
const CONTROL_HEIGHT: f32 = 32.0;
// Bouton de verrouillage, libellé et champ de recherche.
const TITLE_RESERVED_WIDTH: f32 = 350.0;
const DETAIL_LABEL_WIDTH: f32 = 100.0;
// Marges de la carte (2 × 16) et bordure.
const DETAIL_CARD_CHROME: f32 = 34.0;
const DIALOG_WIDTH: f32 = 460.0;
const DIALOG_BUTTON_WIDTH: f32 = 130.0;
const PASSWORD_TOOLS_WIDTH: f32 = 190.0;

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
    dialog_error: Option<String>,
    last_activity: Instant,
}

impl GuiApp {
    fn new(store: Store) -> Self {
        Self {
            store,
            clipboard: SecretClipboard::default(),
            mcp: None,
            workspace: None,
            login: LoginForm::default(),
            dialog: None,
            search: String::new(),
            revealed: false,
            status: None,
            dialog_error: None,
            last_activity: Instant::now(),
        }
    }

    fn set_info(&mut self, message: impl Into<String>) {
        self.status = Some((message.into(), false));
    }

    fn set_error(&mut self, error: impl ToString) {
        self.status = Some((error.to_string(), true));
    }

    fn lock(&mut self) {
        self.workspace = None;
        self.mcp = None;
        self.dialog = None;
        self.dialog_error = None;
        self.search.clear();
        self.revealed = false;
        self.status = None;
        self.login = LoginForm::default();
        self.clipboard.clear();
    }

    fn ui(&mut self, ctx: &Context) {
        ctx.request_repaint_after(TICK);
        self.clipboard.tick();
        if ctx.input(|input| !input.events.is_empty()) {
            self.last_activity = Instant::now();
        }
        if self.workspace.is_some() && self.last_activity.elapsed() >= IDLE_LOCK {
            self.lock();
            self.set_info("Coffre verrouillé après 5 minutes d'inactivité");
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
        ui.label(RichText::new("PG").heading().size(28.0));
        ui.label(
            RichText::new(if registering {
                "Créer un coffre protégé par un mot de passe maître"
            } else {
                "Déverrouiller votre coffre"
            })
            .color(palette(ui).secondary),
        );
        ui.add_space(12.0);
        let mut submitted = false;
        text_field(ui, "Utilisateur", &mut self.login.username);
        submitted |= secret_field(ui, "Mot de passe maître", &mut self.login.password);
        if registering {
            submitted |= secret_field(ui, "Confirmer", &mut self.login.confirm);
        }
        ui.add_space(4.0);
        submitted |= primary_button(
            ui,
            if registering {
                "Créer le compte"
            } else {
                "Se connecter"
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
                self.status = None;
            }
        });
        if submitted {
            self.submit_login();
        }
        info_bar(ui, self.status.as_ref());
    }

    fn submit_login(&mut self) {
        let form = &self.login;
        let session = if form.registering {
            if *form.password != *form.confirm {
                self.set_error(mismatch());
                return;
            }
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
            }
            Err(error) => self.set_error(error),
        }
    }

    fn vault_ui(&mut self, ctx: &Context) {
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
                lock = icon_button(ui, icon::LOCK, "Verrouiller").clicked();
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    let search = ui
                        .add(
                            TextEdit::singleline(&mut self.search)
                                .desired_width(220.0)
                                .margin(vec2(10.0, 6.0)),
                        )
                        .on_hover_text("Ctrl+F");
                    let label = ui.label("Recherche");
                    let search = search.labelled_by(label.id);
                    if self.dialog.is_none()
                        && ui.input_mut(|input| input.consume_key(Modifiers::COMMAND, Key::F))
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
                if command_button(ui, icon::ADD, "Ajouter", false).clicked() {
                    self.dialog = Some(Dialog::Entry {
                        id: None,
                        fields: EntryFields::default(),
                        revealed: false,
                    });
                }
                if command_button(ui, icon::IMPORT, "Importer", false).clicked() {
                    self.dialog = Some(Dialog::Import {
                        path: String::new(),
                    });
                }
                if command_button(ui, icon::EXPORT, "Exporter", false).clicked() {
                    self.dialog = Some(Dialog::Export {
                        path: String::new(),
                    });
                }
                if command_button(ui, icon::KEY, "Mot de passe maître", false).clicked() {
                    self.dialog = Some(Dialog::ChangeMaster {
                        current: Zeroizing::default(),
                        new: Zeroizing::default(),
                        confirm: Zeroizing::default(),
                    });
                }
                if command_button(ui, icon::CONNECT, "MCP", self.mcp.is_some())
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
                    && command_button(ui, icon::COPY, "Jeton MCP", false)
                        .on_hover_text(server.url())
                        .clicked()
                {
                    let message = mcp::copy_token(server, &mut self.clipboard);
                    self.set_info(message);
                }
            });
        });
    }

    fn list_ui(&mut self, ui: &mut Ui) {
        let Some(workspace) = &mut self.workspace else {
            return;
        };
        let previous = workspace.selected_position();
        if self.dialog.is_none() {
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
            ui.add_space(24.0);
            ui.vertical_centered(|ui| {
                ui.label(RichText::new("Aucune entrée").color(palette(ui).secondary));
            });
            return;
        };
        let fields = &entry.fields;
        let revealed = self.revealed;
        ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    ui.spacing_mut().item_spacing.x = 4.0;
                    // Disposition de droite à gauche : le dernier ajouté s'affiche en premier.
                    if command_button(ui, icon::DELETE, "Supprimer", false).clicked() {
                        self.dialog = Some(Dialog::Delete {
                            id: entry.id.clone(),
                            site: fields.url.clone(),
                        });
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
                        if icon_button(ui, icon::COPY, "Copier l'identifiant").clicked() {
                            self.copy(&fields.username, "Identifiant copié (effacé dans 30 s)");
                        }
                    },
                    |ui| detail_value(ui, &fields.username),
                );
                detail_line(
                    ui,
                    "Mot de passe",
                    |ui| {
                        // Disposition de droite à gauche : le dernier ajouté s'affiche en premier.
                        if icon_button(ui, icon::COPY, "Copier le mot de passe").clicked() {
                            self.copy(&fields.password, "Mot de passe copié (effacé dans 30 s)");
                        }
                        let (glyph, label) = if revealed {
                            (icon::HIDE, "Masquer")
                        } else {
                            (icon::SHOW, "Afficher")
                        };
                        if icon_button(ui, glyph, label).clicked() {
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

    fn copy(&mut self, text: &str, message: &str) {
        match self.clipboard.copy(text) {
            Ok(()) => self.set_info(message),
            Err(error) => self.set_error(format!("Presse-papiers indisponible : {error}")),
        }
    }

    fn dialog_ui(&mut self, ctx: &Context) {
        let Some(mut dialog) = self.dialog.take() else {
            return;
        };
        let error = self.dialog_error.clone();
        let modal = Modal::new(egui::Id::new("dialog")).show(ctx, |ui| {
            ui.set_width(DIALOG_WIDTH);
            let mut action = dialog_content(ui, &mut dialog);
            if let Some(error) = &error {
                ui.label(RichText::new(error).color(palette(ui).danger));
            }
            ui.add_space(8.0);
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                let submit = if matches!(dialog, Dialog::Delete { .. }) {
                    "Confirmer la suppression"
                } else {
                    "Valider"
                };
                if secondary_button(ui, "Annuler").clicked() {
                    action = DialogAction::Close;
                }
                if primary_button(ui, submit, DIALOG_BUTTON_WIDTH).clicked() {
                    action = DialogAction::Submit;
                }
            });
            action
        });
        let action = if modal.should_close() {
            DialogAction::Close
        } else {
            modal.inner
        };
        match action {
            DialogAction::Keep => self.dialog = Some(dialog),
            DialogAction::Close => self.dialog_error = None,
            DialogAction::Submit => match self.submit_dialog(&dialog) {
                Ok(message) => {
                    self.dialog_error = None;
                    self.set_info(message);
                }
                Err(error) => {
                    self.dialog_error = Some(error.to_string());
                    self.dialog = Some(dialog);
                }
            },
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
                format!("{} enregistré", entry.fields.url)
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

fn dialog_content(ui: &mut Ui, dialog: &mut Dialog) -> DialogAction {
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
            text_field(ui, "Site", &mut fields.url);
            text_field(ui, "Identifiant", &mut fields.username);
            let label = ui.label("Mot de passe");
            ui.horizontal(|ui| {
                ui.add(
                    TextEdit::singleline(&mut fields.password)
                        .password(!*revealed)
                        .desired_width(ui.available_width() - PASSWORD_TOOLS_WIDTH)
                        .margin(vec2(10.0, 6.0)),
                )
                .labelled_by(label.id);
                ui.checkbox(revealed, "Afficher");
                if ui.button("Générer").clicked() {
                    fields.password = generate_password(DEFAULT_LENGTH);
                    *revealed = true;
                }
            });
            text_field(ui, "E-mail", &mut fields.email);
            text_field(ui, "Téléphone", &mut fields.phone);
            text_field(ui, "Notes", &mut fields.notes);
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
            submitted |= secret_field(ui, "Actuel", current);
            submitted |= secret_field(ui, "Nouveau", new);
            submitted |= secret_field(ui, "Confirmer", confirm);
        }
        Dialog::Import { path } => {
            ui.heading("Importer un CSV");
            ui.add_space(4.0);
            text_field(ui, "Fichier", path);
        }
        Dialog::Export { path } => {
            ui.heading("Exporter en CSV");
            ui.label(
                RichText::new(
                    "L'export est EN CLAIR : tout lecteur du fichier verra les mots de passe.",
                )
                .color(palette(ui).warning),
            );
            text_field(ui, "Fichier", path);
        }
    }
    if submitted {
        DialogAction::Submit
    } else {
        DialogAction::Keep
    }
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
    let colors = palette(ui);
    ui.add_sized(
        vec2(width, CONTROL_HEIGHT),
        Button::new(RichText::new(label).color(colors.on_accent))
            .fill(colors.accent)
            .stroke(Stroke::NONE),
    )
}

fn secondary_button(ui: &mut Ui, label: &str) -> Response {
    ui.add_sized(
        vec2(DIALOG_BUTTON_WIDTH, CONTROL_HEIGHT),
        Button::new(label),
    )
}

/// Bouton de barre de commandes : icône d'accent et texte, sans fond tant qu'il n'est pas survolé.
fn command_button(ui: &mut Ui, glyph: char, label: &str, active: bool) -> Response {
    let colors = palette(ui);
    let icon_font = theme::icon_font(ui, 16.0);
    let text = WidgetText::from(label).into_galley(
        ui,
        Some(TextWrapMode::Extend),
        f32::INFINITY,
        TextStyle::Button,
    );
    let icon_width = if icon_font.is_some() { 24.0 } else { 0.0 };
    let size = vec2(text.size().x + icon_width + 20.0, CONTROL_HEIGHT);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
    response.widget_info(|| WidgetInfo::labeled(WidgetType::Button, ui.is_enabled(), label));
    if ui.is_rect_visible(rect) {
        let fill = if response.is_pointer_button_down_on() {
            Some(colors.pressed)
        } else if response.hovered() || active {
            Some(colors.hover)
        } else {
            None
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
                colors.accent,
            );
        }
        let position = pos2(
            rect.left() + 10.0 + icon_width,
            center_y - text.size().y / 2.0,
        );
        let color = if active { colors.accent } else { colors.text };
        ui.painter().galley(position, text, color);
    }
    response
}

/// Bouton réduit à son icône : le libellé reste dans l'infobulle et pour les lecteurs d'écran.
fn icon_button(ui: &mut Ui, glyph: char, label: &str) -> Response {
    let colors = palette(ui);
    let Some(font) = theme::icon_font(ui, 16.0) else {
        // Sans police d'icônes, le texte reste le seul moyen d'identifier le bouton.
        return ui.button(label);
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
        ui.painter().text(
            rect.center(),
            Align2::CENTER_CENTER,
            glyph,
            font,
            colors.accent,
        );
    }
    response.on_hover_text(label)
}

/// Ligne de liste à la manière d'un volet de navigation : une barre d'accent marque la sélection.
fn entry_row(ui: &mut Ui, site: &str, username: &str, selected: bool) -> Response {
    let colors = palette(ui);
    let size = vec2(ui.available_width(), LIST_ROW_HEIGHT);
    let (rect, response) = ui.allocate_exact_size(size, Sense::click());
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

fn text_field(ui: &mut Ui, label: &str, value: &mut String) {
    let label = ui.label(label);
    ui.add(
        TextEdit::singleline(value)
            .desired_width(f32::INFINITY)
            .margin(vec2(10.0, 6.0)),
    )
    .labelled_by(label.id);
}

/// Renvoie vrai si la touche Entrée valide le champ.
fn secret_field(ui: &mut Ui, label: &str, value: &mut Zeroizing<String>) -> bool {
    let label = ui.label(label);
    let response = ui
        .add(
            TextEdit::singleline(&mut **value)
                .password(true)
                .desired_width(f32::INFINITY)
                .margin(vec2(10.0, 6.0)),
        )
        .labelled_by(label.id);
    response.lost_focus() && ui.input(|input| input.key_pressed(Key::Enter))
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
        click(&mut harness, "Créer un compte");
        type_into(&mut harness, "Utilisateur", "alice");
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
        type_into(&mut harness, "Utilisateur", "alice");
        type_into(&mut harness, "Mot de passe maître", "mauvais mot de passe");
        click(&mut harness, "Se connecter");
        assert!(harness.state().workspace.is_none());
        assert!(harness.query_by_label("Identifiants invalides").is_some());
    }

    #[test]
    fn registration_rejects_a_mismatched_confirmation() {
        let mut harness = harness();
        harness.step();
        click(&mut harness, "Créer un compte");
        type_into(&mut harness, "Utilisateur", "alice");
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
