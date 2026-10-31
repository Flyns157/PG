//! État et écrans de l'interface en terminal.

use std::path::Path;
use std::time::Instant;

use ratatui::Frame;
use ratatui::buffer::Buffer;
use ratatui::crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, List, ListItem, ListState, Paragraph, Wrap};

use super::form::{Field, Form};
use crate::IDLE_LOCK;
use crate::clipboard::SecretClipboard;
use crate::csv_io;
use crate::entry::{Entry, EntryFields};
use crate::error::{Error, Result};
use crate::generator::{DEFAULT_LENGTH, generate_password};
use crate::mcp::{self, McpServer};
use crate::store::Store;
use crate::workspace::Workspace;

const SUBMIT_HINT: &str =
    "Entrée : valider · Tab : champ suivant · Ctrl+R : afficher · Échap : retour";
const ENTRY_HINT: &str =
    "Entrée : valider · Tab : suivant · Ctrl+G : générer · Ctrl+R : afficher · Échap : retour";
const LIST_HINT: &str = "/ chercher · v afficher · c copier · u identifiant · a ajouter · e modifier · d supprimer · i importer · x exporter · m maître · p MCP · P jeton MCP · l verrouiller · q quitter";

#[derive(Clone)]
enum FormKind {
    Login,
    Register,
    NewEntry,
    EditEntry(String),
    ChangeMaster,
    Import,
    Export,
}

enum Submitted {
    Unlocked(Workspace),
    Saved { id: String, message: String },
    Done(String),
}

enum Screen {
    Form(FormKind, Form),
    List { searching: bool, revealed: bool },
    ConfirmDelete,
}

pub struct App {
    store: Store,
    clipboard: SecretClipboard,
    mcp: Option<McpServer>,
    workspace: Option<Workspace>,
    screen: Screen,
    status: Option<(String, bool)>,
    last_activity: Instant,
    quit: bool,
}

impl App {
    pub fn new(store: Store) -> Self {
        Self {
            store,
            clipboard: SecretClipboard::default(),
            mcp: None,
            workspace: None,
            screen: login_screen(),
            status: None,
            last_activity: Instant::now(),
            quit: false,
        }
    }

    pub fn should_quit(&self) -> bool {
        self.quit
    }

    pub fn tick(&mut self) {
        self.clipboard.tick();
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
    }

    fn toggle_mcp(&mut self) {
        match mcp::toggle(&mut self.mcp, &mut self.clipboard, Box::new(|| {})) {
            Ok(message) => self.set_info(message),
            Err(error) => self.set_error(error),
        }
    }

    fn copy_mcp_token(&mut self) {
        if let Some(server) = &self.mcp {
            let message = mcp::copy_token(server, &mut self.clipboard);
            self.set_info(message);
        } else {
            self.set_info("Le serveur MCP est désactivé");
        }
    }

    fn lock(&mut self) {
        self.workspace = None;
        self.mcp = None;
        self.clipboard.clear();
        self.screen = login_screen();
        self.status = None;
    }

    fn set_info(&mut self, message: impl Into<String>) {
        self.status = Some((message.into(), false));
    }

    fn set_error(&mut self, error: impl ToString) {
        self.status = Some((error.to_string(), true));
    }

