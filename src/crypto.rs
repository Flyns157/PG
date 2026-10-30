//! Dérivation de clé (Argon2id) et chiffrement authentifié (XChaCha20-Poly1305).

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::aead::{Aead, KeyInit, Payload};
use chacha20poly1305::{XChaCha20Poly1305, XNonce};
use rand::Rng;
use zeroize::Zeroizing;

use crate::error::{Error, Result};

pub const KEY_LEN: usize = 32;
pub const SALT_LEN: usize = 16;
const NONCE_LEN: usize = 24;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct KdfParams {
    pub memory_kib: u32,
    pub iterations: u32,
    pub parallelism: u32,
}

impl Default for KdfParams {
    fn default() -> Self {
        Self {
            memory_kib: 64 * 1024,
            iterations: 3,
            parallelism: 1,
        }
    }
}

/// Clé symétrique, effacée de la mémoire à sa libération.
#[derive(Clone)]
pub struct Key(Zeroizing<[u8; KEY_LEN]>);

impl Key {
    pub fn generate() -> Self {
        let mut key = Zeroizing::new([0u8; KEY_LEN]);
        rand::rng().fill_bytes(key.as_mut());
        Self(key)
    }

    pub fn derive(password: &str, salt: &[u8], params: KdfParams) -> Result<Self> {
        let params = Params::new(
            params.memory_kib,
            params.iterations,
            params.parallelism,
            Some(KEY_LEN),
        )
        .map_err(|_| Error::Kdf)?;
        let mut key = Zeroizing::new([0u8; KEY_LEN]);
        Argon2::new(Algorithm::Argon2id, Version::V0x13, params)
            .hash_password_into(password.as_bytes(), salt, key.as_mut())
            .map_err(|_| Error::Kdf)?;
        Ok(Self(key))
    }

    fn from_bytes(bytes: &[u8]) -> Result<Self> {
        let array: [u8; KEY_LEN] = bytes.try_into().map_err(|_| Error::Corrupted)?;
        Ok(Self(Zeroizing::new(array)))
    }

    fn cipher(&self) -> XChaCha20Poly1305 {
        XChaCha20Poly1305::new_from_slice(self.0.as_ref()).expect("la clé fait 32 octets")
    }

    /// Chiffre `plaintext` ; le résultat est `nonce || chiffré`. `aad` lie le chiffré à son contexte.
    pub fn seal(&self, aad: &[u8], plaintext: &[u8]) -> Vec<u8> {
        let mut nonce = [0u8; NONCE_LEN];
        rand::rng().fill_bytes(&mut nonce);
        let nonce = XNonce::from(nonce);
        let ciphertext = self
            .cipher()
            .encrypt(
                &nonce,
                Payload {
                    msg: plaintext,
                    aad,
                },
            )
            .expect("le chiffrement en mémoire ne peut échouer que sur une taille excessive");
        let mut sealed = Vec::with_capacity(NONCE_LEN + ciphertext.len());
        sealed.extend_from_slice(nonce.as_slice());
        sealed.extend_from_slice(&ciphertext);
        sealed
    }

    pub fn open(&self, aad: &[u8], sealed: &[u8]) -> Result<Zeroizing<Vec<u8>>> {
        if sealed.len() < NONCE_LEN {
            return Err(Error::Corrupted);
        }
        let (nonce, ciphertext) = sealed.split_at(NONCE_LEN);
        let nonce: [u8; NONCE_LEN] = nonce.try_into().map_err(|_| Error::Corrupted)?;
        self.cipher()
            .decrypt(
                &XNonce::from(nonce),
                Payload {
                    msg: ciphertext,
                    aad,
                },
            )
            .map(Zeroizing::new)
            .map_err(|_| Error::Corrupted)
    }

    /// Protège cette clé par une autre.
    pub fn wrap(&self, wrapping_key: &Key, aad: &[u8]) -> Vec<u8> {
        wrapping_key.seal(aad, self.0.as_ref())
    }

    pub fn unwrap(wrapping_key: &Key, aad: &[u8], wrapped: &[u8]) -> Result<Self> {
        Self::from_bytes(&wrapping_key.open(aad, wrapped)?)
    }
}

impl std::fmt::Debug for Key {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Key(<masquée>)")
    }
}

pub fn random_salt() -> [u8; SALT_LEN] {
    let mut salt = [0u8; SALT_LEN];
    rand::rng().fill_bytes(&mut salt);
    salt
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seal_roundtrip_and_rejects_tampering_and_wrong_context() {
        let key = Key::generate();
        let mut sealed = key.seal(b"ctx", b"secret");
        assert_eq!(key.open(b"ctx", &sealed).unwrap().as_slice(), b"secret");
        assert!(matches!(key.open(b"autre", &sealed), Err(Error::Corrupted)));
        assert!(matches!(
            Key::generate().open(b"ctx", &sealed),
            Err(Error::Corrupted)
        ));
        *sealed.last_mut().unwrap() ^= 1;
        assert!(matches!(key.open(b"ctx", &sealed), Err(Error::Corrupted)));
        assert!(matches!(key.open(b"ctx", b"court"), Err(Error::Corrupted)));
    }

    #[test]
    fn same_plaintext_gives_different_ciphertexts() {
        let key = Key::generate();
        assert_ne!(key.seal(b"", b"x"), key.seal(b"", b"x"));
    }

    #[test]
    fn derivation_depends_on_password_and_salt() {
        let fast = KdfParams {
            memory_kib: 8,
            iterations: 1,
            parallelism: 1,
        };
        let reference = Key::derive("a", b"0123456789abcdef", fast).unwrap();
        let sealed = reference.seal(b"", b"x");
        assert!(
            Key::derive("a", b"0123456789abcdef", fast)
                .unwrap()
                .open(b"", &sealed)
                .is_ok()
        );
        assert!(
            Key::derive("b", b"0123456789abcdef", fast)
                .unwrap()
                .open(b"", &sealed)
                .is_err()
        );
        assert!(
            Key::derive("a", b"fedcba9876543210", fast)
                .unwrap()
                .open(b"", &sealed)
                .is_err()
        );
    }
}
