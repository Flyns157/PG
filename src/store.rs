//! Coffre SQLite. Tout le contenu d'une entrée est chiffré : la base ne révèle que les noms
//! d'utilisateur et le nombre d'entrées de chacun.

use std::path::Path;

use chrono::{DateTime, Utc};
use rand::Rng;
use rusqlite::{Connection, OptionalExtension, params};
use zeroize::Zeroizing;

use crate::crypto::{KdfParams, Key, random_salt};
use crate::entry::{Entry, EntryFields};
use crate::error::{Error, Result};

const SCHEMA_VERSION: i64 = 1;
const MIN_MASTER_PASSWORD_CHARS: usize = 12;

/// Utilisateur déverrouillé. Sa clé n'existe qu'en mémoire et disparaît avec cette valeur.
#[derive(Debug)]
pub struct Session {
    user_id: i64,
    username: String,
    key: Key,
}

impl Session {
    pub fn username(&self) -> &str {
        &self.username
    }
}

/// Entrée à importer, avec ses dates d'origine.
pub struct ImportedEntry {
    pub fields: EntryFields,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ImportReport {
    pub imported: usize,
    pub duplicates: usize,
}

pub struct Store {
    conn: Connection,
    kdf: KdfParams,
}

impl Store {
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(parent) = path
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
        {
            std::fs::create_dir_all(parent)?;
        }
        let store = Self::init(Connection::open(path)?)?;
        restrict_to_owner(path)?;
        Ok(store)
    }

    pub fn open_in_memory() -> Result<Self> {
        Self::init(Connection::open_in_memory()?)
    }

    /// Remplace les paramètres de dérivation appliqués aux futurs comptes et mots de passe.
    pub fn with_kdf(mut self, kdf: KdfParams) -> Self {
        self.kdf = kdf;
        self
    }

    fn init(conn: Connection) -> Result<Self> {
        conn.execute_batch("PRAGMA foreign_keys = ON; PRAGMA secure_delete = ON;")?;
        let version: i64 = conn.query_row("PRAGMA user_version", [], |row| row.get(0))?;
        match version {
            0 => conn.execute_batch(
                "BEGIN;
                 CREATE TABLE users (
                     id INTEGER PRIMARY KEY,
                     username TEXT NOT NULL UNIQUE,
                     salt BLOB NOT NULL,
                     kdf_memory_kib INTEGER NOT NULL,
                     kdf_iterations INTEGER NOT NULL,
                     kdf_parallelism INTEGER NOT NULL,
                     wrapped_key BLOB NOT NULL
                 );
                 CREATE TABLE entries (
                     id TEXT PRIMARY KEY,
                     user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                     sealed BLOB NOT NULL
                 );
                 CREATE INDEX entries_user ON entries(user_id);
                 PRAGMA user_version = 1;
                 COMMIT;",
            )?,
            SCHEMA_VERSION => {}
            newer => return Err(Error::UnsupportedSchema(newer)),
        }
        Ok(Self {
            conn,
            kdf: KdfParams::default(),
        })
    }

    pub fn has_accounts(&self) -> Result<bool> {
        Ok(self
            .conn
            .query_row("SELECT EXISTS(SELECT 1 FROM users)", [], |row| row.get(0))?)
    }

