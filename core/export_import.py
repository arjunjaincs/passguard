"""Secure vault export/import using RSA-4096 public/private key encryption.

This module enables secure vault sharing between devices or users without
exposing master passwords. Uses asymmetric encryption (RSA-4096) to protect
a symmetric key (AES-256-GCM) that encrypts the vault data.

Security Features:
- RSA-4096 keypair for asymmetric encryption
- Private key encrypted with master password (Argon2id + AES-GCM)
- RSA-OAEP with SHA-256 for key wrapping
- RSA-PSS signatures for authenticity verification
- AES-256-GCM for vault data encryption
- No plaintext keys or passwords stored on disk

File Format (.pvgx):
    JSON container with base64-encoded encrypted data
"""

import json
import os
import base64
import uuid
from datetime import datetime
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from core.crypto import derive_key, ARGON_TIME_COST, ARGON_MEMORY_COST, ARGON_PARALLELISM

# Paths
KEYS_DIR = "keys"
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, "public.pem")
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private.pem")
EXPORT_DIR = os.path.join("vaults", "exported")

# RSA parameters
RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537


def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(KEYS_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)


def generate_keypair(master_password: str) -> Tuple[bytes, bytes]:
    """
    Generate RSA-4096 keypair and encrypt private key with master password.
    
    Args:
        master_password: User's master password for encrypting private key
    
    Returns:
        Tuple of (public_key_pem, encrypted_private_key_pem)
    
    Raises:
        ValueError: If keypair generation fails
    """
    try:
        # Generate RSA-4096 keypair
        private_key = rsa.generate_private_key(
            public_exponent=RSA_PUBLIC_EXPONENT,
            key_size=RSA_KEY_SIZE,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Serialize public key (unencrypted)
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Serialize private key (unencrypted first)
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Encrypt private key with master password using AES-GCM
        salt = get_random_bytes(16)
        key = derive_key(master_password, salt, ARGON_TIME_COST, ARGON_MEMORY_COST, ARGON_PARALLELISM)
        nonce = get_random_bytes(12)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(private_pem)
        
        # Package encrypted private key
        encrypted_private = {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
        }
        encrypted_private_pem = json.dumps(encrypted_private).encode('utf-8')
        
        return public_pem, encrypted_private_pem
        
    except Exception as e:
        raise ValueError(f"Failed to generate keypair: {e}")


def save_keypair(master_password: str):
    """
    Generate and save keypair to disk.
    
    Args:
        master_password: User's master password
    
    Raises:
        ValueError: If keypair already exists or save fails
    """
    ensure_directories()
    
    if os.path.exists(PUBLIC_KEY_PATH) or os.path.exists(PRIVATE_KEY_PATH):
        raise ValueError("Keypair already exists. Delete existing keys first if you want to regenerate.")
    
    public_pem, encrypted_private_pem = generate_keypair(master_password)
    
    with open(PUBLIC_KEY_PATH, 'wb') as f:
        f.write(public_pem)
    
    with open(PRIVATE_KEY_PATH, 'wb') as f:
        f.write(encrypted_private_pem)


def load_public_key(path: str = PUBLIC_KEY_PATH):
    """
    Load public key from PEM file.
    
    Args:
        path: Path to public key PEM file
    
    Returns:
        RSA public key object
    
    Raises:
        ValueError: If key file doesn't exist or is invalid
    """
    try:
        if not os.path.exists(path):
            raise ValueError(f"Public key not found at {path}")
        
        with open(path, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        return public_key
    except Exception as e:
        raise ValueError(f"Failed to load public key: {e}")


def load_private_key(master_password: str, path: str = PRIVATE_KEY_PATH):
    """
    Load and decrypt private key using master password.
    
    Args:
        master_password: User's master password
        path: Path to encrypted private key file
    
    Returns:
        RSA private key object
    
    Raises:
        ValueError: If key file doesn't exist, password is wrong, or key is invalid
    """
    try:
        if not os.path.exists(path):
            raise ValueError(f"Private key not found at {path}")
        
        with open(path, 'rb') as f:
            encrypted_data = json.loads(f.read())
        
        # Decrypt private key
        salt = base64.b64decode(encrypted_data['salt'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        tag = base64.b64decode(encrypted_data['tag'])
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        
        key = derive_key(master_password, salt, ARGON_TIME_COST, ARGON_MEMORY_COST, ARGON_PARALLELISM)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        
        try:
            private_pem = cipher.decrypt_and_verify(ciphertext, tag)
        except Exception:
            raise ValueError("Invalid master password for private key decryption")
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_pem,
            password=None,
            backend=default_backend()
        )
        
        return private_key
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to load private key: {e}")


def export_vault(vault_data: dict, master_password: str, vault_label: str, 
                 recipient_pubkey_path: Optional[str] = None) -> str:
    """
    Export vault encrypted with public key.
    
    Args:
        vault_data: Vault credentials dictionary
        master_password: User's master password (for signing)
        vault_label: Label/name of the vault
        recipient_pubkey_path: Path to recipient's public key (None = self)
    
    Returns:
        Path to exported .pvgx file
    
    Raises:
        ValueError: If export fails
    """
    try:
        ensure_directories()
        
        # Ensure keypair exists
        if not os.path.exists(PUBLIC_KEY_PATH):
            save_keypair(master_password)
        
        # Load recipient's public key (or own if backing up)
        if recipient_pubkey_path:
            recipient_public_key = load_public_key(recipient_pubkey_path)
            recipient_name = os.path.basename(recipient_pubkey_path).replace('.pem', '')
        else:
            recipient_public_key = load_public_key(PUBLIC_KEY_PATH)
            recipient_name = "self"
        
        # Generate random AES key for vault encryption
        aes_key = get_random_bytes(32)  # 256-bit key
        nonce = get_random_bytes(12)
        
        # Encrypt vault data with AES-GCM
        plaintext = json.dumps(vault_data, separators=(',', ':')).encode('utf-8')
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        
        # Encrypt AES key with recipient's public key (RSA-OAEP)
        encrypted_key = recipient_public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Sign the export with sender's private key (RSA-PSS)
        private_key = load_private_key(master_password, PRIVATE_KEY_PATH)
        signature = private_key.sign(
            ciphertext,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Create export container
        export_data = {
            "version": 1,
            "vault_label": vault_label,
            "exported_at": datetime.utcnow().isoformat() + 'Z',
            "recipient": recipient_name,
            "encrypted_key": base64.b64encode(encrypted_key).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "signature": base64.b64encode(signature).decode('utf-8')
        }
        
        # Save to file
        export_filename = f"{vault_label.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pvgx"
        export_path = os.path.join(EXPORT_DIR, export_filename)
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return export_path
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to export vault: {e}")


def import_vault(import_file: str, master_password: str, sender_pubkey_path: Optional[str] = None) -> Tuple[dict, str]:
    """
    Import and decrypt vault from .pvgx file.
    
    Args:
        import_file: Path to .pvgx export file
        master_password: User's master password (for private key)
        sender_pubkey_path: Path to sender's public key for signature verification (optional)
    
    Returns:
        Tuple of (vault_data, vault_label)
    
    Raises:
        ValueError: If import fails, signature invalid, or password wrong
    """
    try:
        if not os.path.exists(import_file):
            raise ValueError(f"Import file not found: {import_file}")
        
        # Load export data
        with open(import_file, 'r') as f:
            export_data = json.load(f)
        
        # Validate structure
        required_fields = ["version", "vault_label", "encrypted_key", "nonce", "tag", "ciphertext"]
        for field in required_fields:
            if field not in export_data:
                raise ValueError(f"Corrupted or invalid vault export: missing '{field}'")
        
        # Decode base64 fields
        encrypted_key = base64.b64decode(export_data['encrypted_key'])
        nonce = base64.b64decode(export_data['nonce'])
        tag = base64.b64decode(export_data['tag'])
        ciphertext = base64.b64decode(export_data['ciphertext'])
        
        # Verify signature if provided
        if 'signature' in export_data and sender_pubkey_path:
            signature = base64.b64decode(export_data['signature'])
            sender_public_key = load_public_key(sender_pubkey_path)
            
            try:
                sender_public_key.verify(
                    signature,
                    ciphertext,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except Exception:
                raise ValueError("Invalid signature - vault may have been tampered with")
        
        # Decrypt AES key with private key
        private_key = load_private_key(master_password, PRIVATE_KEY_PATH)
        
        try:
            aes_key = private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        except Exception:
            raise ValueError("Failed to decrypt vault - you may not be the intended recipient")
        
        # Decrypt vault data with AES key
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            vault_data = json.loads(plaintext.decode('utf-8'))
        except Exception:
            raise ValueError("Corrupted or invalid vault data")
        
        vault_label = export_data['vault_label']
        
        return vault_data, vault_label
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to import vault: {e}")


def keypair_exists() -> bool:
    """Check if keypair already exists."""
    return os.path.exists(PUBLIC_KEY_PATH) and os.path.exists(PRIVATE_KEY_PATH)


def get_public_key_fingerprint() -> str:
    """
    Get SHA-256 fingerprint of public key for identification.
    
    Returns:
        Hex string of public key fingerprint
    """
    try:
        public_key = load_public_key(PUBLIC_KEY_PATH)
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        from hashlib import sha256
        fingerprint = sha256(public_pem).hexdigest()
        return fingerprint[:16]  # First 16 chars for display
        
    except Exception:
        return "unknown"
