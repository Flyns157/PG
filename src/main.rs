#![cfg_attr(
    all(windows, feature = "gui", not(feature = "tui")),
    windows_subsystem = "windows"
)]

#[cfg(not(any(feature = "tui", feature = "gui")))]
compile_error!("Activez au moins une interface : la feature `tui` ou `gui`.");

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, ValueEnum};
use pg::store::Store;

#[derive(Clone, Copy, Debug, ValueEnum)]
enum Interface {
    #[cfg(feature = "tui")]
    Tui,
    #[cfg(feature = "gui")]
    Gui,
}

impl Default for Interface {
    fn default() -> Self {
        #[cfg(feature = "gui")]
        return Self::Gui;
        #[cfg(not(feature = "gui"))]
        return Self::Tui;
    }
}

#[derive(Parser)]
#[command(
    version,
    about = "Gestionnaire de mots de passe local, à coffre SQLite chiffré"
)]
struct Cli {
    /// Interface à lancer (par défaut : la GUI si elle est compilée)
    #[arg(short, long, value_enum)]
    interface: Option<Interface>,

    /// Fichier de la base SQLite
    #[arg(long, env = "PG_DB", value_name = "FICHIER")]
    db: Option<PathBuf>,
}

fn default_db_path() -> Result<PathBuf, String> {
    directories::ProjectDirs::from("", "", "PG")
        .map(|dirs| dirs.data_dir().join("pg.db"))
        .ok_or_else(|| "Dossier utilisateur introuvable : indiquez la base avec --db".to_owned())
}

fn run(cli: Cli) -> Result<(), String> {
    let path = cli.db.map_or_else(default_db_path, Ok)?;
    let store = Store::open(&path).map_err(|error| format!("{}: {error}", path.display()))?;
    match cli.interface.unwrap_or_default() {
        #[cfg(feature = "tui")]
        Interface::Tui => pg::tui::run(store).map_err(|error| error.to_string()),
        #[cfg(feature = "gui")]
        Interface::Gui => pg::gui::run(store).map_err(|error| error.to_string()),
    }
}

fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("pg : {message}");
            ExitCode::FAILURE
        }
    }
}
