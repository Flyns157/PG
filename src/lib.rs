//! PG : gestionnaire de mots de passe local, autonome, avec coffre SQLite chiffré.

pub mod clipboard;
pub mod crypto;
pub mod csv_io;
pub mod entry;
pub mod error;
pub mod generator;
pub mod search;
pub mod store;
pub mod workspace;

#[cfg(feature = "gui")]
pub mod gui;
#[cfg(feature = "tui")]
pub mod tui;

use std::time::Duration;

/// Durée d'inactivité au-delà de laquelle le coffre se verrouille.
pub const IDLE_LOCK: Duration = Duration::from_secs(5 * 60);