    pub fn register(&self, username: &str, password: &str) -> Result<Session> {
        let username = username.trim();
        validate_username(username)?;
        validate_master_password(password)?;
        let taken: bool = self.conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM users WHERE username = ?1)",
            [username],
            |row| row.get(0),
        )?;
        if taken {
            return Err(Error::UsernameTaken);
        }

        let salt = random_salt();
        let vault_key = Key::generate();
        let wrapped = vault_key.wrap(
            &Key::derive(password, &salt, self.kdf)?,
            &vault_key_aad(username),
        );
        self.conn.execute(
            "INSERT INTO users (username, salt, kdf_memory_kib, kdf_iterations, kdf_parallelism, wrapped_key)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![username, salt, self.kdf.memory_kib, self.kdf.iterations, self.kdf.parallelism, wrapped],
        )?;
        Ok(Session {
            user_id: self.conn.last_insert_rowid(),
            username: username.to_owned(),
            key: vault_key,
        })
    }

    pub fn login(&self, username: &str, password: &str) -> Result<Session> {
        let username = username.trim();
        let row = self
            .conn
            .query_row(
                "SELECT id, salt, kdf_memory_kib, kdf_iterations, kdf_parallelism, wrapped_key FROM users WHERE username = ?1",
                [username],
                |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, Vec<u8>>(1)?,
                        KdfParams { memory_kib: row.get(2)?, iterations: row.get(3)?, parallelism: row.get(4)? },
                        row.get::<_, Vec<u8>>(5)?,
                    ))
                },
            )
            .optional()?;
        let Some((user_id, salt, kdf, wrapped)) = row else {
            return Err(Error::InvalidCredentials);
        };
        let key = Key::unwrap(
            &Key::derive(password, &salt, kdf)?,
            &vault_key_aad(username),
            &wrapped,
        )
        .map_err(|_| Error::InvalidCredentials)?;
        Ok(Session {
            user_id,
            username: username.to_owned(),
            key,
        })
    }

    /// Protège la clé du coffre par un nouveau mot de passe, sans rechiffrer les entrées.
    pub fn change_master_password(
        &self,
        session: &Session,
        current: &str,
        new: &str,
    ) -> Result<()> {
        self.login(&session.username, current)?;
        validate_master_password(new)?;
        let salt = random_salt();
        let wrapped = session.key.wrap(
            &Key::derive(new, &salt, self.kdf)?,
            &vault_key_aad(&session.username),
        );
        self.conn.execute(
            "UPDATE users SET salt = ?1, kdf_memory_kib = ?2, kdf_iterations = ?3, kdf_parallelism = ?4, wrapped_key = ?5
             WHERE id = ?6",
            params![salt, self.kdf.memory_kib, self.kdf.iterations, self.kdf.parallelism, wrapped, session.user_id],
        )?;
        Ok(())
    }

    pub fn list(&self, session: &Session) -> Result<Vec<Entry>> {
        let mut statement = self
            .conn
            .prepare("SELECT id, sealed FROM entries WHERE user_id = ?1")?;
        let rows = statement.query_map([session.user_id], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, Vec<u8>>(1)?))
        })?;
        rows.map(|row| {
            let (id, sealed) = row?;
            open_entry(session, id, &sealed)
        })
        .collect()
    }

    pub fn add(&self, session: &Session, fields: EntryFields) -> Result<Entry> {
        fields.validate()?;
        let now = Utc::now();
        let entry = Entry {
            id: new_entry_id(),
            fields,
            created_at: now,
            updated_at: now,
        };
        self.conn.execute(
            "INSERT INTO entries (id, user_id, sealed) VALUES (?1, ?2, ?3)",
            params![entry.id, session.user_id, seal_entry(session, &entry)?],
        )?;
        Ok(entry)
    }

    pub fn update(&self, session: &Session, id: &str, fields: EntryFields) -> Result<Entry> {
        fields.validate()?;
        let sealed: Option<Vec<u8>> = self
            .conn
            .query_row(
                "SELECT sealed FROM entries WHERE id = ?1 AND user_id = ?2",
                params![id, session.user_id],
                |row| row.get(0),
            )
            .optional()?;
        let sealed = sealed.ok_or(Error::EntryNotFound)?;
        let mut entry = open_entry(session, id.to_owned(), &sealed)?;
        entry.fields = fields;
        entry.updated_at = Utc::now();
        self.conn.execute(
            "UPDATE entries SET sealed = ?1 WHERE id = ?2 AND user_id = ?3",
            params![seal_entry(session, &entry)?, id, session.user_id],
        )?;
        Ok(entry)
    }

    pub fn delete(&self, session: &Session, id: &str) -> Result<()> {
        let deleted = self.conn.execute(
            "DELETE FROM entries WHERE id = ?1 AND user_id = ?2",
            params![id, session.user_id],
        )?;
        if deleted == 0 {
            return Err(Error::EntryNotFound);
        }
        Ok(())
    }

    /// Importe tout ou rien, en ignorant ce qui existe déjà à l'identique.
    pub fn import(
        &mut self,
        session: &Session,
        records: Vec<ImportedEntry>,
    ) -> Result<ImportReport> {
        for record in &records {
            record.fields.validate()?;
        }
        let mut existing = self.list(session)?;
        let transaction = self.conn.transaction()?;
        let mut report = ImportReport {
            imported: 0,
            duplicates: 0,
        };
        for record in records {
            if existing
                .iter()
                .any(|entry| entry.is_same_credential(&record.fields))
            {
                report.duplicates += 1;
                continue;
            }
            let entry = Entry {
                id: new_entry_id(),
                fields: record.fields,
                created_at: record.created_at,
                updated_at: record.updated_at,
            };
            transaction.execute(
                "INSERT INTO entries (id, user_id, sealed) VALUES (?1, ?2, ?3)",
                params![entry.id, session.user_id, seal_entry(session, &entry)?],
            )?;
            existing.push(entry);
            report.imported += 1;
        }
        transaction.commit()?;
        Ok(report)
    }
}

