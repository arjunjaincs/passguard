"""
Security audit module for PassGuard vault credentials.

Provides functions to:
- Detect reused passwords
- Identify weak passwords (entropy-based)
- Find passwords containing personal information
- Detect similar passwords (Levenshtein distance)
- Generate JSON and Markdown security reports
"""

import json
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


def calculate_entropy(password: str) -> float:
    """
    Calculate Shannon entropy of a password in bits.
    
    Args:
        password: The password string to analyze
        
    Returns:
        Entropy in bits (approximate)
    """
    if not password:
        return 0.0
    
    # Count character types
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    
    # Estimate character space
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
    
    # Entropy = log2(charset_size ^ length)
    return len(password) * math.log2(charset_size)


def classify_password_strength(password: str) -> Tuple[str, float, List[str]]:
    """
    Classify password strength based on entropy and composition.
    
    Args:
        password: The password to classify
        
    Returns:
        Tuple of (strength_label, entropy_bits, issues_list)
        strength_label: "critical", "weak", "medium", "strong"
    """
    issues = []
    entropy = calculate_entropy(password)
    
    if len(password) < 8:
        issues.append("Length < 8 characters")
        return ("critical", entropy, issues)
    
    if len(password) < 12:
        issues.append("Length < 12 characters (recommended)")
    
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    
    if not has_lower:
        issues.append("No lowercase letters")
    if not has_upper:
        issues.append("No uppercase letters")
    if not has_digit:
        issues.append("No digits")
    if not has_symbol:
        issues.append("No special characters")
    
    # Classify by entropy
    if entropy < 40:
        return ("critical", entropy, issues)
    elif entropy < 60:
        return ("weak", entropy, issues)
    elif entropy < 80:
        return ("medium", entropy, issues)
    else:
        return ("strong", entropy, issues)


