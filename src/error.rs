use thiserror::Error;

pub type Result<T> = std::result::Result<T, Error>;

#[derive(Debug, Error)]
pub enum Error {
    #[error("Compte ou mot de passe incorrect")]
    InvalidCredentials,
    #[error("Ce compte existe déjà")]
    UsernameTaken,
    #[error("{0}")]
    Validation(String),
    #[error("Entrée introuvable")]
    EntryNotFound,
    #[error("Donnée chiffrée invalide ou altérée")]
    Corrupted,
    #[error("Cette base utilise le schéma {0}, plus récent que cette version de PG")]
    UnsupportedSchema(i64),
    #[error("Paramètres de dérivation invalides")]
    Kdf,
    #[error("Base de données : {0}")]
    Database(#[from] rusqlite::Error),
    #[error("Fichier : {0}")]
    Io(#[from] std::io::Error),
    #[error("CSV : {0}")]
    Csv(#[from] csv::Error),
    #[error("CSV, ligne {line} : {message}")]
    CsvRow { line: u64, message: String },
    #[error("Sérialisation : {0}")]
    Serialization(#[from] serde_json::Error),
}
