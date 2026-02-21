import json
from pathlib import Path
from typing import Any

import wasmtime

from pymonalisa.exceptions import MonalisaModuleError


class Module:
    """MonaLisa module representation with WASM module"""

    def __init__(self, wasm_path: str | Path, metadata: dict[str, Any] = None):
        """
        Initialize Device with WASM module

        Args:
            wasm_path: Path to MonaLisa WASM file (.wat or .wasm)
            metadata: Optional module metadata
        """
        self.wasm_path = Path(wasm_path)
        self.metadata = metadata or {}
        self._engine = None
        self._module = None
        self._validate_and_load()

    def _validate_and_load(self):
        """Validate and load WASM module"""
        if not self.wasm_path.exists():
            raise MonalisaModuleError(f"WASM file not found: {self.wasm_path}")

        try:
            self._engine = wasmtime.Engine()

            if self.wasm_path.suffix.lower() == ".wat":
                self._module = wasmtime.Module.from_file(
                    self._engine, str(self.wasm_path)
                )
            else:
                wasm_bytes = self.wasm_path.read_bytes()
                self._module = wasmtime.Module(self._engine, wasm_bytes)

        except Exception as e:
            raise MonalisaModuleError(f"Failed to load WASM module: {e}")

    @classmethod
    def load(cls, module_path: str | Path) -> "Module":
        """
        Load module from .json file

        Args:
            module_path: Path to .json file containing module info

        Returns:
            Module: Loaded module instance
        """
        module_path = Path(module_path)

        if not module_path.exists():
            raise MonalisaModuleError(f"Device file not found: {module_path}")

        try:
            with open(module_path) as f:
                device_data = json.load(f)

            wasm_path = device_data.get("wasm_path")
            if not wasm_path:
                raise MonalisaModuleError("Device file missing wasm_path")

            if not Path(wasm_path).is_absolute():
                wasm_path = module_path.parent / wasm_path

            metadata = device_data.get("metadata", {})
            return cls(wasm_path, metadata)

        except json.JSONDecodeError:
            raise MonalisaModuleError(f"Invalid module file format: {module_path}")
        except Exception as e:
            raise MonalisaModuleError(f"Failed to load module: {e}")

    def save(self, module_path: str | Path):
        """
        Save module to .json file

        Args:
            module_path: Path where to save the device file
        """
        module_path = Path(module_path)

        device_data = {"wasm_path": str(self.wasm_path), "metadata": self.metadata}

        try:
            with open(module_path, "w") as f:
                json.dump(device_data, f, indent=2)
        except Exception as e:
            raise MonalisaModuleError(f"Failed to save device: {e}")

    def create_store(self) -> wasmtime.Store:
        """Create fresh store instance for WASM execution"""
        return wasmtime.Store(self._engine)

    @property
    def engine(self) -> wasmtime.Engine:
        """Get WASM engine"""
        return self._engine

    @property
    def module(self) -> wasmtime.Module:
        """Get WASM module"""
        return self._module

    def __repr__(self) -> str:
        return f"Device(wasm_path='{self.wasm_path}')"
