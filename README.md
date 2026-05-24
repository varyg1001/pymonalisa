# pymonalisa
A Python library to decrypt IQIYI DRM License Ticket using a native Python implementation.

## Installation
```shell
pip install pymonalisa
```

Run `pymonalisa --help` to view available CLI functions.

## License Processing
Process a MonaLisa encoded license and extract decryption keys:
```shell
pymonalisa license "AAAADgMwAADECisAAAdoS7HZAQEASDVEQ0lELVYzLVAxLTIwMjUwNTE5LTE0NDM1Mi1NRDc0N0RBNS0xNzQ0NjQ0OTk3LUExMTJERwEQcMHbn2aue/wLGYFpS2aNngMCADhAACCzbv21P1LuugXC34EhhYOfBQm1K7vNBcxClOM9nTS50AIQxPPew5UYQhKhOg3UrJqXLQQBAwMDADkBADCvjimPScsXNIyb9HxbzkHRB7Bhv3J8Pvpgm54TFhIKSwH32SedaLf7dJ6PRExsjyoBAQECASADBAA4QAAgIreHYYp2nI86fJDaAxR6CJyvM1h+OKXATIn9aj43O2ADEIDB259mrnv8CxmBaUtmjZ4EAQMEBQATARBwwdufZq57/AsZgWlLZo2eAP8GADQBEIDB259mrnv8CxmBaUtmjZ4AIM11WGlDSqV01Aw8PkaTUEgYPVduGGQpxMTnWbNx7qpP"
```

### Options
- `-t, --key-type`: Filter keys by type (CONTENT or FULL). Default: CONTENT
- `-v, --version`: Print version information

## Usage
An example code snippet:

```python
from pymonalisa.cdm import CDM
from pymonalisa.license import License
from pymonalisa.types import KeyType

# Initialize CDM
cdm = CDM()

# Open a new session
session_id = cdm.open()

# Create license object from base64 encoded license data
license_data = "AAAADgMwAADECisAAAdoS7HZAQEASDVEQ0lELVYzLVAxLTIwMjUwNTE5LTE0NDM1Mi1NRDc0N0RBNS0xNzQ0NjQ0OTk3LUExMTJERwEQcMHbn2aue/wLGYFpS2aNngMCADhAACCzbv21P1LuugXC34EhhYOfBQm1K7vNBcxClOM9nTS50AIQxPPew5UYQhKhOg3UrJqXLQQBAwMDADkBADCvjimPScsXNIyb9HxbzkHRB7Bhv3J8Pvpgm54TFhIKSwH32SedaLf7dJ6PRExsjyoBAQECASADBAA4QAAgIreHYYp2nI86fJDaAxR6CJyvM1h+OKXATIn9aj43O2ADEIDB259mrnv8CxmBaUtmjZ4EAQMEBQATARBwwdufZq57/AsZgWlLZo2eAP8GADQBEIDB259mrnv8CxmBaUtmjZ4AIM11WGlDSqV01Aw8PkaTUEgYPVduGGQpxMTnWbNx7qpP"
license_obj = License(license_data)

# Parse the license
cdm.parse_license(session_id, license_obj)

# Get content keys
keys = cdm.get_keys(session_id, KeyType.CONTENT)

# Print extracted keys
for key in keys:
    print(f"{key.key.hex()}")  # Content key only
    # or for full key info:
    # print(f"{key.kid.hex()}:{key.key.hex()}")

# Close the session
cdm.close(session_id)
```

## Key Types
- `CONTENT`: Returns only the content decryption KEY
- `FULL`: Returns both Key ID and content key in KID:KEY format

## Notes
- This implementation is designed specifically for IQIYI DRM content
- The library focuses on content key extraction for decrypting IQIYI BBTS streams
- LicenseVersion 3 and below are supported
- No WASM module is required anymore

## Credits
Thanks to duck, ReiDoBrega, xhlove.
Thanks to [Ooo0xffooO/monalisa_v3](https://github.com/Ooo0xffooO/monalisa_v3) for the reference implementation used to remove the WASM dependency.

## License
This project is intended for educational and research purposes only.
