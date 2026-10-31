//! Presse-papiers effacé automatiquement.

use std::time::{Duration, Instant};

use zeroize::Zeroizing;

const CLEAR_AFTER: Duration = Duration::from_secs(30);

/// Copie un secret et l'efface après 30 secondes, ou à la fermeture, s'il n'a pas été remplacé.
#[derive(Default)]
pub struct SecretClipboard {
    copied: Option<(Zeroizing<String>, Instant)>,
}

impl SecretClipboard {
    pub fn copy(&mut self, text: &str) -> Result<(), String> {
        write_secret(text)?;
        self.copied = Some((Zeroizing::new(text.to_owned()), Instant::now()));
        Ok(())
    }

    #[cfg(all(test, feature = "gui"))]
    pub(crate) fn copied_text(&self) -> Option<&str> {
        self.copied.as_ref().map(|(text, _)| text.as_str())
    }

    /// Renvoie vrai si le délai vient d'effacer le secret du presse-papiers.
    pub fn tick(&mut self) -> bool {
        self.copied
            .as_ref()
            .is_some_and(|(_, at)| at.elapsed() >= CLEAR_AFTER)
            && self.clear()
    }

    /// Renvoie vrai si le secret était encore dans le presse-papiers et qu'il a été effacé.
    pub fn clear(&mut self) -> bool {
        let Some((text, _)) = self.copied.take() else {
            return false;
        };
        if let Ok(mut clipboard) = arboard::Clipboard::new()
            && clipboard.get_text().is_ok_and(|current| current == *text)
        {
            return clipboard.clear().is_ok();
        }
        false
    }
}

#[cfg(not(test))]
fn write_secret(text: &str) -> Result<(), String> {
    let mut clipboard = arboard::Clipboard::new().map_err(|error| error.to_string())?;
    secret_setter(&mut clipboard)
        .text(text)
        .map_err(|error| error.to_string())
}

// Les tests ne doivent pas écraser le presse-papiers de la personne qui les lance.
#[cfg(test)]
fn write_secret(_text: &str) -> Result<(), String> {
    Ok(())
}

/// Demande à Windows de garder le secret hors de son historique et de sa synchronisation.
#[cfg(all(windows, not(test)))]
fn secret_setter(clipboard: &mut arboard::Clipboard) -> arboard::Set<'_> {
    use arboard::SetExtWindows;
    clipboard
        .set()
        .exclude_from_monitoring()
        .exclude_from_cloud()
        .exclude_from_history()
}

#[cfg(all(not(windows), not(test)))]
fn secret_setter(clipboard: &mut arboard::Clipboard) -> arboard::Set<'_> {
    clipboard.set()
}

impl Drop for SecretClipboard {
    fn drop(&mut self) {
        self.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn expiry_does_not_report_a_clipboard_it_did_not_clear() {
        // Ce texte n'est pas dans le presse-papiers : le contenu de l'utilisateur reste intact.
        let copied = (
            Zeroizing::new("pg-test-secret-jamais-copie-7f3a".to_owned()),
            Instant::now() - CLEAR_AFTER,
        );
        let mut clipboard = SecretClipboard {
            copied: Some(copied),
        };
        assert!(!clipboard.tick());
        assert!(clipboard.copied.is_none());
    }
}
