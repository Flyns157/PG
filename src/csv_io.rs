//! Import et export CSV, compatibles avec les exports de la version Python de PG.
//! L'import accepte aussi les exports de mots de passe de Chromium.

use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::path::Path;

use chrono::{DateTime, Local, NaiveDateTime, TimeZone, Utc};
use serde::{Deserialize, Serialize};

use crate::entry::{Entry, EntryFields};
use crate::error::{Error, Result};
use crate::store::ImportedEntry;

#[derive(Serialize, Deserialize)]
struct CsvRow {
    url: String,
    #[serde(default, alias = "note")]
    description: String,
    #[serde(alias = "username")]
    key: String,
    password: String,
    #[serde(default)]
    email: String,
    #[serde(default)]
    phone: String,
    #[serde(default)]
    date_added: String,
    #[serde(default)]
    date_updated: String,
}

pub fn write_entries(entries: &[Entry], writer: impl Write) -> Result<()> {
    let mut writer = csv::Writer::from_writer(writer);
    for entry in entries {
        writer.serialize(CsvRow {
            url: entry.fields.url.clone(),
            description: entry.fields.notes.clone(),
            key: entry.fields.username.clone(),
            password: entry.fields.password.clone(),
            email: entry.fields.email.clone(),
            phone: entry.fields.phone.clone(),
            date_added: entry.created_at.to_rfc3339(),
            date_updated: entry.updated_at.to_rfc3339(),
        })?;
    }
    writer.flush()?;
    Ok(())
}

/// Écrit un export en clair. Un fichier existant n'est jamais écrasé.
pub fn export_to_file(entries: &[Entry], path: &Path) -> Result<()> {
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    std::os::unix::fs::OpenOptionsExt::mode(&mut options, 0o600);
    write_entries(entries, options.open(path)?)
}

pub fn read_entries(reader: impl Read) -> Result<Vec<ImportedEntry>> {
    let mut reader = csv::Reader::from_reader(reader);
    let headers = reader.headers()?.clone();
    let mut records = Vec::new();
    for record in reader.records() {
        let record = record?;
        let line = record.position().map_or(0, |position| position.line());
        let row: CsvRow = record.deserialize(Some(&headers))?;
        let invalid = |message: String| Error::CsvRow { line, message };
        let created_at = parse_date(&row.date_added).map_err(invalid)?;
        let updated_at = parse_date(&row.date_updated).map_err(invalid)?;
        let fields = EntryFields {
            url: row.url,
            username: row.key,
            password: row.password,
            notes: row.description,
            email: row.email,
            phone: row.phone,
        };
        fields
            .validate()
            .map_err(|error| invalid(error.to_string()))?;
        records.push(ImportedEntry {
            fields,
            created_at,
            updated_at,
        });
    }
    Ok(records)
}

pub fn import_from_file(path: &Path) -> Result<Vec<ImportedEntry>> {
    read_entries(std::fs::File::open(path)?)
}

fn parse_date(value: &str) -> std::result::Result<DateTime<Utc>, String> {
    let value = value.trim();
    if value.is_empty() {
        return Ok(Utc::now());
    }
    if let Ok(date) = DateTime::parse_from_rfc3339(value) {
        return Ok(date.with_timezone(&Utc));
    }
    if let Ok(date) = DateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S%.f%:z") {
        return Ok(date.with_timezone(&Utc));
    }
    // Sans fuseau, comme dans les exports Python : l'heure est considérée comme locale.
    NaiveDateTime::parse_from_str(value, "%Y-%m-%d %H:%M:%S%.f")
        .ok()
        .and_then(|date| Local.from_local_datetime(&date).earliest())
        .map(|date| date.with_timezone(&Utc))
        .ok_or_else(|| format!("date invalide : {value}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_python_export_whatever_the_column_order() {
        let csv = "password,date_updated,description,email,date_added,url,phone,key\n\
                   s3cret,2026-10-30 17:11:00.823838,d,a@example.com,2026-10-30 17:11:00+00:00,https://example.com/a,,alice\n";
        let records = read_entries(csv.as_bytes()).unwrap();
        assert_eq!(records.len(), 1);
        assert_eq!(records[0].fields.username, "alice");
        assert_eq!(records[0].fields.password, "s3cret");
        assert_eq!(records[0].fields.notes, "d");
        assert_eq!(
            records[0].created_at.to_rfc3339(),
            "2026-10-30T17:11:00+00:00"
        );
    }

    #[test]
    fn reads_chromium_export() {
        let csv = "name,url,username,password,note\n\
                   a.example,https://a.example/login,alice,Xy1]g:oz?{,\n\
                   b.example,https://b.example/,bob@b.example,s3cret,ma note\n";
        let records = read_entries(csv.as_bytes()).unwrap();
        assert_eq!(records.len(), 2);
        assert_eq!(records[0].fields.url, "https://a.example/login");
        assert_eq!(records[0].fields.username, "alice");
        assert_eq!(records[0].fields.password, "Xy1]g:oz?{");
        assert_eq!(records[0].fields.notes, "");
        assert_eq!(records[1].fields.username, "bob@b.example");
        assert_eq!(records[1].fields.notes, "ma note");
    }

    #[test]
    fn reads_chromium_export_without_note_column() {
        let csv = "name,url,username,password\na.example,https://a.example/,alice,s3cret\n";
        let records = read_entries(csv.as_bytes()).unwrap();
        assert_eq!(records[0].fields.username, "alice");
    }

    #[test]
    fn export_then_import_preserves_fields_including_special_characters() {
        let now = Utc::now();
        let mut fields = EntryFields::new("https://a.example/?a=1,2", "moi", "p\"a,s\ns");
        fields.notes = "é".into();
        let entry = Entry {
            id: "x".into(),
            fields,
            created_at: now,
            updated_at: now,
        };
        let mut buffer = Vec::new();
        write_entries(std::slice::from_ref(&entry), &mut buffer).unwrap();
        let records = read_entries(buffer.as_slice()).unwrap();
        assert!(records[0].fields == entry.fields);
        assert_eq!(records[0].created_at, now);
    }

    #[test]
    fn invalid_row_reports_its_line() {
        let csv = "url,key,password,date_added\nhttps://a,moi,p,\nhttps://b,moi,,\n";
        assert!(matches!(
            read_entries(csv.as_bytes()),
            Err(Error::CsvRow { line: 3, .. })
        ));
        let csv = "url,key,password,date_added\nhttps://a,moi,p,hier\n";
        assert!(matches!(
            read_entries(csv.as_bytes()),
            Err(Error::CsvRow { line: 2, .. })
        ));
    }

    #[test]
    fn export_never_overwrites_a_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("e.csv");
        export_to_file(&[], &path).unwrap();
        assert!(matches!(export_to_file(&[], &path), Err(Error::Io(_))));
    }
}
