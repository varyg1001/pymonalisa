from enum import Enum
from dataclasses import dataclass
from typing import Optional


class KeyType(Enum):
    """Key types for MonaLisa keys"""
    CONTENT = "CONTENT"
    SIGNING = "SIGNING"
    OTT = "OTT"
    OPERATOR_SESSION = "OPERATOR_SESSION"


@dataclass
class Key:
    """Represents a MonaLisa key"""
    kid: bytes
    key: bytes
    type: KeyType
    permissions: Optional[list] = None
    
    def __str__(self) -> str:
        return f"[{self.type.value}] {self.kid.hex()}:{self.key.hex()}"