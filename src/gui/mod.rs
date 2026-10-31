//! Interface graphique.

use std::path::Path;
use std::time::{Duration, Instant};

use eframe::egui;
use egui::{
    Align, Button, Color32, Context, Grid, Key, Layout, Modal, Modifiers, RichText, ScrollArea,
    TextEdit, Ui, vec2,
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

const TICK: Duration = Duration::from_secs(1);
const LOGIN_FORM_WIDTH: f32 = 450.0;
const LIST_ROW_HEIGHT: f32 = 26.0;

const ICON_PNG: &[u8] = include_bytes!("../../assets/icon.png");

pub fn run(store: Store) -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("PG")
            .with_inner_size([960.0, 600.0])
            .with_min_inner_size([640.0, 400.0])
            .with_icon(
                eframe::icon_data::from_png_bytes(ICON_PNG).expect("icône intégrée invalide"),
            ),
        ..Default::default()
    };
    eframe::run_native(
        "PG",
        options,
        Box::new(|_| Ok(Box::new(GuiApp::new(store)))),
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
                ui.add_space(ui.available_height() * 0.2);
                ui.heading(if self.login.registering {
                    "PG · Créer un compte"
                } else {
                    "PG · Connexion"
                });
                ui.add_space(16.0);
                let mut submitted = false;
                ui.horizontal(|ui| {
                    ui.add_space(((ui.available_width() - LOGIN_FORM_WIDTH) / 2.0).max(0.0));
                    Grid::new("login")
                        .num_columns(2)
                        .spacing([8.0, 8.0])
                        .show(ui, |ui| {
                            text_row(ui, "Utilisateur", &mut self.login.username);
                            submitted |= secret_row(
                                ui,
                                "Mot de passe maître",
                                &mut self.login.password,
                                false,
                            )
                            .submitted;
                            if self.login.registering {
                                submitted |=
                                    secret_row(ui, "Confirmer", &mut self.login.confirm, false)
                                        .submitted;
                            }
                        });
                });
                ui.add_space(8.0);
                submitted |= ui
                    .button(if self.login.registering {
                        "Créer le compte"
                    } else {
                        "Se connecter"
                    })
                    .clicked();
                let other = if self.login.registering {
                    "J'ai déjà un compte"
                } else {
                    "Créer un compte"
                };
                if ui.link(other).clicked() {
                    self.login.registering = !self.login.registering;
                    self.status = None;
                }
                if submitted {
                    self.submit_login();
                }
                ui.add_space(8.0);
                status_label(ui, self.status.as_ref());
            });
        });
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
        egui::TopBottomPanel::top("toolbar").show(ctx, |ui| self.toolbar_ui(ui));
        egui::TopBottomPanel::bottom("status")
            .show(ctx, |ui| status_label(ui, self.status.as_ref()));
        egui::SidePanel::left("entries")
            .default_width(380.0)
            .show(ctx, |ui| self.list_ui(ui));
        egui::CentralPanel::default().show(ctx, |ui| self.detail_ui(ui));
        self.dialog_ui(ctx);
    }

    fn toolbar_ui(&mut self, ui: &mut Ui) {
        ui.horizontal(|ui| {
            if let Some(workspace) = &mut self.workspace {
                ui.strong(format!(
                    "{} · {} entrée(s)",
                    workspace.session.username(),
                    workspace.all_entries().len()
                ));
                let label = ui.label("Recherche");
                let search = ui
                    .add(TextEdit::singleline(&mut self.search).desired_width(220.0))
                    .labelled_by(label.id)
                    .on_hover_text("Ctrl+F");
                if self.dialog.is_none()
                    && ui.input_mut(|input| input.consume_key(Modifiers::COMMAND, Key::F))
                {
                    search.request_focus();
                }
                if search.changed() {
                    workspace.set_query(&self.search);
                    self.revealed = false;
                }
            }
            ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                if ui.button("Verrouiller").clicked() {
                    self.lock();
                    return;
                }
                if let Some(server) = &self.mcp
                    && ui.button("Jeton MCP").on_hover_text(server.url()).clicked()
                {
                    let message = mcp::copy_token(server, &mut self.clipboard);
                    self.set_info(message);
                }
                if ui
                    .selectable_label(self.mcp.is_some(), "MCP")
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
                if ui.button("Mot de passe maître").clicked() {
                    self.dialog = Some(Dialog::ChangeMaster {
                        current: Zeroizing::default(),
                        new: Zeroizing::default(),
                        confirm: Zeroizing::default(),
                    });
                }
                if ui.button("Exporter").clicked() {
                    self.dialog = Some(Dialog::Export {
                        path: String::new(),
                    });
                }
                if ui.button("Importer").clicked() {
                    self.dialog = Some(Dialog::Import {
                        path: String::new(),
                    });
                }
                if ui.button("Ajouter").clicked() {
                    self.dialog = Some(Dialog::Entry {
                        id: None,
                        fields: EntryFields::default(),
                        revealed: false,
                    });
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
        ScrollArea::vertical().auto_shrink(false).show(ui, |ui| {
            // Lignes jointives : toute la largeur est cliquable, sans trou entre deux entrées.
            ui.spacing_mut().item_spacing.y = 0.0;
            for (position, entry) in workspace.visible().enumerate() {
                let text = format!("{} ({})", entry.fields.url, entry.fields.username);
                let row = Button::selectable(position == selected, text)
                    .truncate()
                    .min_size(vec2(ui.available_width(), LIST_ROW_HEIGHT));
                let response = ui.add(row);
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
            ui.label("Aucune entrée");
            return;
        };
        let fields = &entry.fields;
        Grid::new("detail")
            .num_columns(2)
            .spacing([12.0, 8.0])
            .show(ui, |ui| {
                detail_row(ui, "Site", &fields.url);
                detail_row(ui, "Identifiant", &fields.username);
                ui.label("Mot de passe");
                ui.monospace(if self.revealed {
                    fields.password.as_str()
                } else {
                    "••••••••"
                });
                ui.end_row();
                detail_row(ui, "E-mail", &fields.email);
                detail_row(ui, "Téléphone", &fields.phone);
                detail_row(ui, "Notes", &fields.notes);
                detail_row(ui, "Créée le", &local_date(&entry.created_at));
                detail_row(ui, "Modifiée le", &local_date(&entry.updated_at));
            });
        ui.add_space(12.0);
        ui.horizontal_wrapped(|ui| {
            if ui
                .button(if self.revealed { "Masquer" } else { "Afficher" })
                .clicked()
            {
                self.revealed = !self.revealed;
            }
            if ui.button("Copier le mot de passe").clicked() {
                self.copy(&fields.password, "Mot de passe copié (effacé dans 30 s)");
            }
            if ui.button("Copier l'identifiant").clicked() {
                self.copy(&fields.username, "Identifiant copié (effacé dans 30 s)");
            }
            if ui.button("Modifier").clicked() {
                self.dialog = Some(Dialog::Entry {
                    id: Some(entry.id.clone()),
                    fields: fields.clone(),
                    revealed: false,
                });
            }
            if ui.button("Supprimer").clicked() {
                self.dialog = Some(Dialog::Delete {
                    id: entry.id.clone(),
                    site: fields.url.clone(),
                });
            }
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
            ui.set_width(460.0);
            let mut action = dialog_content(ui, &mut dialog);
            if let Some(error) = &error {
                ui.colored_label(Color32::LIGHT_RED, error);
            }
            ui.add_space(8.0);
            ui.horizontal(|ui| {
                let submit = if matches!(dialog, Dialog::Delete { .. }) {
                    "Confirmer la suppression"
                } else {
                    "Valider"
                };
                if ui.button(submit).clicked() {
                    action = DialogAction::Submit;
                }
                if ui.button("Annuler").clicked() {
                    action = DialogAction::Close;
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
            Grid::new("entry")
                .num_columns(2)
                .spacing([8.0, 8.0])
                .show(ui, |ui| {
                    text_row(ui, "Site", &mut fields.url);
                    text_row(ui, "Identifiant", &mut fields.username);
                    let label = ui.label("Mot de passe");
                    ui.horizontal(|ui| {
                        ui.add(
                            TextEdit::singleline(&mut fields.password)
                                .password(!*revealed)
                                .desired_width(240.0),
                        )
                        .labelled_by(label.id);
                        ui.checkbox(revealed, "Afficher");
                        if ui.button("Générer").clicked() {
                            fields.password = generate_password(DEFAULT_LENGTH);
                            *revealed = true;
                        }
                    });
                    ui.end_row();
                    text_row(ui, "E-mail", &mut fields.email);
                    text_row(ui, "Téléphone", &mut fields.phone);
                    text_row(ui, "Notes", &mut fields.notes);
                });
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
            Grid::new("master")
                .num_columns(2)
                .spacing([8.0, 8.0])
                .show(ui, |ui| {
                    submitted |= secret_row(ui, "Actuel", current, false).submitted;
                    submitted |= secret_row(ui, "Nouveau", new, false).submitted;
                    submitted |= secret_row(ui, "Confirmer", confirm, false).submitted;
                });
        }
        Dialog::Import { path } => {
            ui.heading("Importer un CSV");
            Grid::new("import")
                .num_columns(2)
                .show(ui, |ui| text_row(ui, "Fichier", path));
        }
        Dialog::Export { path } => {
            ui.heading("Exporter en CSV");
            ui.colored_label(
                Color32::YELLOW,
                "L'export est EN CLAIR : tout lecteur du fichier verra les mots de passe.",
            );
            Grid::new("export")
                .num_columns(2)
                .show(ui, |ui| text_row(ui, "Fichier", path));
        }
    }
    if submitted {
        DialogAction::Submit
    } else {
        DialogAction::Keep
    }
}

struct RowResponse {
    submitted: bool,
}

fn text_row(ui: &mut Ui, label: &str, value: &mut String) {
    let label = ui.label(label);
    ui.add(TextEdit::singleline(value).desired_width(320.0))
        .labelled_by(label.id);
    ui.end_row();
}

fn secret_row(
    ui: &mut Ui,
    label: &str,
    value: &mut Zeroizing<String>,
    revealed: bool,
) -> RowResponse {
    let label = ui.label(label);
    let response = ui
        .add(
            TextEdit::singleline(&mut **value)
                .password(!revealed)
                .desired_width(320.0),
        )
        .labelled_by(label.id);
    ui.end_row();
    RowResponse {
        submitted: response.lost_focus() && ui.input(|input| input.key_pressed(Key::Enter)),
    }
}

fn detail_row(ui: &mut Ui, label: &str, value: &str) {
    ui.label(label);
    ui.add(egui::Label::new(RichText::new(value)).wrap());
    ui.end_row();
}

fn status_label(ui: &mut Ui, status: Option<&(String, bool)>) {
    if let Some((message, is_error)) = status {
        ui.colored_label(
            if *is_error {
                Color32::LIGHT_RED
            } else {
                Color32::LIGHT_GREEN
            },
            message,
        );
    }
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
        Harness::new_state(|ctx, app: &mut GuiApp| app.ui(ctx), GuiApp::new(store))
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
