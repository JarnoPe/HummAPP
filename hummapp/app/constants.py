"""Tilat ja roolit yhdessä paikassa (aiemmin merkkijonoina ympäri koodia)."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # Jinja ja f-stringit näyttävät pelkän arvon
        return self.value


class EventStatus(StrEnum):
    RECEIVED = "RECEIVED"
    WAITING_FOR_RECORDING = "WAITING_FOR_RECORDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ClipStatus(StrEnum):
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


EDITOR_ROLES = [Role.ADMIN.value, Role.USER.value]
ADMIN_ROLES = [Role.ADMIN.value]


class NfcResult(StrEnum):
    OK = "OK"
    UNKNOWN_TAG = "UNKNOWN_TAG"
    DUPLICATE_SCAN_IGNORED = "DUPLICATE_SCAN_IGNORED"
