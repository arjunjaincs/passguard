"""
Secure local API server for browser autofill support.
Runs only when vault is unlocked. Provides credentials via token-authenticated endpoint.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import secrets
import threading
from urllib.parse import urlparse
import logging
import os
import json
import base64
from cryptography.fernet import Fernet
import hashlib

# Disable Flask's default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

class AutofillServer:
    TOKEN_FILE = os.path.join('vaults', 'autofill_token.enc')
    # Derive encryption key from machine-specific data
    ENCRYPTION_KEY = base64.urlsafe_b64encode(
        hashlib.sha256(f"{os.getlogin()}{os.path.expanduser('~')}".encode()).digest()
    )
    
    def __init__(self, credentials: list, port: int = 5777):
        """
        Initialize the autofill server.
        
        Args:
            credentials: List of credential dictionaries from unlocked vault
            port: Port to run the server on (default: 5777)
        """
        self.credentials = credentials
        self.port = port
        self.token = self._load_or_generate_token()  # Load existing or generate new token
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for browser extension
        self.server_thread = None
        self.vault_unlocked_once = False  # Track if vault was ever unlocked this session
        
        # Rate limiting: track failed auth attempts
        self.failed_attempts = {}  # IP -> (count, last_attempt_time)
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        
        self._setup_routes()
    
    def _load_or_generate_token(self) -> str:
        """Load existing token or generate a new one."""
        try:
            if os.path.exists(self.TOKEN_FILE):
                # Read encrypted token
                with open(self.TOKEN_FILE, 'rb') as f:
                    encrypted_data = f.read()
                
                # Decrypt token
                fernet = Fernet(self.ENCRYPTION_KEY)
                decrypted_data = fernet.decrypt(encrypted_data)
                token = decrypted_data.decode('utf-8')
                
                print(f"[AutofillServer] Loaded existing token (encrypted)")
                return token
        except Exception as e:
            print(f"[AutofillServer] Error loading token: {e}")
        
        print("[AutofillServer] Generating new token...")
        return self._generate_and_save_token()
    
    def _generate_and_save_token(self) -> str:
        """Generate a new token and save it encrypted."""
        token = secrets.token_urlsafe(32)
        try:
            os.makedirs('vaults', exist_ok=True)
            
            # Encrypt token before saving
            fernet = Fernet(self.ENCRYPTION_KEY)
            encrypted_token = fernet.encrypt(token.encode('utf-8'))
            
            with open(self.TOKEN_FILE, 'wb') as f:
                f.write(encrypted_token)
            
            print(f"[AutofillServer] Token saved (encrypted)")
        except Exception as e:
            print(f"[AutofillServer] Warning: Could not save token: {e}")
        return token
        
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            # Only allow from localhost for security
            if request.remote_addr not in ['127.0.0.1', 'localhost', '::1']:
                return jsonify({"error": "Forbidden"}), 403
            
            vault_status = "ready" if self.vault_unlocked_once else "locked"
            return jsonify({"status": "running", "vault": vault_status}), 200
        
        @self.app.route('/get_credentials', methods=['GET'])
        def get_credentials():
            """
            Get credentials for a specific domain.
            Requires token authentication.
            """
            # Only allow from localhost for security
            if request.remote_addr not in ['127.0.0.1', 'localhost', '::1']:
                return jsonify({"error": "Forbidden"}), 403
            
            # Check rate limiting
            client_ip = request.remote_addr
            if self._is_rate_limited(client_ip):
                return jsonify({"error": "Too Many Requests", "message": "Too many failed attempts. Try again later."}), 429
            
            # Check if vault was ever unlocked this session
            if not self.vault_unlocked_once:
                return jsonify({"error": "Vault Not Unlocked", "message": "Please unlock vault first"}), 403
            
            # Verify token
            auth_token = request.headers.get('Authorization')
            if not auth_token or auth_token != f"Bearer {self.token}":
                self._record_failed_attempt(client_ip)
                return jsonify({"error": "Unauthorized", "message": "Invalid or missing token"}), 401
            
            # Clear failed attempts on successful auth
            if client_ip in self.failed_attempts:
                del self.failed_attempts[client_ip]
            
            # Get domain from query params
            domain = request.args.get('domain', '').strip()
            if not domain:
                return jsonify({"error": "Bad Request", "message": "Domain parameter required"}), 400
            
            # Sanitize domain input to prevent injection
            domain = domain.replace('\x00', '').replace('\n', '').replace('\r', '')
            
            # Normalize domain (remove protocol, www, etc.)
            domain_normalized = self._normalize_domain(domain)
            
            # Search for matching credentials
            matches = []
            print(f"[AutofillServer] Looking for domain: {domain_normalized}")
            for cred in self.credentials:
                cred_domain = self._normalize_domain(cred.get('website', ''))
                print(f"[AutofillServer] Checking: {cred_domain} (username: {cred.get('username', 'N/A')})")
                if domain_normalized in cred_domain or cred_domain in domain_normalized:
                    print(f"[AutofillServer] ✓ Match found!")
                    matches.append({
                        'website': cred['website'],
                        'username': cred['username'],
                        'password': cred['password']
                    })
            
            if not matches:
                return jsonify({"error": "Not Found", "message": f"No credentials found for {domain}"}), 404
            
            # Return first match (or all matches if multiple)
            if len(matches) == 1:
                return jsonify({"success": True, "credential": matches[0]}), 200
            else:
                return jsonify({"success": True, "credentials": matches, "multiple": True}), 200
        
        @self.app.route('/get_token', methods=['GET'])
        def get_token():
            """
            Get the current authentication token.
            This endpoint is only accessible from localhost.
            """
            # Only allow from localhost
            if request.remote_addr not in ['127.0.0.1', 'localhost', '::1']:
                return jsonify({"error": "Forbidden"}), 403
            
            return jsonify({"token": self.token}), 200
    
    def _is_rate_limited(self, ip: str) -> bool:
        """Check if an IP is rate limited due to failed attempts."""
        import time
        
        if ip not in self.failed_attempts:
            return False
        
        count, last_attempt = self.failed_attempts[ip]
        
        # Check if lockout period has expired
        if time.time() - last_attempt > self.lockout_duration:
            del self.failed_attempts[ip]
            return False
        
        return count >= self.max_failed_attempts
    
    def _record_failed_attempt(self, ip: str):
        """Record a failed authentication attempt."""
        import time
        
        if ip in self.failed_attempts:
            count, _ = self.failed_attempts[ip]
            self.failed_attempts[ip] = (count + 1, time.time())
        else:
            self.failed_attempts[ip] = (1, time.time())
    
    def _normalize_domain(self, url: str) -> str:
        """
        Normalize a URL/domain for matching.
        Handles: https://www.reddit.com, www.reddit.com, reddit.com
        
        Args:
            url: URL or domain string
            
        Returns:
            Normalized domain string (e.g., "reddit.com")
        """
        try:
            # Remove protocol if present
            if '://' in url:
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path
            else:
                domain = url
            
            # Convert to lowercase
            domain = domain.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Remove port if present
            if ':' in domain and not domain.count(':') > 1:  # Not IPv6
                domain = domain.split(':')[0]
            
            # Remove trailing slash and path
            domain = domain.split('/')[0]
            
            # Remove any remaining whitespace
            domain = domain.strip()
            
            return domain
        except Exception as e:
            print(f"[AutofillServer] Error normalizing domain '{url}': {e}")
            return url.lower().strip()
    
    def start(self):
        """Start the Flask server in a background thread."""
        if self.server_thread and self.server_thread.is_alive():
            self.vault_unlocked_once = True  # Mark vault as unlocked
            return  # Already running
        
        def run_server():
            self.app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.vault_unlocked_once = True  # Mark vault as unlocked
        print(f"[AutofillServer] Started on http://127.0.0.1:{self.port}")
        print(f"[AutofillServer] Token: {self.token}")
    
    def stop(self):
        """Stop the Flask server."""
        # Don't reset vault_unlocked_once - it stays true for the session
        # Flask doesn't have a clean shutdown method in threaded mode
        # The daemon thread will be terminated when the main app closes
        print("[AutofillServer] Stopped (extension still works)")
    
    def get_token(self) -> str:
        """Get the current authentication token."""
        return self.token
    
    def update_credentials(self, credentials: list):
        """Update credentials when vault data changes."""
        self.credentials = credentials
