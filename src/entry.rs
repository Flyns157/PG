//! Entrées du coffre.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use zeroize::{Zeroize, ZeroizeOnDrop};

use crate::error::{Error, Result};

/// Champs saisis par l'utilisateur, effacés de la mémoire à leur libération.
#[derive(Clone, Default, PartialEq, Eq, Serialize, Deserialize, Zeroize, ZeroizeOnDrop)]
pub struct EntryFields {
    pub url: String,
    pub username: String,
    pub password: String,
    pub notes: String,
    pub email: String,
    pub phone: String,
}

impl EntryFields {
    pub fn new(url: &str, username: &str, password: &str) -> Self {
        let mut fields = Self::default();
        fields.url = url.to_owned();
        fields.username = username.to_owned();
        fields.password = password.to_owned();
        fields
    }

    pub fn validate(&self) -> Result<()> {
        let invalid = |message: &str| Err(Error::Validation(message.to_owned()));
        if self.url.trim().is_empty() {
            return invalid("Le site est obligatoire");
        }
        if self.username.trim().is_empty() {
            return invalid("L'identifiant est obligatoire");
        }
        if self.password.is_empty() {
            return invalid("Le mot de passe est obligatoire");
        }
        if !self.email.is_empty() && !self.email.contains('@') {
            return invalid("L'adresse e-mail est invalide");
        }
        Ok(())
    }
}

impl std::fmt::Debug for EntryFields {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EntryFields")
            .field("url", &self.url)
            .field("username", &self.username)
            .finish_non_exhaustive()
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Entry {
    #[serde(skip)]
    pub id: String,
    pub fields: EntryFields,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

impl Entry {
    pub fn is_same_credential(&self, fields: &EntryFields) -> bool {
        self.fields.url == fields.url
            && self.fields.username == fields.username
            && self.fields.password == fields.password
    }
}