    pub fn handle_key(&mut self, key: KeyEvent) {
        self.last_activity = Instant::now();
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            self.quit = true;
            return;
        }
        match self.screen {
            Screen::Form(..) => self.handle_form_key(key),
            Screen::List {
                searching: true, ..
            } => self.handle_search_key(key),
            Screen::List { .. } => self.handle_list_key(key),
            Screen::ConfirmDelete => self.handle_confirm_key(key),
        }
    }

    fn handle_form_key(&mut self, key: KeyEvent) {
        let Screen::Form(kind, form) = &mut self.screen else {
            return;
        };
        let control = key.modifiers.contains(KeyModifiers::CONTROL);
        match (key.code, kind.clone()) {
            (KeyCode::Enter, _) => self.submit_form(),
            (KeyCode::Esc, FormKind::Login | FormKind::Register) => self.quit = true,
            (KeyCode::F(2), FormKind::Register) => {
                self.screen = login_screen();
                self.status = None;
            }
            (KeyCode::Esc, _) => {
                self.back_to_list();
                self.status = None;
            }
            (KeyCode::F(2), FormKind::Login) => {
                self.screen = register_screen();
                self.status = None;
            }
            (KeyCode::Char('g'), FormKind::NewEntry | FormKind::EditEntry(_)) if control => {
                let password = &mut form.fields[PASSWORD_FIELD];
                password.set(&generate_password(DEFAULT_LENGTH));
                password.reveal();
            }
            (KeyCode::Char('r'), _) if control => form.toggle_reveal(),
            (KeyCode::Char(_), _) if control => {}
            _ => form.handle_key(key),
        }
    }

    fn submit_form(&mut self) {
        let Screen::Form(kind, _) = &self.screen else {
            return;
        };
        let kind = kind.clone();
        let outcome = match kind {
            FormKind::Login | FormKind::Register => self.unlock(&kind).map(Submitted::Unlocked),
            FormKind::NewEntry => self.save_entry(None),
            FormKind::EditEntry(ref id) => self.save_entry(Some(id)),
            FormKind::ChangeMaster => self.change_master(),
            FormKind::Import => self.import(),
            FormKind::Export => self.export(),
        };
        match outcome {
            Ok(Submitted::Unlocked(workspace)) => {
                self.workspace = Some(workspace);
                self.status = None;
                self.back_to_list();
            }
            Ok(Submitted::Saved { id, message }) => {
                self.back_to_list();
                if let Some(workspace) = &mut self.workspace {
                    workspace.select_id(&id);
                }
                self.set_info(message);
            }
            Ok(Submitted::Done(message)) => {
                self.back_to_list();
                self.set_info(message);
            }
            Err(error) => self.set_error(error),
        }
    }

    fn unlock(&self, kind: &FormKind) -> Result<Workspace> {
        let Screen::Form(_, form) = &self.screen else {
            return Err(no_form());
        };
        let session = if matches!(kind, FormKind::Login) {
            self.store.login(form.value(0), form.value(1))?
        } else {
            if form.value(1) != form.value(2) {
                return Err(mismatch());
            }
            self.store.register(form.value(0), form.value(1))?
        };
        Workspace::open(&self.store, session)
    }

    fn open_form(&self) -> Result<(&Form, &Workspace)> {
        match (&self.screen, &self.workspace) {
            (Screen::Form(_, form), Some(workspace)) => Ok((form, workspace)),
            _ => Err(no_form()),
        }
    }

    fn save_entry(&self, id: Option<&str>) -> Result<Submitted> {
        let (form, workspace) = self.open_form()?;
        let fields = entry_fields(form);
        let entry = match id {
            Some(id) => self.store.update(&workspace.session, id, fields)?,
            None => self.store.add(&workspace.session, fields)?,
        };
        Ok(Submitted::Saved {
            message: format!("Entrée enregistrée : {}", entry.fields.url),
            id: entry.id.clone(),
        })
    }

    fn change_master(&self) -> Result<Submitted> {
        let (form, workspace) = self.open_form()?;
        if form.value(1) != form.value(2) {
            return Err(mismatch());
        }
        self.store
            .change_master_password(&workspace.session, form.value(0), form.value(1))?;
        Ok(Submitted::Done("Mot de passe maître modifié".to_owned()))
    }

    fn import(&mut self) -> Result<Submitted> {
        let (form, _) = self.open_form()?;
        let records = csv_io::import_from_file(Path::new(form.value(0)))?;
        let Some(workspace) = &self.workspace else {
            return Err(no_form());
        };
        let report = self.store.import(&workspace.session, records)?;
        Ok(Submitted::Done(format!(
            "{} entrée(s) importée(s), {} doublon(s) ignoré(s)",
            report.imported, report.duplicates
        )))
    }

    fn export(&self) -> Result<Submitted> {
        let (form, workspace) = self.open_form()?;
        csv_io::export_to_file(workspace.all_entries(), Path::new(form.value(0)))?;
        Ok(Submitted::Done(format!(
            "Export EN CLAIR écrit dans {}",
            form.value(0)
        )))
    }

    fn back_to_list(&mut self) {
        self.screen = Screen::List {
            searching: false,
            revealed: false,
        };
        if let Some(workspace) = &mut self.workspace
            && let Err(error) = workspace.reload(&self.store)
        {
            self.status = Some((error.to_string(), true));
        }
    }

    fn handle_search_key(&mut self, key: KeyEvent) {
        let Some(workspace) = &mut self.workspace else {
            return;
        };
        let mut query = workspace.query().to_owned();
        match key.code {
            KeyCode::Esc => {
                workspace.set_query("");
                self.screen = Screen::List {
                    searching: false,
                    revealed: false,
                };
            }
            KeyCode::Enter => {
                self.screen = Screen::List {
                    searching: false,
                    revealed: false,
                }
            }
            KeyCode::Up => workspace.move_selection(-1),
            KeyCode::Down => workspace.move_selection(1),
            KeyCode::Backspace => {
                query.pop();
                workspace.set_query(&query);
            }
            KeyCode::Char(character) if !key.modifiers.contains(KeyModifiers::CONTROL) => {
                query.push(character);
                workspace.set_query(&query);
            }
            _ => {}
        }
    }

    fn handle_list_key(&mut self, key: KeyEvent) {
        self.status = None;
        let Some(workspace) = &mut self.workspace else {
            return;
        };
        match key.code {
            KeyCode::Up | KeyCode::Char('k') => {
                workspace.move_selection(-1);
                self.hide_password();
            }
            KeyCode::Down | KeyCode::Char('j') => {
                workspace.move_selection(1);
                self.hide_password();
            }
            KeyCode::Char('/') => {
                self.screen = Screen::List {
                    searching: true,
                    revealed: false,
                }
            }
            KeyCode::Char('v') | KeyCode::Enter => {
                if let Screen::List { revealed, .. } = &mut self.screen {
                    *revealed = !*revealed;
                }
            }
            KeyCode::Char('c') => self.copy(
                |entry| &entry.fields.password,
                "Mot de passe copié (effacé dans 30 s)",
            ),
            KeyCode::Char('u') => self.copy(
                |entry| &entry.fields.username,
                "Identifiant copié (effacé dans 30 s)",
            ),
            KeyCode::Char('a') => {
                self.screen = Screen::Form(FormKind::NewEntry, entry_form("Nouvelle entrée", None))
            }
            KeyCode::Char('e') => {
                if let Some(entry) = workspace.selected() {
                    let form = entry_form("Modifier l'entrée", Some(entry));
                    self.screen = Screen::Form(FormKind::EditEntry(entry.id.clone()), form);
                }
            }
            KeyCode::Char('d') if workspace.selected().is_some() => {
                self.screen = Screen::ConfirmDelete
            }
            KeyCode::Char('i') => {
                let form = Form::new("Importer un CSV", SUBMIT_HINT, vec![Field::text("Fichier")]);
                self.screen = Screen::Form(FormKind::Import, form);
            }
            KeyCode::Char('x') => {
                let form = Form::new(
                    "Exporter EN CLAIR : tout lecteur du fichier verra les mots de passe",
                    SUBMIT_HINT,
                    vec![Field::text("Fichier")],
                );
                self.screen = Screen::Form(FormKind::Export, form);
            }
            KeyCode::Char('m') => {
                let fields = vec![
                    Field::secret("Actuel"),
                    Field::secret("Nouveau"),
                    Field::secret("Confirmer"),
                ];
                self.screen = Screen::Form(
                    FormKind::ChangeMaster,
                    Form::new("Changer le mot de passe maître", SUBMIT_HINT, fields),
                );
            }
            KeyCode::Char('p') => self.toggle_mcp(),
            KeyCode::Char('P') => self.copy_mcp_token(),
            KeyCode::Char('l') => self.lock(),
            KeyCode::Char('q') | KeyCode::Esc => self.quit = true,
            _ => {}
        }
    }

    fn hide_password(&mut self) {
        if let Screen::List { revealed, .. } = &mut self.screen {
            *revealed = false;
        }
    }

    fn copy(&mut self, field: impl Fn(&Entry) -> &String, message: &str) {
        let Some(text) = self
            .workspace
            .as_ref()
            .and_then(|workspace| workspace.selected())
            .map(|entry| field(entry).clone())
        else {
            return;
        };
        match self.clipboard.copy(&text) {
            Ok(()) => self.set_info(message),
            Err(error) => self.set_error(format!("Presse-papiers indisponible : {error}")),
        }
    }

    fn handle_confirm_key(&mut self, key: KeyEvent) {
        if key.code == KeyCode::Char('o') {
            let Some(workspace) = &self.workspace else {
                return;
            };
            let Some(entry) = workspace.selected() else {
                return;
            };
            let outcome = self.store.delete(&workspace.session, &entry.id);
            self.back_to_list();
            match outcome {
                Ok(()) => self.set_info("Entrée supprimée"),
                Err(error) => self.set_error(error),
            }
        } else {
            self.screen = Screen::List {
                searching: false,
                revealed: false,
            };
        }
    }

    pub fn render(&self, frame: &mut Frame) {
        self.draw(frame);
        strip_terminal_controls(frame.buffer_mut());
    }

    fn draw(&self, frame: &mut Frame) {
        let status = self.status.as_ref().map(|(message, is_error)| {
            let color = if *is_error { Color::Red } else { Color::Green };
            Line::styled(message.clone(), Style::new().fg(color))
        });
        match &self.screen {
            Screen::Form(_, form) => form.render(frame, status.as_ref()),
            Screen::List {
                searching,
                revealed,
            } => self.render_list(frame, *searching, *revealed, status.as_ref()),
            Screen::ConfirmDelete => {
                self.render_list(frame, false, false, None);
                let site = self
                    .workspace
                    .as_ref()
                    .and_then(|workspace| workspace.selected())
                    .map_or("", |entry| &entry.fields.url);
                let message = Line::styled(
                    format!("Supprimer {site} ? o : oui · autre touche : non"),
                    Style::new().fg(Color::Yellow),
                );
                let [_, line, _] = Layout::vertical([
                    Constraint::Fill(1),
                    Constraint::Length(1),
                    Constraint::Length(1),
                ])
                .areas(frame.area());
                frame.render_widget(Paragraph::new(message), line);
            }
        }
    }

    fn render_list(
        &self,
        frame: &mut Frame,
        searching: bool,
        revealed: bool,
        status: Option<&Line<'_>>,
    ) {
        let Some(workspace) = &self.workspace else {
            return;
        };
        let [header, search, body, status_area, hint] = Layout::vertical([
            Constraint::Length(1),
            Constraint::Length(3),
            Constraint::Fill(1),
            Constraint::Length(1),
            Constraint::Length(3),
        ])
        .areas(frame.area());

        let title = format!(
            "PG · {} · {} entrée(s){}",
            workspace.session.username(),
            workspace.all_entries().len(),
            if self.mcp.is_some() {
                " · MCP actif"
            } else {
                ""
            }
        );
        frame.render_widget(
            Paragraph::new(title).style(Style::new().add_modifier(Modifier::BOLD)),
            header,
        );

        let search_border = if searching {
            Style::new().fg(Color::Cyan)
        } else {
            Style::new()
        };
        let search_box = Paragraph::new(workspace.query()).block(
            Block::bordered()
                .title(" Recherche ")
                .border_style(search_border),
        );
        frame.render_widget(search_box, search);

        let [list_area, detail_area] =
            Layout::horizontal([Constraint::Percentage(45), Constraint::Percentage(55)])
                .areas(body);
        let items: Vec<ListItem> = workspace
            .visible()
            .map(|entry| ListItem::new(format!("{} ({})", entry.fields.url, entry.fields.username)))
            .collect();
        let empty = items.is_empty();
        let list = List::new(items)
            .block(Block::bordered().title(" Entrées "))
            .highlight_style(Style::new().add_modifier(Modifier::REVERSED));
        let mut state =
            ListState::default().with_selected((!empty).then(|| workspace.selected_position()));
        frame.render_stateful_widget(list, list_area, &mut state);
        render_detail(frame, detail_area, workspace.selected(), revealed);

        if let Some(status) = status {
            frame.render_widget(Paragraph::new(status.clone()), status_area);
        }
        let hint_text = if searching {
            "Entrée : garder le filtre · Échap : effacer"
        } else {
            LIST_HINT
        };
        frame.render_widget(
            Paragraph::new(hint_text)
                .wrap(Wrap { trim: true })
                .style(Style::new().fg(Color::DarkGray)),
            hint,
        );
    }
}

