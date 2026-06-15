import re

BLOCKED_PATTERNS = [
    "hack", "взлом", "бұзу", "steal", "украсть", "ұрлау", "password", "пароль",
    "sms code", "смс код", "otp", "2fa", "bypass", "обход", "keylogger", "malware",
    "sim registration owner", "кімнің атында", "иесі кім", "найди владельца", "пробей номер",
    "address of", "адрес", "мекенжай", "private database", "скрытая база", "слитая база",
    "bank records", "government database"
]

SENSITIVE_LABELS = [
    {"label": "Owner identity", "status": "REDACTED", "reason": "Private personal data. Requires verified lawful basis."},
    {"label": "Home address", "status": "BLOCKED", "reason": "Private location data is not provided."},
    {"label": "SIM registration", "status": "RESTRICTED", "reason": "Telecom registration records are not public-source data."},
    {"label": "Private databases", "status": "NOT ACCESSED", "reason": "BRIGHTLY does not use leaked or hidden databases."},
    {"label": "Banking records", "status": "NOT ACCESSED", "reason": "Financial records are restricted and not supported."},
    {"label": "Government records", "status": "NOT ACCESSED", "reason": "Restricted state databases are not accessed."},
]


def legal_filter(query: str) -> dict:
    q = (query or "").lower()
    hits = [p for p in BLOCKED_PATTERNS if p in q]
    if hits:
        return {
            "allowed": False,
            "status": "blocked",
            "matched": hits,
            "summary": "Request appears to involve private, restricted, or harmful data access.",
            "safe_alternative": "Use only public-source metadata, defensive checks, and consent-based self-check reports."
        }
    return {"allowed": True, "status": "approved", "matched": [], "summary": "Allowed for legal public-source analysis."}


def restricted_layer() -> list[dict]:
    return SENSITIVE_LABELS
