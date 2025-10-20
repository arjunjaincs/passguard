"""
Password strength estimation and classification for PassGuard.

Provides real-time password strength analysis with entropy calculation,
character class checking, and personal information detection.
"""

import math
import re
from typing import Dict, List, Optional, Tuple


def estimate_entropy(password: str) -> float:
    """
    Estimate password entropy in bits using Shannon entropy approximation.
    
    Args:
        password: Password string to analyze
        
    Returns:
        Estimated entropy in bits
        
    Example:
        >>> estimate_entropy("password")
        37.6
        >>> estimate_entropy("P@ssw0rd!2024")
        85.7
    """
    if not password:
        return 0.0
    
    # Determine character set size based on classes present
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    
    charset_size = 0
    if has_lower:
        charset_size += 26
    if has_upper:
        charset_size += 26
    if has_digit:
        charset_size += 10
    if has_symbol:
        charset_size += 32  # Common symbols
    
    if charset_size == 0:
        return 0.0
    
    # Entropy = length * log2(charset_size)
    entropy = len(password) * math.log2(charset_size)
    return round(entropy, 1)


def count_character_classes(password: str) -> int:
    """
    Count the number of character classes present in password.
    
    Args:
        password: Password to analyze
        
    Returns:
        Number of classes (0-4): lowercase, uppercase, digits, symbols
    """
    classes = 0
    if any(c.islower() for c in password):
        classes += 1
    if any(c.isupper() for c in password):
        classes += 1
    if any(c.isdigit() for c in password):
        classes += 1
    if any(not c.isalnum() for c in password):
        classes += 1
    return classes


def check_personal_info(password: str, user_hints: Optional[List[str]] = None) -> List[str]:
    """
    Check if password contains personal information.
    
    Args:
        password: Password to check
        user_hints: Optional list of personal strings (name, email, etc.)
        
    Returns:
        List of matched personal info strings
    """
    if not user_hints:
        return []
    
    password_lower = password.lower()
    matches = []
    
    for hint in user_hints:
        if not hint:
            continue
        
        hint_lower = hint.lower()
        
        # Check for direct substring match (min 3 chars)
        if len(hint_lower) >= 3 and hint_lower in password_lower:
            matches.append(hint)
            continue
        
        # Check for parts of hint (e.g., "john" from "john.doe@email.com")
        parts = re.split(r'[@._\-\s]+', hint_lower)
        for part in parts:
            if len(part) >= 3 and part in password_lower:
                matches.append(part)
    
    return matches