fn render_detail(frame: &mut Frame, area: Rect, entry: Option<&Entry>, revealed: bool) {
    let block = Block::bordered().title(" Détail ");
    let Some(entry) = entry else {
        frame.render_widget(Paragraph::new("Aucune entrée").block(block), area);
        return;
    };
    let fields = &entry.fields;
    let password = if revealed {
        fields.password.clone()
    } else {
        "•".repeat(8)
    };
    let dates = |date: chrono::DateTime<chrono::Utc>| {
        date.with_timezone(&chrono::Local)
            .format("%d/%m/%Y %H:%M")
            .to_string()
    };
    let lines = [
        ("Site", fields.url.clone()),
        ("Identifiant", fields.username.clone()),
        ("Mot de passe", password),
        ("E-mail", fields.email.clone()),
        ("Téléphone", fields.phone.clone()),
        ("Notes", fields.notes.clone()),
        ("Créée le", dates(entry.created_at)),
        ("Modifiée le", dates(entry.updated_at)),
    ]
    .map(|(label, value)| Line::from(format!("{label:<13}{value}")));
    frame.render_widget(
        Paragraph::new(lines.to_vec())
            .wrap(Wrap { trim: false })
            .block(block),
        area,
    );
}

/// Un CSV importé ne doit pas pouvoir piloter le terminal : ratatui écrit ces caractères tels quels.
fn strip_terminal_controls(buffer: &mut Buffer) {
    for cell in &mut buffer.content {
        if cell.symbol().chars().any(is_terminal_control) {
            let clean: String = cell
                .symbol()
                .chars()
                .filter(|&c| !is_terminal_control(c))
                .collect();
            cell.set_symbol(if clean.is_empty() { " " } else { &clean });
        }
    }
}

