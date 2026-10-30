//! Génération de mots de passe.

use rand::RngExt;

const LOWER: &str = "abcdefghijkmnopqrstuvwxyz";
const UPPER: &str = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const DIGITS: &str = "23456789";
const SYMBOLS: &str = "!@#$%^&*-_=+?";
pub const DEFAULT_LENGTH: usize = 20;

/// Génère un mot de passe contenant au moins une minuscule, une majuscule, un chiffre et un symbole.
pub fn generate_password(length: usize) -> String {
    let length = length.max(4);
    let alphabet: Vec<char> = [LOWER, UPPER, DIGITS, SYMBOLS].concat().chars().collect();
    let mut rng = rand::rng();
    loop {
        let password: String = (0..length)
            .map(|_| alphabet[rng.random_range(0..alphabet.len())])
            .collect();
        if [LOWER, UPPER, DIGITS, SYMBOLS]
            .iter()
            .all(|set| password.chars().any(|c| set.contains(c)))
        {
            return password;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_password_has_requested_length_and_all_classes() {
        for _ in 0..100 {
            let password = generate_password(DEFAULT_LENGTH);
            assert_eq!(password.chars().count(), DEFAULT_LENGTH);
            for set in [LOWER, UPPER, DIGITS, SYMBOLS] {
                assert!(password.chars().any(|c| set.contains(c)));
            }
        }
        assert_ne!(
            generate_password(DEFAULT_LENGTH),
            generate_password(DEFAULT_LENGTH)
        );
    }
}
