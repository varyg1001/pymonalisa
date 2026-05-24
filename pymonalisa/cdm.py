import uuid

from pymonalisa.exceptions import MonalisaLicenseError, MonalisaSessionError
from pymonalisa.license import License
from pymonalisa.types import Key, KeyType
from pymonalisa.utils import decrypt_ticket_key, extract_dcid


class CDM:
    """MonaLisa Content Decryption Module"""

    def __init__(self):
        """Initialize CDM"""
        self._sessions: dict[str, "Session"] = {}

    def open(self) -> str:
        """
        Open new CDM session

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(session_id)
        return session_id

    def close(self, session_id: str):
        """
        Close CDM session

        Args:
            session_id: Session ID to close
        """
        if session_id in self._sessions:
            self._sessions[session_id].cleanup()
            del self._sessions[session_id]

    def get_license_challenge(self, session_id: str, ticket: str):
        return License(ticket)

    def parse_license(self, session_id: str, license: License | str | bytes):
        """
        Parse license and extract keys directly

        Args:
            session_id: Session ID
            license: License data (MonaLisa license string/bytes)
        """
        session = self._get_session(session_id)

        if not isinstance(license, License):
            license = License(license)

        session.parse_license(license)

    def get_keys(
        self, session_id: str, key_type: KeyType | None = KeyType.CONTENT
    ) -> list[Key]:
        """
        Get keys from session

        Args:
            session_id: Session ID
            key_type: Optional key type filter

        Returns:
            List[Key]: List of keys
        """
        session = self._get_session(session_id)
        return session.get_keys(key_type)

    def _get_session(self, session_id: str) -> "Session":
        """Get session by ID"""
        if session_id not in self._sessions:
            raise MonalisaSessionError(f"Session not found: {session_id}")
        return self._sessions[session_id]

    def __del__(self):
        """Cleanup all sessions on destruction"""
        for session_id in list(self._sessions.keys()):
            self.close(session_id)


class Session:
    """MonaLisa CDM session"""

    def __init__(self, session_id: str):
        """Initialize session"""
        self.session_id = session_id
        self._keys: list[Key] = []

    def parse_license(self, license_: License):
        """Parse license and extract keys directly"""
        try:
            license_str = license_.b64

            # Decrypt license key using Python logic
            _, _, ckey32 = decrypt_ticket_key(license_str)
            key_bytes = ckey32[:16]

            # Extract CID from license for KID generation
            dcid = extract_dcid(license_str)
            if dcid:
                kid = uuid.uuid5(uuid.NAMESPACE_DNS, dcid)
            else:
                kid = uuid.UUID(int=0)  # default if fails

            # Create key object
            key = Key(kid=kid.bytes, key=key_bytes, type=KeyType.CONTENT)

            self._keys.append(key)

        except Exception as e:
            raise MonalisaLicenseError(f"Failed to parse license: {e}")

    def get_keys(self, key_type: KeyType | None = None) -> list[Key]:
        """Get keys from session"""
        if key_type:
            return [key for key in self._keys if key.type == key_type]
        return self._keys.copy()

    def cleanup(self):
        """Cleanup session resources"""
        self._keys.clear()
