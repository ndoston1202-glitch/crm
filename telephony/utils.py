import re


def normalize_phone(value):
    """Telefonni solishtirish uchun oxirgi 9 raqamga keltiradi: '+998 (90) 123-45-67' -> '901234567'."""
    digits = re.sub(r"\D", "", value or "")
    return digits[-9:] if len(digits) >= 9 else digits