pub fn validate_username(username: &str) -> Result<()> {
    if !(3..=50).contains(&username.trim().chars().count()) {
        return Err(Error::Validation(
            "Le nom du compte doit faire de 3 à 50 caractères".into(),
        ));
    }
    Ok(())
}

pub fn validate_master_password(password: &str) -> Result<()> {
    if password.chars().count() < MIN_MASTER_PASSWORD_CHARS {
        return Err(Error::Validation(format!(
            "Le mot de passe maître doit faire au moins {MIN_MASTER_PASSWORD_CHARS} caractères"
        )));
    }
    Ok(())
}

fn vault_key_aad(username: &str) -> Vec<u8> {
    format!("pg:vault-key:v1:{username}").into_bytes()
}

// Lie le chiffré à son propriétaire et à son identifiant : déplacer une ligne en base la rend illisible.
fn entry_aad(session: &Session, id: &str) -> Vec<u8> {
    format!("pg:entry:v1:{}:{id}", session.user_id).into_bytes()
}

fn seal_entry(session: &Session, entry: &Entry) -> Result<Vec<u8>> {
    let plaintext = Zeroizing::new(serde_json::to_vec(entry)?);
    Ok(session.key.seal(&entry_aad(session, &entry.id), &plaintext))
}

fn open_entry(session: &Session, id: String, sealed: &[u8]) -> Result<Entry> {
    let plaintext = session.key.open(&entry_aad(session, &id), sealed)?;
    let mut entry: Entry = serde_json::from_slice(&plaintext)?;
    entry.id = id;
    Ok(entry)
}

fn new_entry_id() -> String {
    let mut bytes = [0u8; 16];
    rand::rng().fill_bytes(&mut bytes);
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(unix)]
fn restrict_to_owner(path: &Path) -> Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o600))?;
    Ok(())
}

#[cfg(not(unix))]
fn restrict_to_owner(_path: &Path) -> Result<()> {
    Ok(())
}

#[cfg(test)]
pub(crate) const FAST_KDF: KdfParams = KdfParams {
    memory_kib: 8,
    iterations: 1,
    parallelism: 1,
};

#[cfg(test)]
mod tests {
    use super::*;

    const MASTER: &str = "correct horse battery";

    fn store() -> Store {
        Store::open_in_memory().unwrap().with_kdf(FAST_KDF)
    }

    fn fields(url: &str, password: &str) -> EntryFields {
        EntryFields::new(url, "moi", password)
    }

    #[test]
    fn login_requires_the_right_password() {
        let store = store();
        store.register("alice", MASTER).unwrap();
        assert!(store.login("alice", MASTER).is_ok());
        assert!(matches!(
            store.login("alice", "mauvais mot de passe"),
            Err(Error::InvalidCredentials)
        ));
        assert!(matches!(
            store.login("inconnu", MASTER),
            Err(Error::InvalidCredentials)
        ));
    }

    #[test]
    fn register_rejects_weak_password_duplicate_and_bad_username() {
        let store = store();
        assert!(matches!(
            store.register("alice", "court"),
            Err(Error::Validation(_))
        ));
        assert!(matches!(
            store.register("al", MASTER),
            Err(Error::Validation(_))
        ));
        store.register("alice", MASTER).unwrap();
        assert!(matches!(
            store.register("alice", MASTER),
            Err(Error::UsernameTaken)
        ));
    }

