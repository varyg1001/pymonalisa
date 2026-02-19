def get_env_strings() -> list[str]:
    return [
        "USER=web_user",
        "LOGNAME=web_user",
        "PATH=/",
        "PWD=/",
        "HOME=/home/web_user",
        "LANG=zh_CN.UTF-8",
        "_=./this.program",
    ]


def bytes_to_hex(data: bytes) -> str:
    """Convert bytes to uppercase hex string"""
    return data.hex().upper()


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string to bytes"""
    return bytes.fromhex(hex_str)
