"""Enhanced vault encryption with Argon2id and AES-256-GCM.

File Format (Binary):
    [MAGIC (8 bytes)] = b'PGVLTv1\x00'  (PassGuard Vault v1)
    [HEADER_LEN (2 bytes, big-endian)] - length of JSON header
    [HEADER (HEADER_LEN bytes)] - JSON metadata (version, salt, argon params, created_at)
    [RANDOM_PAD (32-64 bytes)] - random noise for obfuscation
    [NONCE (12 bytes)] - AES-GCM nonce
    [TAG (16 bytes)] - AES-GCM authentication tag
    [CIPHERTEXT (remaining)] - AES-GCM encrypted credentials JSON

Security:
    - Argon2id with time_cost=4, memory_cost=131072 KB (128 MiB), parallelism=2
    - AES-256-GCM for authenticated encryption
    - Random salt per vault
    - File appears as random binary when opened in text editor
    - Backward compatible with old base64 format
"""

import json
import os
import struct
from datetime import datetime
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from argon2.low_level import hash_secret_raw, Type

# File format constants
MAGIC = b'PGVLTv1\x00'  # PassGuard Vault v1
MAGIC_LEN = 8
HEADER_LEN_SIZE = 2
SALT_LEN = 16
KEY_LEN = 32
NONCE_LEN = 12
TAG_LEN = 16
MIN_PAD = 32
MAX_PAD = 64

# Argon2id parameters
# Trade-off: Higher memory_cost = more secure but slower
# Current: 128 MiB RAM, ~0.5-1s on modern CPU
# Power users can increase memory_cost to 2**18 (256 MiB) or 2**19 (512 MiB)
ARGON_TIME_COST = 4
ARGON_MEMORY_COST = 2**17  # 131072 KB = 128 MiB
ARGON_PARALLELISM = 2
ARGON_HASH_LEN = 32

def derive_key(password: str, salt: bytes, time_cost: int = ARGON_TIME_COST, 
               memory_cost: int = ARGON_MEMORY_COST, parallelism: int = ARGON_PARALLELISM) -> bytes:
    """
    Derive encryption key from password using Argon2id.
    
    Args:
        password: Master password
        salt: Random salt (16 bytes)
        time_cost: Argon2 time parameter (default: 4)
        memory_cost: Argon2 memory in KB (default: 131072 = 128 MiB)
        parallelism: Argon2 parallelism (default: 2)
    
    Returns:
        32-byte encryption key
    """
    return hash_secret_raw(
        password.encode('utf-8'),
        salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=ARGON_HASH_LEN,
        type=Type.ID
    )

def is_passguard_vault(blob: bytes) -> bool:
    """
    Check if blob is a PassGuard v1 vault file.
    
    Args:
        blob: Binary data to check
    
    Returns:
        True if blob starts with PassGuard magic header
    """
    return blob[:MAGIC_LEN] == MAGIC

def encrypt_data(password: str, data: dict) -> bytes:
    """
    Encrypt vault data with enhanced security.
    
    Creates binary vault file with:
    - Magic header for format identification
    - Metadata header (salt, argon params, timestamp)
    - Random padding for obfuscation
    - AES-256-GCM authenticated encryption
    
    Args:
        password: Master password
        data: Dictionary containing credentials
    
    Returns:
        Binary vault blob (NOT base64)
    """
    # Generate cryptographic materials
    salt = os.urandom(SALT_LEN)
    key = derive_key(password, salt)
    nonce = os.urandom(NONCE_LEN)
    
    # Encrypt credentials
    plaintext = json.dumps(data, separators=(',', ':')).encode('utf-8')
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    
    # Create metadata header
    header = {
        "version": "1",
        "salt": salt.hex(),
        "argon": {
            "time": ARGON_TIME_COST,
            "mem": ARGON_MEMORY_COST,
            "parallelism": ARGON_PARALLELISM
        },
        "created": datetime.utcnow().isoformat() + 'Z'
    }
    header_bytes = json.dumps(header, separators=(',', ':')).encode('utf-8')
    header_len = len(header_bytes)
    
    if header_len > 65535:
        raise ValueError("Header too large")
    
    # Random padding for obfuscation
    pad_len = os.urandom(1)[0] % (MAX_PAD - MIN_PAD + 1) + MIN_PAD
    random_pad = os.urandom(pad_len)
    
    # Assemble binary vault file
    vault_blob = b''.join([
        MAGIC,
        struct.pack('>H', header_len),  # Big-endian 2-byte header length
        header_bytes,
        random_pad,
        nonce,
        tag,
        ciphertext
    ])
    
    return vault_blob