    #[test]
    fn entries_are_isolated_between_users() {
        let store = store();
        let alice = store.register("alice", MASTER).unwrap();
        let bob = store.register("bobby", MASTER).unwrap();
        let entry = store
            .add(&alice, fields("https://a.example", "s3cret"))
            .unwrap();

        assert_eq!(store.list(&alice).unwrap().len(), 1);
        assert!(store.list(&bob).unwrap().is_empty());
        assert!(matches!(
            store.update(&bob, &entry.id, fields("x", "y")),
            Err(Error::EntryNotFound)
        ));
        assert!(matches!(
            store.delete(&bob, &entry.id),
            Err(Error::EntryNotFound)
        ));
        assert_eq!(store.list(&alice).unwrap()[0].fields.password, "s3cret");
    }

    #[test]
    fn moving_a_sealed_row_to_another_user_makes_it_unreadable() {
        let store = store();
        let alice = store.register("alice", MASTER).unwrap();
        let bob = store.register("bobby", MASTER).unwrap();
        store
            .add(&alice, fields("https://a.example", "s3cret"))
            .unwrap();
        store
            .conn
            .execute("UPDATE entries SET user_id = ?1", [bob.user_id])
            .unwrap();
        assert!(matches!(store.list(&bob), Err(Error::Corrupted)));
    }

    #[test]
    fn update_keeps_creation_date_and_changes_update_date() {
        let store = store();
        let alice = store.register("alice", MASTER).unwrap();
        let entry = store
            .add(&alice, fields("https://a.example", "un"))
            .unwrap();
        std::thread::sleep(std::time::Duration::from_millis(5));
        let updated = store
            .update(&alice, &entry.id, fields("https://a.example", "deux"))
            .unwrap();
        assert_eq!(updated.created_at, entry.created_at);
        assert!(updated.updated_at > entry.updated_at);
        assert_eq!(store.list(&alice).unwrap()[0].fields.password, "deux");
    }

    #[test]
    fn changing_master_password_keeps_entries_readable() {
        let store = store();
        let alice = store.register("alice", MASTER).unwrap();
        store
            .add(&alice, fields("https://a.example", "s3cret"))
            .unwrap();
        let new = "un tout nouveau secret";
        assert!(matches!(
            store.change_master_password(&alice, "faux", new),
            Err(Error::InvalidCredentials)
        ));
        store.change_master_password(&alice, MASTER, new).unwrap();
        assert!(store.login("alice", MASTER).is_err());
        let session = store.login("alice", new).unwrap();
        assert_eq!(store.list(&session).unwrap()[0].fields.password, "s3cret");
    }

    #[test]
    fn import_skips_duplicates() {
        let mut store = store();
        let alice = store.register("alice", MASTER).unwrap();
        let record = |url: &str| ImportedEntry {
            fields: fields(url, "p"),
            created_at: Utc::now(),
            updated_at: Utc::now(),
        };
        let first = store
            .import(&alice, vec![record("a"), record("b"), record("a")])
            .unwrap();
        assert_eq!(
            first,
            ImportReport {
                imported: 2,
                duplicates: 1
            }
        );
        let second = store.import(&alice, vec![record("a")]).unwrap();
        assert_eq!(
            second,
            ImportReport {
                imported: 0,
                duplicates: 1
            }
        );
    }

    #[test]
    fn database_file_contains_no_secret_and_survives_reopening() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("sous-dossier").join("pg.db");
        {
            let store = Store::open(&path).unwrap().with_kdf(FAST_KDF);
            let alice = store.register("alice", MASTER).unwrap();
            store
                .add(
                    &alice,
                    fields("https://secret-site.example", "mot-de-passe-unique"),
                )
                .unwrap();
        }
        let raw = std::fs::read(&path).unwrap();
        for needle in ["secret-site", "mot-de-passe-unique", MASTER] {
            assert!(
                !raw.windows(needle.len())
                    .any(|window| window == needle.as_bytes()),
                "{needle} en clair"
            );
        }
        let store = Store::open(&path).unwrap();
        let session = store.login("alice", MASTER).unwrap();
        assert_eq!(store.list(&session).unwrap().len(), 1);
    }

    #[test]
    fn newer_schema_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("pg.db");
        Connection::open(&path)
            .unwrap()
            .execute_batch("PRAGMA user_version = 99")
            .unwrap();
        assert!(matches!(
            Store::open(&path),
            Err(Error::UnsupportedSchema(99))
        ));
    }
}
