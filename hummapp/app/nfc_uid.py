"""NFC-tagin UID:n yhtenäinen normalisointi ja validointi (ennen kolme eri toteutusta)."""
import re

_UID_RE = re.compile(r"^[0-9A-F]{8,20}$")
_SEPARATORS = re.compile(r"[\s:\-]")


def normalize_nfc_uid(raw: str) -> str:
    """
    Poistaa välilyönnit, kaksoispisteet ja väliviivat ja muuttaa isoiksi kirjaimiksi.
    Hyväksyy 4–10 tavun UID:t heksamuodossa (NTAG21x = 7 tavua, ISO 15693 = 8 tavua).
    """
    cleaned = _SEPARATORS.sub("", raw or "").upper()
    if not _UID_RE.match(cleaned):
        raise ValueError("NFC UID:n tulee olla 8–20 heksamerkkiä (esim. 04A31B92C56F80).")
    return cleaned
