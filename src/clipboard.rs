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
        let mut clipboard = arboard::Clipboard::new().map_err(|error| error.to_string())?;
        clipboard
            .set_text(text)
            .map_err(|error| error.to_string())?;
        self.copied = Some((Zeroizing::new(text.to_owned()), Instant::now()));
        Ok(())
    }

    pub fn tick(&mut self) {
        if self
            .copied
            .as_ref()
            .is_some_and(|(_, at)| at.elapsed() >= CLEAR_AFTER)
        {
            self.clear();
        }
    }

    pub fn clear(&mut self) {
        let Some((text, _)) = self.copied.take() else {
            return;
        };
        if let Ok(mut clipboard) = arboard::Clipboard::new()
            && clipboard.get_text().is_ok_and(|current| current == *text)
        {
            let _ = clipboard.clear();
        }
    }
}

impl Drop for SecretClipboard {
    fn drop(&mut self) {
        self.clear();
    }
}