fn is_terminal_control(character: char) -> bool {
    character.is_control() || matches!(character, '\u{202A}'..='\u{202E}' | '\u{2066}'..='\u{2069}')
}

const PASSWORD_FIELD: usize = 2;

fn entry_form(title: &str, entry: Option<&Entry>) -> Form {
    let default = EntryFields::default();
    let fields = entry.map_or(&default, |entry| &entry.fields);
    Form::new(
        title,
        ENTRY_HINT,
        vec![
            Field::text("Site").with_value(&fields.url),
            Field::text("Identifiant").with_value(&fields.username),
            Field::secret("Mot de passe").with_value(&fields.password),
            Field::text("E-mail").with_value(&fields.email),
            Field::text("Téléphone").with_value(&fields.phone),
            Field::text("Notes").with_value(&fields.notes),
        ],
    )
}

fn entry_fields(form: &Form) -> EntryFields {
    let mut fields = EntryFields::new(form.value(0), form.value(1), form.value(PASSWORD_FIELD));
    fields.email = form.value(3).to_owned();
    fields.phone = form.value(4).to_owned();
    fields.notes = form.value(5).to_owned();
    fields
}

fn login_screen() -> Screen {
    let hint = "Entrée : valider · Tab : champ suivant · F2 : créer un compte · Échap : quitter";
    let fields = vec![Field::text("Compte"), Field::secret("Mot de passe maître")];
    Screen::Form(FormKind::Login, Form::new("PG · Connexion", hint, fields))
}

