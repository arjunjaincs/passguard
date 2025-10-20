"""Have I Been Pwned (HIBP) Breach Check Integration.

Provides password and account breach checking using HIBP API:
- Password check: k-anonymity (only first 5 SHA1 chars sent)
- Account check: Full breach details (requires API key)

Privacy:
- Passwords never sent to server (k-anonymity model)
- Only first 5 characters of SHA1 hash transmitted
- Full hash comparison done locally

API Documentation:
- https://haveibeenpwned.com/API/v3
"""

import hashlib
import requests
from typing import List, Dict, Optional


def sha1_hex(s: str) -> str:
    """
    Compute SHA1 hash of string and return uppercase hex.
    
    Args:
        s: String to hash (typically a password)
    
    Returns:
        Uppercase hexadecimal SHA1 hash
    
    Example:
        >>> sha1_hex("password")
        '5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8'
    """
    return hashlib.sha1(s.encode('utf-8')).hexdigest().upper()


def check_password_pwned_k_anonymity(password: str) -> int:
    """
    Check if password has been pwned using k-anonymity model.
    
    Privacy-preserving: Only sends first 5 characters of SHA1 hash.
    Server returns all hashes with same prefix; client compares locally.
    
    Args:
        password: Password to check
    
    Returns:
        Number of times password appears in breaches (0 if not found)
    
    Raises:
        requests.RequestException: Network error
        ValueError: Invalid response from server
    
    Example:
        >>> count = check_password_pwned_k_anonymity("password123")
        >>> if count > 0:
        ...     print(f"Password found in {count} breaches!")
    """
    # Compute SHA1 hash
    password_hash = sha1_hex(password)
    
    # Split into prefix (first 5) and suffix (rest)
    prefix = password_hash[:5]
    suffix = password_hash[5:]
    
    # Query HIBP API with prefix only
    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        raise requests.RequestException("Request timed out - check your internet connection")
    except requests.ConnectionError:
        raise requests.RequestException("Connection failed - check your internet connection")
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            raise requests.RequestException("Rate limit exceeded - please try again later")
        raise requests.RequestException(f"HTTP error: {e.response.status_code}")
    
    # Parse response (format: "SUFFIX:COUNT\r\n")
    lines = response.text.strip().split('\r\n')
    
    for line in lines:
        try:
            hash_suffix, count_str = line.split(':')
            if hash_suffix == suffix:
                return int(count_str)
        except ValueError:
            # Skip malformed lines
            continue
    
    # Not found in breaches
    return 0


