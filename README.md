# pymonalisa
A Python library to decrypt IQIYI DRM License Ticket using the MonaLisa Content Decryption Module.

## Installation
```shell
pip install pymonalisa
```

Run `pymonalisa --help` to view available CLI functions.

## Devices
To use pymonalisa, you need a MonaLisa device file (.mld). These device files load the WASM module required to process IQIYI DRM License Tickets correctly.

## License Processing
Process a MonaLisa encoded license and extract decryption keys:
```shell
pymonalisa license "AAAADgMwAADECisAAAdoS7HZAQEASDVEQ0lELVYzLVAxLTIwMjUwNTE5LTE0NDM1Mi1NRDc0N0RBNS0xNzQ0NjQ0OTk3LUExMTJERwEQcMHbn2aue/wLGYFpS2aNngMCADhAACCzbv21P1LuugXC34EhhYOfBQm1K7vNBcxClOM9nTS50AIQxPPew5UYQhKhOg3UrJqXLQQBAwMDADkBADCvjimPScsXNIyb9HxbzkHRB7Bhv3J8Pvpgm54TFhIKSwH32SedaLf7dJ6PRExsjyoBAQECASADBAA4QAAgIreHYYp2nI86fJDaAxR6CJyvM1h+OKXATIn9aj43O2ADEIDB259mrnv8CxmBaUtmjZ4EAQMEBQATARBwwdufZq57/AsZgWlLZo2eAP8GADQBEIDB259mrnv8CxmBaUtmjZ4AIM11WGlDSqV01Aw8PkaTUEgYPVduGGQpxMTnWbNx7qpP" device.mld
```

### Options
- `-t, --key-type`: Filter keys by type (CONTENT or FULL). Default: FULL
- `-v, --version`: Print version information

## Usage
An example code snippet:

```python
from pymonalisa.cdm import Cdm
from pymonalisa.module import Module
from pymonalisa.license import License
from pymonalisa.types import KeyType

# Load the MonaLisa device module
module = Module.load("path/to/device.mld")

# Initialize CDM from module
cdm = Cdm.from_module(module)

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
- The library currently focuses on content key extraction for decrypting IQIYI BBTS streams
- LicenseVersion 3 and below are supported
- Keys are typically returned in hexadecimal format

## TODO
- Add support for LicenseVersion up to 3

## Credits
Thanks to duck.

## License
This project is intended for educational and research purposes only.