fn register_screen() -> Screen {
    let hint = "Entrée : valider · Tab : champ suivant · Ctrl+R : afficher · F2 : se connecter · Échap : quitter";
    let fields = vec![
        Field::text("Compte"),
        Field::secret("Mot de passe maître"),
        Field::secret("Confirmer"),
    ];
    Screen::Form(
        FormKind::Register,
        Form::new("PG · Créer un compte", hint, fields),
    )
}

fn mismatch() -> Error {
    Error::Validation("Les deux mots de passe diffèrent".to_owned())
}

fn no_form() -> Error {
    Error::Validation("Aucun formulaire ouvert".to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::store::FAST_KDF;
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    const MASTER: &str = "correct horse battery";

    fn press(app: &mut App, code: KeyCode) {
        app.handle_key(KeyEvent::new(code, KeyModifiers::NONE));
    }

    fn control(app: &mut App, character: char) {
        app.handle_key(KeyEvent::new(
            KeyCode::Char(character),
            KeyModifiers::CONTROL,
        ));
    }

    fn type_text(app: &mut App, text: &str) {
        text.chars()
            .for_each(|character| press(app, KeyCode::Char(character)));
    }

    fn fill(app: &mut App, values: &[&str]) {
        for value in values {
            type_text(app, value);
            press(app, KeyCode::Tab);
        }
        press(app, KeyCode::Enter);
    }

    fn screen(app: &App) -> String {
        let mut terminal = Terminal::new(TestBackend::new(140, 30)).unwrap();
        terminal.draw(|frame| app.render(frame)).unwrap();
        let buffer = terminal.backend().buffer().clone();
        buffer
            .content()
            .chunks(140)
            .map(|row| row.iter().map(|cell| cell.symbol()).collect::<String>() + "\n")
            .collect()
    }

    #[test]
    fn login_hint_is_complete_at_the_bottom_of_the_screen() {
        let app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        let mut terminal = Terminal::new(TestBackend::new(80, 24)).unwrap();
        terminal.draw(|frame| app.render(frame)).unwrap();
        let bottom: String = terminal.backend().buffer().content()[80 * 22..]
            .iter()
            .map(|cell| cell.symbol())
            .collect();
        assert!(bottom.contains("F2 : créer un compte · Échap : quitter"));
    }

    #[test]
    fn f2_switches_between_login_and_register() {
        let mut app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        press(&mut app, KeyCode::F(2));
        assert!(screen(&app).contains("PG · Créer un compte"));
        assert!(screen(&app).contains("F2 : se connecter"));
        press(&mut app, KeyCode::F(2));
        assert!(screen(&app).contains("PG · Connexion"));
    }

    #[test]
    fn escape_quits_from_register() {
        let mut app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        press(&mut app, KeyCode::F(2));
        assert!(screen(&app).contains("Échap : quitter"));
        press(&mut app, KeyCode::Esc);
        assert!(app.quit);
    }

    #[test]
    fn form_box_has_no_empty_line_without_status() {
        let app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        let mut terminal = Terminal::new(TestBackend::new(80, 24)).unwrap();
        terminal.draw(|frame| app.render(frame)).unwrap();
        let rows: Vec<String> = terminal
            .backend()
            .buffer()
            .content()
            .chunks(80)
            .map(|row| row.iter().map(|cell| cell.symbol()).collect())
            .collect();
        let last_field = rows
            .iter()
            .position(|row| row.contains("Mot de passe maître"))
            .unwrap();
        assert!(rows[last_field + 1].contains('└'));
    }

    #[test]
    fn p_starts_then_stops_the_mcp_server() {
        let mut app = registered_app();
        assert!(app.mcp.is_none());
        press(&mut app, KeyCode::Char('p'));
        assert!(screen(&app).contains("MCP actif"), "{}", screen(&app));
        let server = app.mcp.as_ref().unwrap();
        let url = server.url().to_owned();
        let body = r#"{"jsonrpc":"2.0","method":"notifications/initialized"}"#;
        assert_eq!(mcp::post(&url, server.token(), body).0, 202);
        press(&mut app, KeyCode::Char('p'));
        assert!(app.mcp.is_none());
        assert!(!screen(&app).contains("MCP actif"));
        assert!(std::net::TcpStream::connect(("127.0.0.1", mcp::PORT)).is_err());
    }

    fn assert_no_terminal_control(app: &App) {
        let mut terminal = Terminal::new(TestBackend::new(140, 30)).unwrap();
        terminal.draw(|frame| app.render(frame)).unwrap();
        let symbols = terminal.backend().buffer().content().iter();
        assert!(
            symbols
                .into_iter()
                .all(|cell| !cell.symbol().chars().any(is_terminal_control))
        );
    }

    #[test]
    fn control_characters_never_reach_the_terminal() {
        let mut app = registered_app();
        add_entry(&mut app, "a\x1b]0;PWNED\x07b\u{202e}c", "p1");
        assert_no_terminal_control(&app);
        assert!(screen(&app).contains("]0;PWNED"));
        press(&mut app, KeyCode::Char('e'));
        assert_no_terminal_control(&app);
    }

    #[test]
    fn locking_stops_the_mcp_server() {
        let mut app = registered_app();
        app.mcp = Some(McpServer::start_on(0, Box::new(|| {})).unwrap());
        let url = app.mcp.as_ref().unwrap().url().to_owned();
        let address = url
            .trim_start_matches("http://")
            .trim_end_matches("/mcp")
            .to_owned();
        press(&mut app, KeyCode::Char('l'));
        assert!(app.mcp.is_none());
        assert!(std::net::TcpStream::connect(address).is_err());
    }

    fn registered_app() -> App {
        let mut app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        press(&mut app, KeyCode::F(2));
        fill(&mut app, &["alice", MASTER, MASTER]);
        assert!(screen(&app).contains("alice"), "{}", screen(&app));
        app
    }

    fn add_entry(app: &mut App, site: &str, password: &str) {
        press(app, KeyCode::Char('a'));
        fill(app, &[site, "moi", password, "", "", ""]);
    }

    #[test]
    fn registration_rejects_a_mismatched_confirmation() {
        let mut app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        press(&mut app, KeyCode::F(2));
        fill(&mut app, &["alice", MASTER, "autre chose"]);
        assert!(screen(&app).contains("diffèrent"));
    }

    #[test]
    fn password_stays_masked_until_revealed_and_hides_on_move() {
        let mut app = registered_app();
        add_entry(&mut app, "https://a.example", "secret-visible");
        assert!(screen(&app).contains("https://a.example"));
        assert!(!screen(&app).contains("secret-visible"));
        press(&mut app, KeyCode::Char('v'));
        assert!(screen(&app).contains("secret-visible"));
        press(&mut app, KeyCode::Down);
        assert!(!screen(&app).contains("secret-visible"));
    }

    #[test]
    fn master_password_is_never_displayed_while_typing() {
        let mut app = App::new(Store::open_in_memory().unwrap().with_kdf(FAST_KDF));
        type_text(&mut app, "alice");
        press(&mut app, KeyCode::Tab);
        type_text(&mut app, MASTER);
        assert!(!screen(&app).contains(MASTER));
        control(&mut app, 'r');
        assert!(screen(&app).contains(MASTER));
    }

    #[test]
    fn invalid_entry_keeps_the_form_open_with_its_content() {
        let mut app = registered_app();
        press(&mut app, KeyCode::Char('a'));
        fill(&mut app, &["https://a.example", "moi", "", "", "", ""]);
        let display = screen(&app);
        assert!(display.contains("Le mot de passe est obligatoire"));
        assert!(display.contains("https://a.example"));
    }

    #[test]
    fn generated_password_fills_the_form() {
        let mut app = registered_app();
        press(&mut app, KeyCode::Char('a'));
        control(&mut app, 'g');
        let Screen::Form(_, form) = &app.screen else {
            panic!("formulaire attendu")
        };
        assert_eq!(form.value(PASSWORD_FIELD).chars().count(), DEFAULT_LENGTH);
    }

    #[test]
    fn search_filters_and_escape_clears() {
        let mut app = registered_app();
        add_entry(&mut app, "https://github.example", "p1");
        add_entry(&mut app, "https://impots.example", "p2");
        press(&mut app, KeyCode::Char('/'));
        type_text(&mut app, "impots");
        let display = screen(&app);
        assert!(display.contains("impots.example"));
        assert!(!display.contains("github.example"));
        press(&mut app, KeyCode::Esc);
        assert!(screen(&app).contains("github.example"));
    }

    #[test]
    fn edit_updates_the_selected_entry() {
        let mut app = registered_app();
        add_entry(&mut app, "https://a.example", "p1");
        press(&mut app, KeyCode::Char('e'));
        type_text(&mut app, "/nouveau");
        press(&mut app, KeyCode::Enter);
        let workspace = app.workspace.as_ref().unwrap();
        assert_eq!(workspace.all_entries().len(), 1);
        assert_eq!(
            workspace.all_entries()[0].fields.url,
            "https://a.example/nouveau"
        );
        assert_eq!(workspace.all_entries()[0].fields.password, "p1");
    }

    #[test]
    fn delete_requires_confirmation() {
        let mut app = registered_app();
        add_entry(&mut app, "https://a.example", "p1");
        press(&mut app, KeyCode::Char('d'));
        assert!(screen(&app).contains("Supprimer"));
        press(&mut app, KeyCode::Char('n'));
        assert_eq!(app.workspace.as_ref().unwrap().all_entries().len(), 1);
        press(&mut app, KeyCode::Char('d'));
        press(&mut app, KeyCode::Char('o'));
        assert!(app.workspace.as_ref().unwrap().all_entries().is_empty());
    }

    #[test]
    fn export_then_import_reports_duplicates() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("e.csv");
        let path = path.to_str().unwrap();
        let mut app = registered_app();
        add_entry(&mut app, "https://a.example", "p1");
        press(&mut app, KeyCode::Char('x'));
        assert!(screen(&app).contains("EN CLAIR"));
        fill(&mut app, &[path]);
        assert!(screen(&app).contains("EN CLAIR"));
        press(&mut app, KeyCode::Char('i'));
        fill(&mut app, &[path]);
        assert!(
            screen(&app).contains("0 entrée(s) importée(s), 1 doublon(s)"),
            "{}",
            screen(&app)
        );
    }

    #[test]
    fn locking_forgets_the_session_and_requires_the_password() {
        let mut app = registered_app();
        add_entry(&mut app, "https://a.example", "p1");
        press(&mut app, KeyCode::Char('l'));
        assert!(app.workspace.is_none());
        assert!(!screen(&app).contains("https://a.example"));
        fill(&mut app, &["alice", "mauvais mot de passe"]);
        assert!(screen(&app).contains("Compte ou mot de passe incorrect"));
        assert!(app.workspace.is_none());
    }

    #[test]
    fn idle_timeout_locks_the_vault() {
        let mut app = registered_app();
        app.last_activity = Instant::now() - IDLE_LOCK;
        app.tick();
        assert!(app.workspace.is_none());
        assert!(screen(&app).contains("verrouillé"));
    }

    #[test]
    fn changing_master_password_requires_matching_confirmation() {
        let mut app = registered_app();
        press(&mut app, KeyCode::Char('m'));
        fill(
            &mut app,
            &[MASTER, "un nouveau secret!", "different secret!!"],
        );
        assert!(screen(&app).contains("diffèrent"));
    }
}
