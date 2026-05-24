from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass

from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad

V3_UNWRAP_MASK_32 = bytes.fromhex(
    "65ab3479a2d83c6f60b891c024194e24a0d2a25c1f7a4926a3d4ac0c675255d8"
)


@dataclass
class TicketData:
    version: int
    uid: bytes
    kek_data: bytes
    ckey_cipher_data: bytes


def read_unit(buf: bytes, pos: int) -> tuple[int, int, bytes, int]:
    if pos + 4 > len(buf):
        raise ValueError("truncated outer TLV header")
    typ = buf[pos]
    data_len = (buf[pos + 2] << 8) | buf[pos + 3]
    end = pos + 4 + data_len
    if end > len(buf):
        raise ValueError("truncated outer TLV payload")
    return typ, buf[pos + 1], buf[pos + 4 : end], end


def iter_type3_chunks(data: bytes):
    pos = 0
    while pos + 4 <= len(data):
        flag = data[pos]
        seg_len = (data[pos + 1] << 8) | data[pos + 2]
        mark_pos = pos + 3 + seg_len
        if mark_pos >= len(data):
            break
        seg = data[pos + 3 : pos + 3 + seg_len]
        kind = data[mark_pos]
        yield flag, seg, kind
        pos += 4 + seg_len


def parse_ticket(license_b64: str) -> TicketData:
    raw = base64.b64decode(license_b64)

    version = None
    uid = b""
    kek_data = b""
    ckey_cipher_data = b""

    pos = 0
    while pos + 4 <= len(raw):
        typ, _idx, data, pos_next = read_unit(raw, pos)

        if typ == 0:
            version = data[0]
        elif typ == 1:
            uid = data[1:]
        elif typ == 2 and data and data[0] == 1:
            uid = data[1:]
        elif typ == 3:
            for flag, seg, kind in iter_type3_chunks(data):
                if kind == 1 and flag == 1:
                    ckey_cipher_data = seg
                elif kind == 2:
                    kek_data = seg
        elif typ == 255:
            cert_len = data[1]
            hash_len = (data[cert_len + 2] << 8) | data[cert_len + 3]
            hash_in_ticket = data[cert_len + 4 : cert_len + 4 + hash_len]
            calc = hashlib.sha256(raw[:pos]).digest()
            if data[0] == 1 and calc != hash_in_ticket:
                raise ValueError("ticket sha256 verification failed")

        pos = pos_next

    if version is None:
        raise ValueError("missing version")
    if not kek_data:
        raise ValueError("missing KekData")
    if not ckey_cipher_data:
        raise ValueError("missing CkeyCipherData")

    return TicketData(
        version=version,
        uid=uid,
        kek_data=kek_data,
        ckey_cipher_data=ckey_cipher_data,
    )


def aes_dec_v3(ciphertext: bytes, key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError(f"expected 32-byte KekData, got {len(key)}")
    iv = b"0" * 16
    plain = AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)
    return unpad(plain, 16)


def unwrap_v3_ckey(blob: bytes) -> bytes:
    if len(blob) < 32:
        raise ValueError(f"expected >=32-byte v3 blob, got {len(blob)}")
    return bytes(a ^ b for a, b in zip(blob[:32], V3_UNWRAP_MASK_32))


def decrypt_ticket_key(license_b64: str) -> tuple[TicketData, bytes, bytes]:
    ticket = parse_ticket(license_b64)
    blob = aes_dec_v3(ticket.ckey_cipher_data, ticket.kek_data)
    ckey32 = unwrap_v3_ckey(blob)
    return ticket, blob, ckey32


def extract_dcid(license_b64: str) -> str:
    raw = base64.b64decode(license_b64)
    text = raw.decode("ascii", errors="ignore")
    match = re.search(r"DCID-[A-Z0-9-]+", text)
    return match.group(0) if match else ""
