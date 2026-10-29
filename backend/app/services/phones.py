"""Phone checks for elder and contact routes. Owner: Utkarsh."""

import re

# Optional leading +, then 10 to 15 digits. Surrounding whitespace is removed first.
_PHONE = re.compile(r"^\+?\d{10,15}$")
PHONE_ERROR = "Phone must be 10 to 15 digits, with an optional leading +."


def normalize_phone(phone: str) -> str:
    if not isinstance(phone, str):
        raise ValueError(PHONE_ERROR)
    text = phone.strip()
    if _PHONE.fullmatch(text) is None:
        raise ValueError(PHONE_ERROR)
    return text
