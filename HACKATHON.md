# 🔐 PassGuard - Hackathon Presentation

**Team**: Guneet, Daksh, Arjun

---

## 🎯 Quick Pitch (30 seconds)

PassGuard is a **secure, local-first password manager** with browser autofill. Unlike cloud-based solutions that get breached, PassGuard keeps your passwords encrypted on YOUR device with military-grade AES-256-GCM encryption. One-click autofill, breach detection, and secure vault sharing - all without ever touching the cloud.

---

## 🔐 The Problem

- **70% of data breaches** happen due to weak/reused passwords
- Average person has **100+ accounts** to manage
- Cloud password managers get **breached** (LastPass, etc.)
- Browser built-in managers store passwords **unencrypted**

---

## ✨ Our Solution

### Core Features
1. **Military-Grade Encryption**: AES-256-GCM + Argon2id
2. **Browser Autofill**: One-click login on any website
3. **Security Audit**: Breach detection + weak password alerts
4. **Vault Sharing**: RSA-4096 encrypted sharing
5. **100% Local**: Your passwords NEVER leave your device

---

## 🛠️ Tech Stack

### Backend (Python 3.13)
- **CustomTkinter 5.2.1** - Modern dark-themed UI framework
- **Flask 3.0.0** - Local API server for browser extension
- **Flask-CORS 4.0.0** - Cross-origin resource sharing

### Security & Cryptography
- **Argon2-cffi 23.1.0** - Memory-hard key derivation (KDF)
- **PyCryptodome 3.20.0** - AES-256-GCM encryption
- **Cryptography 41.0.7** - RSA-4096, Fernet encryption

### System Integration
- **Pystray 0.19.5** - System tray integration
- **Pillow 10.1.0** - Icon rendering
- **Pyperclip 1.8.2** - Secure clipboard management

### Features
- **ReportLab 4.0.7** - PDF export generation
- **Requests 2.31.0** - HaveIBeenPwned API integration

### Browser Extension
- **JavaScript (ES6+)** - Extension logic
- **Chrome Extension API** - Manifest V3
- **HTML5 + CSS3** - Popup UI

---

## 🎬 Demo Flow (See VIDEO_SCRIPT.md)

1. Create vault with strong password
2. Add credentials (GitHub, Gmail, etc.)
3. Install browser extension
4. One-click autofill demonstration
5. Security audit showing breach detection

---

## 🏆 Why PassGuard Wins

| Feature | PassGuard | LastPass | Browser |
|---------|-----------|----------|---------|
| Local Storage | ✅ | ❌ | ❌ |
| Open Source | ✅ | ❌ | ❌ |
| No Cloud Risk | ✅ | ❌ | ❌ |
| Free Forever | ✅ | Limited | ✅ |
| Breach Detection | ✅ | ✅ | ❌ |

---

## 📞 Links

- **GitHub**: [Your Repo]
- **Video**: [Demo Video]
- **Slides**: [Presentation]

---

**PassGuard: Your Passwords, Truly Secure** 🔐

For detailed video script, see `VIDEO_SCRIPT.md`
