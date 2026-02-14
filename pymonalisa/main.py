import logging
import click
import cloup
from loggpy import logging, Logger
from datetime import datetime
from pathlib import Path
from typing import Optional

from pymonalisa import __version__
from pymonalisa.cdm import Cdm
from pymonalisa.module import Module
from pymonalisa.license import License
from pymonalisa.types import KeyType
from pymonalisa.exceptions import (
    MonalisaError,
    MonalisaLicenseError,
    MonalisaModuleError,
    MonalisaSessionError
)


@cloup.group(
    name='pymonalisa',
    invoke_without_command=True,
    context_settings=cloup.Context.settings(
            help_option_names=["-h", "--help"],
    max_content_width=116,
    align_option_groups=False,
    align_sections=True,
    formatter_settings=cloup.HelpFormatter.settings(
        indent_increment=3,
        col1_max_width=50,
        col_spacing=3,
        theme=cloup.HelpTheme(
            invoked_command=cloup.Style(fg="cyan"),
            heading=cloup.Style(fg="bright_white", bold=True),
            col1=cloup.Style(fg="bright_green"),
        ),
    ),
),
    help=click.style(
        text="A Python library to decrypt IQIYI DRM License Ticket", 
        fg='green', 
        dim=True,
        overline=True,
        strikethrough=True,
        blink=True,
        bold=True,
    ),
    epilog=click.style(
        text="""
            \b
            Made for fun only by ReiDoBrega.

            \b
             Thanks to duck
            """,
        fg='blue', 
        bold=True,
        italic=True,
    )
)


@cloup.option("-v", "--version", is_flag=True, default=False, help="Print version information.")
def main(version: bool) -> None:
    """Python MonaLisa CDM implementation"""

    Logger.mount(level=logging.INFO)
    log = Logger('pymonalisa')

    current_year = datetime.now().year
    copyright_years = f"2025-{current_year}" if current_year > 2025 else "2025"

    log.info("pymonalisa version %s Copyright (c) %s pymonalisa Team", __version__, copyright_years)
    log.info("MonaLisa Content Decryption Module for Python")
    log.info("Run 'pymonalisa --help' for help")
    
    if version:
        return


@main.command(name="license")
@cloup.argument("license_data", type=str)
@cloup.argument("device_path", type=cloup.Path(exists=True, path_type=Path))
@cloup.option_group(
    "Key filtering options",
    cloup.option(
        "-t", "--key-type", 
        type=cloup.Choice(["CONTENT", "FULL"], case_sensitive=False),
        default="CONTENT", 
        help="Filter keys by type"
    ),
)
def license_(
    license_data: str,
    device_path: Path,
    key_type: Optional[str],
) -> None:
    """
    Process a MonaLisa encoded license and extract decryption keys.
    
    LICENSE_DATA: Base64 encoded MonaLisa license string
    DEVICE_PATH: Path to MonaLisa device file (.mld)
    
    Example:
        pymonalisa license "AIUACgMAAAAAAAAAAAQChgACATADhwAnAgAg3UBbUdVCWXAjkgoUgmICmHvomvZai0jGglWe+oaQC+M..." device.mld
    """
    log = logging.getLogger("license")

    # Validate inputs
    if not device_path.is_file():
        log.error(f"Module file not found: {device_path}")
        return

    try:
        log.info(f"Loading module: {device_path}")
        module = Module.load(device_path)
        log.info(f"Loaded module successfully")
        
        log.info("Initializing CDM...")
        cdm = Cdm.from_module(module)
        log.info("CDM initialized successfully")

        log.info("Opening CDM session...")
        session_id = cdm.open()
        log.info(f"Session opened: {session_id}")

        log.info("Processing license data...")
        license_obj = License(license_data)

        log.info("Parsing license and extracting keys...")
        cdm.parse_license(session_id, license_obj)
        log.info("License parsed successfully")

        keys = cdm.get_keys(session_id, KeyType.CONTENT) # CONTENT only for now
        
        if not keys:
            log.warning("No keys found in license")
            cdm.close(session_id)
            return

        log.info(f"Found {len(keys)} keys:")
        for key in keys: # One only always, dont sure about others verions up LicenseVersion 3
            # NOTE: we can handle here but the key_type always will be CONTENT, to decrypt the IQIYI bbts we need the KEY only, not the KID
            if key_type == "CONTENT":
                log.info(f"{key.key.hex()}")
            else:
                log.info(f"{key.kid.hex()}:{key.key.hex()}")

        cdm.close(session_id)
        log.info("Session closed successfully")

    except MonalisaModuleError as e:
        log.error(f"Module error: {e}")
    except MonalisaLicenseError as e:
        log.error(f"License error: {e}")
    except MonalisaSessionError as e:
        log.error(f"Session error: {e}")
    except MonalisaError as e:
        log.error(f"MonaLisa error: {e}")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            log.debug(traceback.format_exc())


if __name__ == "__main__":
    main()