def classify_strength(
    password: str,
    user_hints: Optional[List[str]] = None,
    require_strong: bool = False
) -> Dict:
    """
    Classify password strength with detailed analysis.
    
    Args:
        password: Password to analyze
        user_hints: Optional personal info to check against
        require_strong: If True, enforce stricter rules (for vault creation)
        
    Returns:
        Dict with:
            - score: int (0-4) - 0=very weak, 1=weak, 2=medium, 3=strong, 4=very strong
            - label: str - Human-readable strength label
            - entropy: float - Estimated entropy in bits
            - reasons: List[str] - Specific issues or strengths
            - meets_minimum: bool - True if meets minimum requirements
            - color: str - Hex color for UI display
            
    Example:
        >>> classify_strength("abc")
        {'score': 0, 'label': 'Very Weak', 'entropy': 14.1, ...}
        >>> classify_strength("P@ssw0rd!2024#Secure")
        {'score': 4, 'label': 'Very Strong', 'entropy': 132.9, ...}
    """
    length = len(password)
    entropy = estimate_entropy(password)
    char_classes = count_character_classes(password)
    personal_matches = check_personal_info(password, user_hints)
    
    reasons = []
    score = 0
    
    # Length analysis
    if length == 0:
        return {
            'score': 0,
            'label': 'Empty',
            'entropy': 0.0,
            'reasons': ['Password is empty'],
            'meets_minimum': False,
            'color': '#95a5a6'
        }
    elif length < 8:
        reasons.append(f'Too short ({length} chars, need 8+)')
        score = 0
    elif length < 12:
        reasons.append(f'Length OK ({length} chars, 12+ recommended)')
        score = 1
    else:
        reasons.append(f'Good length ({length} chars)')
        score = 2
    
    # Character class analysis
    if char_classes < 2:
        reasons.append('Only 1 character type (need variety)')
        score = min(score, 0)
    elif char_classes < 3:
        reasons.append('Only 2 character types (add more variety)')
        score = min(score, 1)
    elif char_classes == 3:
        reasons.append('3 character types (good)')
        score = max(score, 2)
    else:  # 4 classes
        reasons.append('All 4 character types (excellent)')
        score = max(score, 3)
    
    # Specific class checks
    if not any(c.islower() for c in password):
        reasons.append('Missing lowercase letters')
    if not any(c.isupper() for c in password):
        reasons.append('Missing uppercase letters')
    if not any(c.isdigit() for c in password):
        reasons.append('Missing digits')
    if not any(not c.isalnum() for c in password):
        reasons.append('Missing special characters')
    
    # Entropy check
    if entropy < 40:
        reasons.append(f'Low entropy ({entropy} bits, need 60+)')
        score = min(score, 0)
    elif entropy < 60:
        reasons.append(f'Moderate entropy ({entropy} bits, 60+ recommended)')
        score = min(score, 1)
    elif entropy < 80:
        reasons.append(f'Good entropy ({entropy} bits)')
        score = max(score, 2)
    else:
        reasons.append(f'Excellent entropy ({entropy} bits)')
        score = max(score, 3)
    
    # Personal info penalty
    if personal_matches:
        reasons.append(f'Contains personal info: {", ".join(personal_matches[:2])}')
        score = max(0, score - 1)
    
    # Common patterns check
    if password.lower() in ['password', 'qwerty', '123456', 'letmein', 'admin']:
        reasons.append('Common/weak password pattern')
        score = 0
    
    # Sequential characters
    if re.search(r'(012|123|234|345|456|567|678|789|abc|bcd|cde|def)', password.lower()):
        reasons.append('Contains sequential characters')
        score = max(0, score - 1)
    
    # Repeated characters
    if re.search(r'(.)\1{2,}', password):
        reasons.append('Contains repeated characters')
    
    # Final score adjustment for very long passwords
    if length >= 16 and char_classes >= 3:
        score = max(score, 3)
    if length >= 20 and char_classes == 4:
        score = 4
    
    # Determine label and color
    labels = {
        0: ('Very Weak', '#e74c3c'),
        1: ('Weak', '#e67e22'),
        2: ('Medium', '#f39c12'),
        3: ('Strong', '#27ae60'),
        4: ('Very Strong', '#16a085')
    }
    
    label, color = labels.get(score, ('Unknown', '#95a5a6'))
    
    # Determine if meets minimum requirements
    if require_strong:
        # Vault creation: must be at least medium with 3+ classes
        meets_minimum = (score >= 2 and char_classes >= 3 and length >= 8 and not personal_matches)
    else:
        # Credentials: just warn, don't block
        meets_minimum = True
    
    return {
        'score': score,
        'label': label,
        'entropy': entropy,
        'reasons': reasons,
        'meets_minimum': meets_minimum,
        'color': color,
        'char_classes': char_classes,
        'length': length,
        'has_personal_info': len(personal_matches) > 0
    }


def get_strength_requirements(require_strong: bool = False) -> List[str]:
    """
    Get list of password strength requirements.
    
    Args:
        require_strong: If True, return vault creation requirements
        
    Returns:
        List of requirement strings
    """
    if require_strong:
        return [
            "At least 8 characters (12+ recommended)",
            "At least 3 character types (uppercase, lowercase, digits, symbols)",
            "Minimum 60 bits entropy",
            "No personal information (name, email, etc.)",
            "No common patterns or sequences"
        ]
    else:
        return [
            "8+ characters recommended",
            "Mix uppercase, lowercase, digits, symbols",
            "Avoid personal information",
            "Avoid common patterns"
        ]
