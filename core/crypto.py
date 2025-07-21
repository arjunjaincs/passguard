import json
import os
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from argon2.low_level import hash_secret_raw, Type

SALT_LEN = 16
KEY_LEN = 32
NONCE_LEN = 12


def derive_key(password: str, salt: bytes) -> bytes:
    return hash_secret_raw(
        password.encode(),
        salt,
        time_cost=3,
        memory_cost=65536,
        parallelism=1,
        hash_len=KEY_LEN,
        type=Type.ID
    )


def encrypt_data(password: str, data: dict) -> bytes:
    salt = get_random_bytes(SALT_LEN)
    key = derive_key(password, salt)
    nonce = get_random_bytes(NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    plaintext = json.dumps(data).encode()
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)

    return b64encode(
        salt + nonce + tag + ciphertext
    )


def decrypt_data(password: str, blob: bytes) -> dict:
    decoded = b64decode(blob)
    salt = decoded[:SALT_LEN]
    nonce = decoded[SALT_LEN:SALT_LEN + NONCE_LEN]
    tag = decoded[SALT_LEN + NONCE_LEN:SALT_LEN + NONCE_LEN + 16]
    ciphertext = decoded[SALT_LEN + NONCE_LEN + 16:]

    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return json.loads(plaintext.decode())
    except Exception:
        raise ValueError("Invalid password or corrupted data")