def mask_password(password: str) -> str:
    """
    Mask password showing only first and last character.
    
    Args:
        password: Password to mask
        
    Returns:
        Masked password like "p******d"
    """
    if len(password) <= 2:
        return "*" * len(password)
    return password[0] + "*" * (len(password) - 2) + password[-1]


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Args:
        s1, s2: Strings to compare
        
    Returns:
        Edit distance
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def detect_reused_passwords(credentials: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Detect passwords used on multiple sites.
    
    Args:
        credentials: List of dicts with keys: website, username, password
        
    Returns:
        List of dicts: {masked_password, sites, count}
    """
    password_map = defaultdict(list)
    
    for cred in credentials:
        pw = cred.get("password", "")
        site = cred.get("website", "Unknown")
        if pw:
            password_map[pw].append(site)
    
    reused = []
    for pw, sites in password_map.items():
        if len(sites) >= 2:
            reused.append({
                "masked_password": mask_password(pw),
                "sites": sites,
                "count": len(sites)
            })
    
    # Sort by count descending
    reused.sort(key=lambda x: x["count"], reverse=True)
    return reused


def detect_weak_passwords(credentials: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Detect weak passwords based on entropy and composition.
    
    Args:
        credentials: List of credential dicts
        
    Returns:
        List of dicts: {website, username, masked_password, strength, entropy, issues}
    """
    weak = []
    
    for cred in credentials:
        pw = cred.get("password", "")
        site = cred.get("website", "Unknown")
        user = cred.get("username", "")
        
        if not pw:
            continue
        
        strength, entropy, issues = classify_password_strength(pw)
        
        if strength in ["critical", "weak"]:
            weak.append({
                "website": site,
                "username": user,
                "masked_password": mask_password(pw),
                "strength": strength,
                "entropy": round(entropy, 2),
                "issues": issues
            })
    
    # Sort by strength (critical first)
    weak.sort(key=lambda x: (0 if x["strength"] == "critical" else 1, x["entropy"]))
    return weak


def detect_pii_in_passwords(
    credentials: List[Dict[str, str]],
    user_info: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Detect passwords containing personal information.
    
    Args:
        credentials: List of credential dicts
        user_info: Optional dict with keys: name, dob, email, phone
        
    Returns:
        List of dicts: {website, username, masked_password, matched_fields}
    """
    if not user_info:
        return []
    
    matches = []
    
    # Extract PII tokens (case-insensitive)
    pii_tokens = []
    if user_info.get("name"):
        # Split name into parts
        name_parts = re.split(r'\s+', user_info["name"].lower())
        pii_tokens.extend([p for p in name_parts if len(p) >= 3])
    
    if user_info.get("dob"):
        # Extract year, month, day
        dob_parts = re.findall(r'\d+', user_info["dob"])
        pii_tokens.extend(dob_parts)
    
    if user_info.get("email"):
        # Extract username part of email
        email_user = user_info["email"].split("@")[0].lower()
        if len(email_user) >= 3:
            pii_tokens.append(email_user)
    
    if user_info.get("phone"):
        # Extract digits
        phone_digits = re.sub(r'\D', '', user_info["phone"])
        if len(phone_digits) >= 4:
            pii_tokens.append(phone_digits)
    
    for cred in credentials:
        pw = cred.get("password", "").lower()
        site = cred.get("website", "")
        user = cred.get("username", "")
        
        if not pw:
            continue
        
        matched_fields = []
        for token in pii_tokens:
            if token and token in pw:
                matched_fields.append(f"Contains '{token}'")
        
        if matched_fields:
            matches.append({
                "website": site,
                "username": user,
                "masked_password": mask_password(cred.get("password", "")),
                "matched_fields": matched_fields
            })
    
    return matches


def detect_similar_passwords(credentials: List[Dict[str, str]], threshold: int = 3) -> List[Dict[str, Any]]:
    """
    Detect similar passwords using Levenshtein distance.
    
    Args:
        credentials: List of credential dicts
        threshold: Maximum edit distance to consider similar
        
    Returns:
        List of similarity groups: {passwords: [masked], sites: [...], distance: int}
    """
    passwords = [(cred.get("password", ""), cred.get("website", "Unknown")) for cred in credentials]
    passwords = [(pw, site) for pw, site in passwords if pw]
    
    similarity_groups = []
    seen = set()
    
    for i, (pw1, site1) in enumerate(passwords):
        if pw1 in seen:
            continue
        
        group_passwords = [pw1]
        group_sites = [site1]
        
        for j, (pw2, site2) in enumerate(passwords):
            if i != j and pw2 not in seen and pw1 != pw2:
                dist = levenshtein_distance(pw1, pw2)
                if dist <= threshold:
                    group_passwords.append(pw2)
                    group_sites.append(site2)
                    seen.add(pw2)
        
        if len(group_passwords) > 1:
            seen.add(pw1)
            similarity_groups.append({
                "passwords": [mask_password(p) for p in group_passwords],
                "sites": group_sites,
                "max_distance": threshold
            })
    
    return similarity_groups


def generate_recommendations(
    reused: List[Dict],
    weak: List[Dict],
    pii_matches: List[Dict],
    similar: List[Dict]
) -> List[str]:
    """
    Generate prioritized recommendations based on findings.
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    critical_count = sum(1 for w in weak if w["strength"] == "critical")
    if critical_count > 0:
        recommendations.append(f"🔴 CRITICAL: {critical_count} password(s) are critically weak (< 8 chars or very low entropy). Change immediately.")
    
    if reused:
        recommendations.append(f"🔴 HIGH: {len(reused)} password(s) are reused across multiple sites. Use unique passwords for each site.")
    
    if pii_matches:
        recommendations.append(f"🟠 HIGH: {len(pii_matches)} password(s) contain personal information. Avoid using names, dates, or emails in passwords.")
    
    if similar:
        recommendations.append(f"🟡 MEDIUM: {len(similar)} group(s) of similar passwords detected. Avoid minor variations of the same password.")
    
    weak_count = sum(1 for w in weak if w["strength"] == "weak")
    if weak_count > 0:
        recommendations.append(f"🟡 MEDIUM: {weak_count} password(s) are weak. Increase length and complexity.")
    
    if not recommendations:
        recommendations.append("✅ No major security issues detected. Keep practicing good password hygiene!")
    
    return recommendations


def run_security_audit(
    credentials: List[Dict[str, str]],
    user_info: Optional[Dict[str, str]] = None,
    report_name: str = "Security Audit"
) -> Dict[str, Any]:
    """
    Run complete security audit on vault credentials.
    
    Args:
        credentials: List of credential dicts (website, username, password)
        user_info: Optional personal info for PII detection
        report_name: Display name for the report
        
    Returns:
        Complete audit report dict
        
    Raises:
        ValueError: If credentials format is invalid
    """
    if not isinstance(credentials, list):
        raise ValueError("Credentials must be a list")
    
    for cred in credentials:
        if not isinstance(cred, dict):
            raise ValueError("Each credential must be a dict")
        if "password" not in cred:
            raise ValueError("Each credential must have a 'password' key")
    
    # Run all checks
    reused = detect_reused_passwords(credentials)
    weak = detect_weak_passwords(credentials)
    pii_matches = detect_pii_in_passwords(credentials, user_info)
    similar = detect_similar_passwords(credentials)
    
    # Generate recommendations
    recommendations = generate_recommendations(reused, weak, pii_matches, similar)
    
    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "report_name": report_name,
        "user_profile": {
            "has_name": bool(user_info and user_info.get("name")),
            "has_dob": bool(user_info and user_info.get("dob")),
            "has_email": bool(user_info and user_info.get("email")),
            "has_phone": bool(user_info and user_info.get("phone"))
        } if user_info else {},
        "stats": {
            "total_credentials": len(credentials),
            "reused_passwords": len(reused),
            "weak_passwords": len(weak),
            "pii_matches": len(pii_matches),
            "similarity_groups": len(similar)
        },
        "findings": {
            "reused_passwords": reused,
            "weak_passwords": weak,
            "pii_matches": pii_matches,
            "similarity_groups": similar
        },
        "recommendations": recommendations
    }
    
    return report


def generate_markdown_report(report: Dict[str, Any]) -> str:
    """
    Generate human-readable Markdown summary from audit report.
    
    Args:
        report: Audit report dict from run_security_audit
        
    Returns:
        Markdown-formatted string
    """
    md = []
    md.append(f"# {report['report_name']}")
    md.append(f"\n**Generated:** {report['timestamp']}\n")
    
    stats = report['stats']
    md.append("## Summary")
    md.append(f"- **Total Credentials:** {stats['total_credentials']}")
    md.append(f"- **Reused Passwords:** {stats['reused_passwords']}")
    md.append(f"- **Weak Passwords:** {stats['weak_passwords']}")
    md.append(f"- **PII Matches:** {stats['pii_matches']}")
    md.append(f"- **Similarity Groups:** {stats['similarity_groups']}\n")
    
    md.append("## Recommendations")
    for rec in report['recommendations']:
        md.append(f"- {rec}")
    md.append("")
    
    findings = report['findings']
    
    # Reused passwords
    if findings['reused_passwords']:
        md.append("## 🔴 Reused Passwords")
        for item in findings['reused_passwords'][:10]:  # Top 10
            md.append(f"- **{item['masked_password']}** used on {item['count']} sites:")
            for site in item['sites']:
                md.append(f"  - {site}")
        md.append("")
    
    # Weak passwords
    if findings['weak_passwords']:
        md.append("## 🔴 Weak Passwords")
        md.append("| Website | Username | Password | Strength | Entropy | Issues |")
        md.append("|---------|----------|----------|----------|---------|--------|")
        for item in findings['weak_passwords'][:10]:  # Top 10
            issues_str = "; ".join(item['issues'][:2])  # First 2 issues
            md.append(f"| {item['website']} | {item['username']} | {item['masked_password']} | {item['strength']} | {item['entropy']} | {issues_str} |")
        md.append("")
    
    # PII matches
    if findings['pii_matches']:
        md.append("## 🟠 Passwords Containing Personal Info")
        for item in findings['pii_matches'][:10]:
            md.append(f"- **{item['website']}** ({item['username']}): {', '.join(item['matched_fields'])}")
        md.append("")
    
    # Similar passwords
    if findings['similarity_groups']:
        md.append("## 🟡 Similar Password Groups")
        for i, group in enumerate(findings['similarity_groups'][:5], 1):
            md.append(f"{i}. Sites: {', '.join(group['sites'])}")
        md.append("")
    
    return "\n".join(md)


def save_report_json(report: Dict[str, Any], filepath: str) -> None:
    """
    Save audit report as JSON file.
    
    Args:
        report: Audit report dict
        filepath: Path to save JSON file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def save_report_markdown(report: Dict[str, Any], filepath: str) -> None:
    """
    Save audit report as Markdown file.
    
    Args:
        report: Audit report dict
        filepath: Path to save Markdown file
    """
    md_content = generate_markdown_report(report)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
