import os
import json
from core.crypto import encrypt_data, decrypt_data

VAULT_PATH = "vaults/user_vault.dat"
LABEL_FILE = "vaults/labels.dat"  # todo encrypted
LABEL_KEY = "__passguard__labels__v1__"  # constant key for now


def create_vault(password: str, path: str = VAULT_PATH):
    data = {"credentials": []}
    encrypted = encrypt_data(password, data)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(encrypted)


def unlock_vault(password: str, path: str = VAULT_PATH) -> dict:
    with open(path, "rb") as f:
        blob = f.read()
    return decrypt_data(password, blob)


def save_vault(password: str, data: dict, path: str = VAULT_PATH):
    encrypted = encrypt_data(password, data)
    with open(path, "wb") as f:
        f.write(encrypted)


def save_vault_label(filename: str, label: str):
    os.makedirs(os.path.dirname(LABEL_FILE), exist_ok=True)
    try:
        with open(LABEL_FILE, "rb") as f:
            data = decrypt_data(LABEL_KEY, f.read())
    except FileNotFoundError:
        data = {}
    except Exception:
        print("[WARN] Could not read labels. Creating new.")
        data = {}

    data[filename] = label
    encrypted = encrypt_data(LABEL_KEY, data)
    with open(LABEL_FILE, "wb") as f:
        f.write(encrypted)


def load_vault_labels() -> dict:
    try:
        with open(LABEL_FILE, "rb") as f:
            return decrypt_data(LABEL_KEY, f.read())
    except FileNotFoundError:
        return {}
    except Exception:
        print("[WARN] Failed to load encrypted labels. Returning empty.")
        return {}