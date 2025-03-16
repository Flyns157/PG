import hashlib
import base64
import os
from cryptography.fernet import Fernet

def hash_password(password, algorithm="sha256"):
    if algorithm not in hashlib.algorithms_available:
        raise ValueError("Algorithme non supporté")
    hasher = hashlib.new(algorithm)
    hasher.update(password.encode('utf-8'))
    return hasher.hexdigest()

def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32)).decode()

def get_cipher(key):
    return Fernet(key.encode())

def encrypt_password(password, key):
    cipher = get_cipher(key)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    cipher = get_cipher(key)
    return cipher.decrypt(encrypted_password.encode()).decode()

def supported_algorithms():
    return sorted(hashlib.algorithms_available)