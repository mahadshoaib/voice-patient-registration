import re
from datetime import UTC, date, datetime

STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
    "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC "
    "AS GU MP PR VI UM".split()
)
DIGITS = dict(zip("zero one two three four five six seven eight nine".split(), "0123456789")) | {
    "oh": "0"
}


def name(value: str) -> str:
    value = value.strip().replace("’", "'")
    if not 1 <= len(value) <= 50 or not any(c.isalpha() for c in value):
        raise ValueError("Name must contain 1-50 letters, hyphens or apostrophes")
    if not all(c.isalpha() or c in "-'" for c in value):
        raise ValueError("Use letters, hyphens or apostrophes only")
    return value


def dob(value) -> date:
    if isinstance(value, datetime):
        raise ValueError("Use a date, not a timestamp")
    if isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        value = value.strip()
        try:
            if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
                parsed = datetime.strptime(value, "%m/%d/%Y").date()
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                parsed = date.fromisoformat(value)
            else:
                raise ValueError
        except ValueError:
            raise ValueError("Give a valid date as MM/DD/YYYY or YYYY-MM-DD") from None
    else:
        raise ValueError("Give a valid date as MM/DD/YYYY or YYYY-MM-DD")
    if parsed > datetime.now(UTC).date():
        raise ValueError("Date of birth cannot be in the future")
    return parsed


def phone(value: str) -> str:
    value = value.strip().lower()
    for word, digit in DIGITS.items():
        value = re.sub(rf"\b{word}\b", digit, value)
    value = re.sub(r"\b(dash|hyphen|space|open parenthesis|close parenthesis)\b", "", value)
    if re.search(r"[^0-9+().\s-]", value):
        raise ValueError("Give a U.S. 10-digit phone number; extensions are not supported")
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if not re.fullmatch(r"[2-9]\d{2}[2-9]\d{6}", digits):
        raise ValueError("Give a U.S. 10-digit phone number with a valid area and exchange code")
    return digits


def state(value: str) -> str:
    value = value.strip().upper()
    if value not in STATES:
        raise ValueError("Give a valid two-letter U.S. state or territory abbreviation")
    return value


def zip_code(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[0-9]{5}(-[0-9]{4})?", value):
        raise ValueError("Give a five-digit ZIP code or ZIP+4 (12345-6789)")
    return value
