"""
Validation rules (copied from the Milestone 1 login).

Implements the field validation requirements specified by Infosys Springboard 7.0:
1. Mandatory fields verification
2. Email format rule: >= 2 chars before @, >= 2 chars between @ and dot, >= 2 chars after final dot
3. Password complexity: >= 8 chars, >= 1 uppercase, >= 1 lowercase, >= 1 digit, >= 1 special symbol
4. Password confirmation matching
"""

import re
from typing import Tuple, Dict, Any

SPECIAL_CHARACTERS = set("!@#$%^&*(),.?\":{}|<>~`_-+=/\\[];'")

def validate_mandatory_fields(fields: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Checks that none of the provided form fields are empty or whitespace-only.
    """
    for field_name, value in fields.items():
        if value is None:
            return False, f"'{field_name}' is required."
        if isinstance(value, str) and not value.strip():
            return False, f"'{field_name}' cannot be empty."
    return True, ""

def validate_email_format(email: str) -> Tuple[bool, str]:
    """
    Validates email format against the official Infosys Milestone 1 rule:
    - At least 2 characters before the '@'
    - At least 2 characters between the '@' and the dot
    - At least 2 characters after the final dot
    Example compliant shape: ab@cd.ef
    """
    if not email or not isinstance(email, str):
        return False, "Email address is required."

    email = email.strip()
    if "@" not in email:
        return False, "Email must contain an '@' symbol."

    parts = email.split("@")
    if len(parts) != 2:
        return False, "Email must contain exactly one '@' symbol."

    local_part, domain_part = parts[0], parts[1]

    # Rule 1: At least 2 characters before the @
    if len(local_part) < 2:
        return False, "Email must have at least 2 characters before the '@' symbol."

    if "." not in domain_part:
        return False, "Email domain must contain at least one '.' (dot)."

    domain_subparts = domain_part.split(".")
    # Intermediate domain name (between @ and first dot) must be at least 2 characters
    if len(domain_subparts[0]) < 2:
        return False, "Email domain must have at least 2 characters between '@' and the dot."

    # Final domain extension (after final dot) must be at least 2 characters
    final_extension = domain_subparts[-1]
    if len(final_extension) < 2:
        return False, "Email domain must have at least 2 characters after the final dot."

    # Standard general syntax check
    email_regex = r"^[a-zA-Z0-9_.+-]{2,}@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        return False, "Invalid email format. Format must match pattern like ab@cd.ef"

    return True, ""

def validate_password_complexity(password: str) -> Tuple[bool, str]:
    """
    Validates password against Infosys complexity requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special symbol
    """
    if not password or not isinstance(password, str):
        return False, "Password is required."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    has_upper = any(c.isupper() for c in password)
    if not has_upper:
        return False, "Password must contain at least one uppercase letter (A-Z)."

    has_lower = any(c.islower() for c in password)
    if not has_lower:
        return False, "Password must contain at least one lowercase letter (a-z)."

    has_digit = any(c.isdigit() for c in password)
    if not has_digit:
        return False, "Password must contain at least one numeric digit (0-9)."

    has_special = any(c in SPECIAL_CHARACTERS for c in password)
    if not has_special:
        return False, "Password must contain at least one special symbol (e.g. !@#$%^&*)."

    return True, ""

def validate_password_confirmation(password: str, confirm_password: str) -> Tuple[bool, str]:
    """
    Validates that password and confirm password match exactly.
    """
    if password != confirm_password:
        return False, "Confirm Password does not match Password."
    return True, ""

def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validates username format (min 3 chars, alphanumeric and underscores).
    """
    if not username or not isinstance(username, str):
        return False, "Username is required."
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores."
    return True, ""