def decrypt_data(password: str, blob: bytes) -> dict:
    """
    Decrypt vault data with backward compatibility.
    
    Supports:
    - New binary format (PassGuard v1 with magic header)
    - Legacy base64 format (for old vaults)
    
    Args:
        password: Master password
        blob: Binary vault data
    
    Returns:
        Decrypted credentials dictionary
    
    Raises:
        ValueError: If password is incorrect or data is corrupted
    """
    # Check for new binary format
    if is_passguard_vault(blob):
        return _decrypt_v1(password, blob)
    
    # Try legacy base64 format for backward compatibility
    try:
        return _decrypt_legacy(password, blob)
    except Exception:
        raise ValueError("Invalid password, corrupted data, or unknown vault format")

def _decrypt_v1(password: str, blob: bytes) -> dict:
    """
    Decrypt PassGuard v1 binary format.
    
    Args:
        password: Master password
        blob: Binary vault data with magic header
    
    Returns:
        Decrypted credentials dictionary
    
    Raises:
        ValueError: If password is incorrect or data is corrupted
    """
    try:
        offset = MAGIC_LEN
        
        # Read header length
        header_len = struct.unpack('>H', blob[offset:offset + HEADER_LEN_SIZE])[0]
        offset += HEADER_LEN_SIZE
        
        # Read and parse header
        header_bytes = blob[offset:offset + header_len]
        offset += header_len
        header = json.loads(header_bytes.decode('utf-8'))
        
        # Extract salt and argon parameters
        salt = bytes.fromhex(header['salt'])
        argon_params = header.get('argon', {})
        time_cost = argon_params.get('time', ARGON_TIME_COST)
        memory_cost = argon_params.get('mem', ARGON_MEMORY_COST)
        parallelism = argon_params.get('parallelism', ARGON_PARALLELISM)
        
        # Derive key
        key = derive_key(password, salt, time_cost, memory_cost, parallelism)
        
        # Skip random padding (variable length between MIN_PAD and MAX_PAD)
        # We know nonce is 12 bytes, tag is 16 bytes, so work backwards
        # Find where encrypted data starts by skipping pad
        remaining = blob[offset:]
        
        # Padding is between header and nonce
        # We need to find where nonce starts
        # Since pad length is variable (32-64 bytes), we try to find it
        # Actually, we know: pad + nonce + tag + ciphertext
        # Minimum total after header: 32 + 12 + 16 + len(ciphertext)
        # We can't know ciphertext length without decrypting
        # Solution: pad length was random 32-64, let's read it properly
        
        # Better approach: we know structure, read backwards or forward
        # Let's assume pad is next MIN_PAD to MAX_PAD bytes
        # Actually, we stored pad_len in the random bytes, but we didn't save it
        # We need to skip unknown pad length
        
        # Workaround: Try different pad lengths (32-64)
        # Or better: store pad length in header
        # For now, let's use a fixed approach:
        # We'll try to decrypt with different pad lengths
        
        # Actually simpler: we know total structure
        # remaining = pad + nonce(12) + tag(16) + ciphertext
        # We need at least MIN_PAD + 12 + 16 bytes
        # Let's calculate: remaining_len - 12 - 16 - ciphertext_len = pad_len
        # But we don't know ciphertext_len
        
        # Best solution: try each possible pad length
        last_error = None
        for pad_len in range(MIN_PAD, MAX_PAD + 1):
            try:
                test_offset = pad_len
                nonce = remaining[test_offset:test_offset + NONCE_LEN]
                tag = remaining[test_offset + NONCE_LEN:test_offset + NONCE_LEN + TAG_LEN]
                ciphertext = remaining[test_offset + NONCE_LEN + TAG_LEN:]
                
                if len(nonce) != NONCE_LEN or len(tag) != TAG_LEN:
                    continue
                
                cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
                plaintext = cipher.decrypt_and_verify(ciphertext, tag)
                return json.loads(plaintext.decode('utf-8'))
            except Exception as e:
                last_error = e
                continue
        
        raise ValueError("Invalid password or corrupted data")
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to decrypt vault: {e}")

def _decrypt_legacy(password: str, blob: bytes) -> dict:
    """
    Decrypt legacy base64 format (backward compatibility).
    
    Args:
        password: Master password
        blob: Base64-encoded vault data
    
    Returns:
        Decrypted credentials dictionary
    
    Raises:
        ValueError: If password is incorrect or data is corrupted
    """
    try:
        decoded = b64decode(blob)
        salt = decoded[:SALT_LEN]
        nonce = decoded[SALT_LEN:SALT_LEN + NONCE_LEN]
        tag = decoded[SALT_LEN + NONCE_LEN:SALT_LEN + NONCE_LEN + TAG_LEN]
        ciphertext = decoded[SALT_LEN + NONCE_LEN + TAG_LEN:]
        
        # Use legacy argon2 parameters
        key = hash_secret_raw(
            password.encode('utf-8'),
            salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=KEY_LEN,
            type=Type.ID
        )
        
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
        return json.loads(plaintext.decode('utf-8'))
    except Exception:
        raise ValueError("Invalid password or corrupted data (legacy format)")