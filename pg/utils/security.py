# pg.utils.security.py
"""
Module de gestion de la sécurité
"""

import hashlib
import base64
import string
import os
from cryptography.fernet import Fernet


def hash_password(password: str, algorithm: str = "sha256"):
    """
    Hache le mot de passe avec l'algorithme spécifié

    Args:
        password (str): Le mot de passe à hacher
        algorithm (str, optional): L'algorithme de hachage à utiliser. Defaults to "sha256".

    Raises:
        ValueError: L'algorithme spécifié n'est pas supporté

    Returns:
        str: Le mot de passe haché
    """
    if algorithm not in hashlib.algorithms_available:
        raise ValueError("Algorithme non supporté")
    hasher = hashlib.new(algorithm)
    hasher.update(password.encode('utf-8'))
    return hasher.hexdigest()

def generate_key() -> str:
    """
    Génère une clé de chiffrement aléatoire

    Returns:
        str: La clé de chiffrement
    """
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def get_cipher(key: bytes | str) -> Fernet:
    """
    Retourne un objet de chiffrement Fernet à partir de la clé de chiffrement
    
    Returns:
        Fernet: L'objet de chiffrement
    """
    return Fernet(key.encode())

def encrypt_password(password: str, key: bytes) -> str:
    """
    Chiffre le mot de passe avec la clé de chiffrement

    Args:
        password (str): Le mot de passe à chiffrer
        key (bytes): La clé de chiffrement

    Returns:
        str: Le mot de passe chiffré
    """
    cipher = get_cipher(key)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str, key: bytes) -> str:
    """
    Déchiffre le mot de passe avec la clé de chiffrement

    Args:
        encrypted_password (str): Le mot de passe chiffré
        key (bytes): La clé de chiffrement

    Returns:
        str: Le mot de passe déchiffré
    """
    cipher = get_cipher(key)
    return cipher.decrypt(encrypted_password.encode()).decode()

def supported_algorithms() -> list[str]:
    """
    Retourne la liste des algorithmes de hachage supportés

    Returns:
        list[str]: La liste des algorithmes de hachage supportés
    """
    return sorted(hashlib.algorithms_available)

def validate_password_strength(password: str) -> str:
    """
    Vérifie la force du mot de passe

    Args:
        password (str): Le mot de passe à vérifier

    Raises:
        ValueError: Le mot de passe est trop faible

    Returns:
        str: Le mot de passe
    """
    if len(password) < 8:
        raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
    if not any(c.isupper() for c in password):
        raise ValueError('Le mot de passe doit contenir au moins une majuscule')
    if not any(c.islower() for c in password):
        raise ValueError('Le mot de passe doit contenir au moins une minuscule')
    if not any(c.isdigit() for c in password):
        raise ValueError('Le mot de passe doit contenir au moins un chiffre')
    if not any(c in string.punctuation for c in password):
        raise ValueError('Le mot de passe doit contenir au moins un caractère spécial')
    return password