def check_account_breached_hibp(account: str, api_key: str) -> List[Dict[str, any]]:
    """
    Check if account/email has been in data breaches.
    
    Requires HIBP API key (paid service).
    Get key at: https://haveibeenpwned.com/API/Key
    
    Args:
        account: Email address or username to check
        api_key: HIBP API key
    
    Returns:
        List of breach dictionaries with keys:
        - Name: Breach name
        - Title: Human-readable title
        - Domain: Breached domain
        - BreachDate: Date of breach (YYYY-MM-DD)
        - PwnCount: Number of accounts affected
        - Description: HTML description
        - DataClasses: List of compromised data types
    
    Raises:
        requests.RequestException: Network error or rate limit (429)
        ValueError: Invalid API key (401) or malformed response
    
    Example:
        >>> breaches = check_account_breached_hibp("test@example.com", "api_key")
        >>> for breach in breaches:
        ...     print(f"{breach['Title']} - {breach['BreachDate']}")
    """
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{account}"
    
    headers = {
        'hibp-api-key': api_key,
        'user-agent': 'PassGuard-Password-Manager'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # 404 = No breaches found (success case)
        if response.status_code == 404:
            return []
        
        # 401 = Invalid API key
        if response.status_code == 401:
            raise ValueError("Invalid HIBP API key - please check your key at haveibeenpwned.com")
        
        # 429 = Rate limit
        if response.status_code == 429:
            raise requests.RequestException("Rate limit exceeded - please wait and try again later")
        
        response.raise_for_status()
        
        # Parse JSON response
        breaches = response.json()
        
        if not isinstance(breaches, list):
            raise ValueError("Unexpected response format from HIBP API")
        
        return breaches
        
    except requests.Timeout:
        raise requests.RequestException("Request timed out - check your internet connection")
    except requests.ConnectionError:
        raise requests.RequestException("Connection failed - check your internet connection")
    except requests.JSONDecodeError:
        raise ValueError("Invalid JSON response from HIBP API")
    except requests.HTTPError as e:
        raise requests.RequestException(f"HTTP error: {e.response.status_code}")


def format_breach_summary(breaches: List[Dict]) -> str:
    """
    Format breach list into human-readable summary.
    
    Args:
        breaches: List of breach dictionaries from check_account_breached_hibp
    
    Returns:
        Formatted string summary
    
    Example:
        >>> summary = format_breach_summary(breaches)
        >>> print(summary)
        Found in 3 breaches:
        - Adobe (2013-10-04): 152 million accounts
        - LinkedIn (2012-05-05): 164 million accounts
        ...
    """
    if not breaches:
        return "No breaches found ✓"
    
    summary = f"Found in {len(breaches)} breach(es):\n"
    
    for breach in breaches[:5]:  # Limit to 5 for brevity
        name = breach.get('Title', breach.get('Name', 'Unknown'))
        date = breach.get('BreachDate', 'Unknown date')
        pwn_count = breach.get('PwnCount', 0)
        
        # Format count
        if pwn_count >= 1_000_000:
            count_str = f"{pwn_count / 1_000_000:.1f}M"
        elif pwn_count >= 1_000:
            count_str = f"{pwn_count / 1_000:.1f}K"
        else:
            count_str = str(pwn_count)
        
        summary += f"  • {name} ({date}): {count_str} accounts\n"
    
    if len(breaches) > 5:
        summary += f"  ... and {len(breaches) - 5} more\n"
    
    return summary.strip()


# Module-level test
if __name__ == "__main__":
    print("=" * 60)
    print("HIBP Breach Check Test")
    print("=" * 60)
    
    # Test 1: SHA1 hash
    print("\n[Test 1] SHA1 Hash")
    test_hash = sha1_hex("password")
    expected = "5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8"
    print(f"Input: 'password'")
    print(f"Hash:  {test_hash}")
    print(f"Match: {test_hash == expected} ✓" if test_hash == expected else "FAIL ✗")
    
    # Test 2: Known pwned password
    print("\n[Test 2] Known Pwned Password")
    print("Checking 'password' (known to be pwned)...")
    try:
        count = check_password_pwned_k_anonymity("password")
        print(f"Result: Found in {count:,} breaches")
        if count > 0:
            print("✓ Test passed (password is pwned)")
        else:
            print("✗ Test failed (should be pwned)")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 3: Secure password (likely not pwned)
    print("\n[Test 3] Secure Password")
    secure_pw = "MyS3cur3P@ssw0rd!2024#XyZ"
    print(f"Checking '{secure_pw}'...")
    try:
        count = check_password_pwned_k_anonymity(secure_pw)
        if count == 0:
            print("✓ Not found in breaches (good!)")
        else:
            print(f"⚠ Found in {count:,} breaches (consider changing)")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Test 4: Account check (requires API key)
    print("\n[Test 4] Account Breach Check")
    print("Skipped (requires HIBP API key)")
    print("To test: Set HIBP_API_KEY environment variable")
    
    import os
    api_key = os.environ.get('HIBP_API_KEY')
    if api_key:
        test_email = "test@example.com"
        print(f"Checking {test_email}...")
        try:
            breaches = check_account_breached_hibp(test_email, api_key)
            print(format_breach_summary(breaches))
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
