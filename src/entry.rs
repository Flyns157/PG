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

    pub fn url_error(&self) -> Option<&'static str> {
        self.url
            .trim()
            .is_empty()
            .then_some("Le site est obligatoire")
    }

    pub fn username_error(&self) -> Option<&'static str> {
        self.username
            .trim()
            .is_empty()
            .then_some("L'identifiant est obligatoire")
    }

    pub fn password_error(&self) -> Option<&'static str> {
        self.password
            .is_empty()
            .then_some("Le mot de passe est obligatoire")
    }

    pub fn email_error(&self) -> Option<&'static str> {
        (!self.email.is_empty() && !self.email.contains('@'))
            .then_some("L'adresse e-mail est invalide")
    }

    pub fn validate(&self) -> Result<()> {
        let error = self
            .url_error()
            .or_else(|| self.username_error())
            .or_else(|| self.password_error())
            .or_else(|| self.email_error());
        match error {
            Some(message) => Err(Error::Validation(message.to_owned())),
            None => Ok(()),
        }
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
