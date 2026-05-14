import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


MONEY_QUANT = Decimal("0.01")


def only_digits(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\D", "", str(value))


def is_valid_cpf(cpf: str) -> bool:
    digits = only_digits(cpf)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False

    def calc_digit(base: str, start_weight: int) -> str:
        total = sum(int(n) * weight for n, weight in zip(base, range(start_weight, 1, -1)))
        remainder = (total * 10) % 11
        return "0" if remainder == 10 else str(remainder)

    return digits[9] == calc_digit(digits[:9], 10) and digits[10] == calc_digit(digits[:10], 11)


def normalize_cpf(cpf):
    digits = only_digits(cpf)
    if not digits:
        return None
    if len(digits) < 11:
        digits = digits.zfill(11)
    if len(digits) != 11:
        return None
    return digits


def format_cpf(cpf) -> str:
    digits = normalize_cpf(cpf)
    if not digits:
        return ""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_name(name):
    if name is None:
        return ""
    text = " ".join(str(name).strip().split()).upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def parse_money(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    text = text.replace("R$", "").replace("\xa0", " ").strip()
    text = re.sub(r"[^\d,.\-()]", "", text)
    negative = text.startswith("(") and text.endswith(")")
    text = text.replace("(", "").replace(")", "")
    if not text or text in {"-", ",", "."}:
        return None

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        parts = text.split(".")
        text = "".join(parts[:-1]) + "." + parts[-1]

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    if negative:
        amount = -amount
    return amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def decimal_to_str(value):
    if value is None:
        return ""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return str(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))
