# 🔐 Export/Import - Quick Visual Guide

## 🎯 What Is It?

Securely **backup** or **share** vaults using RSA-4096 encryption.

```
┌─────────────┐                    ┌─────────────┐
│   Device A  │ ──── .pvgx ────>   │   Device B  │
│  (Sender)   │   Encrypted File   │ (Receiver)  │
└─────────────┘                    └─────────────┘
```

**No passwords shared. Only encrypted files.**

---

## 🔑 How Keys Work

```
┌──────────────────────────────────────────────────────────┐
│  First Time: PassGuard Auto-Generates Keypair            │
└──────────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                 ↓
  📄 public.pem                    🔒 private.pem
  (Shareable)                      (Encrypted, Secret)
  
  Share with others         ←──   Never share this!
  to receive vaults                Encrypted with your
                                   master password
```

### Key Exchange Flow

```
Alice                                           Bob
  │                                              │
  │  1. Share public.pem ──────────────────────> │
  │                                              │
  │  <────────────────────── Share public.pem   │
  │                                              │
  │  2. Export vault for Bob ───────────────────>│
  │     (Encrypted with Bob's public key)        │
  │                                              │
  │                                              │ 3. Import vault
  │                                              │    (Decrypt with
  │                                              │     Bob's private key)
  │                                              │
```

---

## 📤 Export Flow

```
┌─────────────────────────────────────────────────────────┐
│  1. Click 📤 Export in PassGuard                        │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  2. Choose Export Type:                                 │
│     ○ Backup for myself                                 │
│     ○ Share with another user                           │
└─────────────────────────────────────────────────────────┘
                      ↓
         ┌────────────┴────────────┐
         ↓                         ↓
  [Backup Mode]            [Share Mode]
         │                         │
         │                         │ Select recipient's
         │                         │ public.pem
         ↓                         ↓
┌─────────────────────────────────────────────────────────┐
│  3. Vault encrypted and saved as .pvgx file             │
│     Location: vaults/exported/VaultName_xxxxx.pvgx      │
└─────────────────────────────────────────────────────────┘
```

### What Happens Behind the Scenes

```
Your Vault Data
      ↓
   AES-256-GCM Encryption (Random Key)
      ↓
   Encrypted Vault
      ↓
   AES Key → RSA-4096 Encryption (Recipient's Public Key)
      ↓
   Everything → Digital Signature (Your Private Key)
      ↓
   .pvgx File (Safe to share!)
```

---

## 📥 Import Flow

```
┌─────────────────────────────────────────────────────────┐
│  1. Click 📥 Import in PassGuard                        │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  2. Select .pvgx file                                   │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  3. (Optional) Verify sender's signature                │
│     Select sender's public.pem                          │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  4. Enter YOUR master password                          │
│     (Decrypts your private key)                         │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  5. Vault decrypted and added to your vault list        │
│     ✅ Ready to use!                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 🎬 Quick Start Examples

### Example 1: Backup to Cloud

```
1. Open vault → Click 📤 Export
2. Select "Backup for myself"
3. Save .pvgx file to Dropbox/Google Drive
4. Done! ✅

If device crashes:
1. Install PassGuard on new device
2. Click 📥 Import
3. Select .pvgx from cloud
4. Enter master password
5. Vault restored! ✅
```

### Example 2: Share with Friend

```
You                              Friend
─────────────────────────────────────────────────
1. Send your public.pem    →    Receives key
                                
                           ←    2. Exports vault
                                   for you
                                   
3. Import .pvgx file       ←    Sends .pvgx
   Enter YOUR password
   
4. Access shared vault! ✅
```

---

## 🔒 Security Summary

```
✅ RSA-4096 encryption (industry standard)
✅ AES-256-GCM (prevents tampering)
✅ Digital signatures (verify sender)
✅ No password sharing needed
✅ Each export uses unique encryption key
```

---

## ⚠️ Important Rules

### ✅ DO
- Backup `keys/` folder to USB/secure location
- Share **public.pem** freely
- Verify signatures from untrusted sources

### ❌ DON'T  
- **NEVER share private.pem** (it's your identity!)
- Don't lose your master password
- Don't skip backups

---

## 📁 File Locations

```
passguard/
├── keys/
│   ├── public.pem     ← Share this
│   └── private.pem    ← NEVER share!
│
└── vaults/exported/
    └── *.pvgx         ← Encrypted exports
```

---

## 🆘 Troubleshooting

| Error | Solution |
|-------|----------|
| "Failed to load private key" | Wrong master password |
| "Not intended recipient" | File encrypted for someone else |
| "Invalid signature" | File was tampered with |

---

**That's it!** Simple, secure vault sharing. 🎉
