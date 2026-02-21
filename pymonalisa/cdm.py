import base64
import re
import uuid

import wasmtime

from pymonalisa.exceptions import MonalisaLicenseError, MonalisaSessionError
from pymonalisa.license import License
from pymonalisa.module import Module
from pymonalisa.types import Key, KeyType
from pymonalisa.utils import get_env_strings


class CDM:
    """MonaLisa Content Decryption Module"""

    def __init__(self, module: Module):
        """
        Initialize CDM with module

        Args:
            module: MonaLisa module instance
        """
        self.module = module
        self._sessions: dict[str, "Session"] = {}

    @classmethod
    def from_module(cls, module: Module) -> "CDM":
        """
        Create CDM from module

        Args:
            module: MonaLisa module instance

        Returns:
            Cdm: CDM instance
        """
        return cls(module)

    def open(self) -> str:
        """
        Open new CDM session

        Returns:
            str: Session ID
        """
        session_id = str(uuid.uuid4())
        store = self.module.create_store()
        session = Session(session_id, self.module, store)
        session.initialize()
        self._sessions[session_id] = session
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

    # Memory configuration constants
    DYNAMIC_BASE = 6065008
    DYNAMICTOP_PTR = 821968
    LICENSE_KEY_OFFSET = 0x5C8C0C
    LICENSE_KEY_LENGTH = 16

    def __init__(self, session_id: str, module: Module, store: wasmtime.Store):
        """Initialize session"""
        self.session_id = session_id
        self.module = module
        self.store = store
        self.instance = None
        self.memory = None
        self.exports = {}
        self._ctx = None
        self._keys: list[Key] = []
        self._initialized = False

    def initialize(self):
        """Initialize WASM instance and context"""
        if self._initialized:
            return

        try:
            # Create memory
            memory_type = wasmtime.MemoryType(wasmtime.Limits(256, 256))
            self.memory = wasmtime.Memory(self.store, memory_type)

            # Set up dynamic memory pointer
            self._write_i32(self.DYNAMICTOP_PTR, self.DYNAMIC_BASE)

            # Build imports
            imports = self._build_imports()

            # Initialize WASM instance
            self.instance = wasmtime.Instance(self.store, self.module.module, imports)

            # Get exports
            self.exports = {
                "___wasm_call_ctors": self.instance.exports(self.store)["s"],
                "_monalisa_context_alloc": self.instance.exports(self.store)["D"],
                "monalisa_set_license": self.instance.exports(self.store)["F"],
                "_monalisa_set_canvas_id": self.instance.exports(self.store)["t"],
                "_monalisa_version_get": self.instance.exports(self.store)["A"],
                "monalisa_get_line_number": self.instance.exports(self.store)["v"],
                "stackAlloc": self.instance.exports(self.store)["N"],
                "stackSave": self.instance.exports(self.store)["L"],
                "stackRestore": self.instance.exports(self.store)["M"],
            }

            # Initialize MonaLisa context
            self.exports["___wasm_call_ctors"](self.store)
            self._ctx = self.exports["_monalisa_context_alloc"](self.store)
            self._initialized = True

        except Exception as e:
            raise MonalisaSessionError(f"Failed to initialize session: {e}")

    def parse_license(self, license_: License):
        """Parse license and extract keys directly"""
        try:
            # Use the base64 string format for WASM module
            license_str = license_.b64

            # Set license in WASM module
            ret = self._ccall(
                "monalisa_set_license", int, self._ctx, license_str, len(license_str), "0"
            )

            if ret != 0:
                raise MonalisaLicenseError(f"License validation failed with code: {ret}")

            # Extract license key from memory
            key_hex = self._extract_license_key()
            key_bytes = bytes.fromhex(key_hex)

            # Extract CID from license for KID generation
            m = re.search(
                r"DCID-[A-Z0-9]+-[A-Z0-9]+-\d{8}-\d{6}-[A-Z0-9]+-\d{10}-[A-Z0-9]+",
                base64.b64decode(license_str).decode("ascii", errors="ignore"),
            )
            if m:
                kid = uuid.uuid5(uuid.NAMESPACE_DNS, m.group())
            else:
                kid = uuid.UUID(int=0)  # default if fails

            # Create key object (assuming CONTENT key for now)
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
        self._ctx = None
        self.instance = None
        self.memory = None
        self._initialized = False

    def _extract_license_key(self) -> str:
        """Extract license key from memory"""
        data = self.memory.data_ptr(self.store)
        data_len = self.memory.data_len(self.store)

        if self.LICENSE_KEY_OFFSET + self.LICENSE_KEY_LENGTH > data_len:
            raise MonalisaLicenseError("License key offset beyond memory bounds")

        # Read key bytes from memory
        import ctypes

        mem_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_ubyte * data_len))
        key_bytes = bytes(
            mem_ptr.contents[
                self.LICENSE_KEY_OFFSET : self.LICENSE_KEY_OFFSET
                + self.LICENSE_KEY_LENGTH
            ]
        )
        return key_bytes.hex()

    def _ccall(self, func_name: str, return_type: type, *args):
        """Call WASM function with argument conversion"""
        stack = 0
        converted_args = []

        for arg in args:
            if isinstance(arg, str):
                if stack == 0:
                    stack = self.exports["stackSave"](self.store)
                max_length = (len(arg) << 2) + 1
                ptr = self.exports["stackAlloc"](self.store, max_length)
                self._string_to_utf8(arg, ptr, max_length)
                converted_args.append(ptr)
            elif isinstance(arg, list):
                if stack == 0:
                    stack = self.exports["stackSave"](self.store)
                ptr = self.exports["stackAlloc"](self.store, len(arg))
                self._write_array_to_memory(arg, ptr)
                converted_args.append(ptr)
            else:
                converted_args.append(arg)

        result = self.exports[func_name](self.store, *converted_args)

        if stack != 0:
            self.exports["stackRestore"](self.store, stack)

        if isinstance(return_type, str):
            return self._utf8_to_string(result)
        elif isinstance(return_type, bool):
            return bool(result)
        return result

    def _write_i32(self, addr: int, value: int):
        """Write 32-bit integer to memory"""
        data = self.memory.data_ptr(self.store)
        import ctypes

        mem_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_int32))
        mem_ptr[addr >> 2] = value

    def _read_i32(self, addr: int) -> int:
        """Read 32-bit integer from memory"""
        data = self.memory.data_ptr(self.store)
        import ctypes

        mem_ptr = ctypes.cast(data, ctypes.POINTER(ctypes.c_int32))
        return mem_ptr[addr >> 2]

    def _string_to_utf8(self, data: str, ptr: int, max_length: int) -> int:
        """Convert string to UTF-8 and write to memory"""
        encoded = data.encode("utf-8")
        write_length = min(len(encoded), max_length - 1)

        mem_data = self.memory.data_ptr(self.store)
        import ctypes

        mem_ptr = ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte))

        for i in range(write_length):
            mem_ptr[ptr + i] = encoded[i]
        mem_ptr[ptr + write_length] = 0  # null terminator

        return write_length

    def _write_array_to_memory(self, array: list, ptr: int):
        """Write array to memory"""
        mem_data = self.memory.data_ptr(self.store)
        import ctypes

        mem_ptr = ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte))

        for i, val in enumerate(array):
            mem_ptr[ptr + i] = val
        return ptr

    def _utf8_to_string(self, ptr: int) -> str:
        """Convert UTF-8 from memory to string"""
        if ptr == 0:
            return ""

        mem_data = self.memory.data_ptr(self.store)
        data_len = self.memory.data_len(self.store)

        if ptr >= data_len:
            return ""

        import ctypes

        mem_ptr = ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte))

        # Find null terminator
        length = 0
        while ptr + length < data_len and mem_ptr[ptr + length] != 0:
            length += 1

        # Extract bytes and decode
        data = bytes(mem_ptr[ptr : ptr + length])
        return data.decode("utf-8")

    def _write_ascii_to_memory(self, string: str, buffer: int, dont_add_null: int = 0):
        """Write ASCII string to memory"""
        mem_data = self.memory.data_ptr(self.store)
        import ctypes

        mem_ptr = ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte))

        encoded = string.encode("utf-8")
        for i, byte_val in enumerate(encoded):
            mem_ptr[buffer + i] = byte_val

        if dont_add_null == 0:
            mem_ptr[buffer + len(encoded)] = 0

    def _build_imports(self):
        """Build import object with required external functions"""

        # System call stubs
        def sys_fcntl64(*_, **__) -> int:
            return 0

        def fd_write(*_, **__) -> int:
            return 0

        def fd_close(*_, **__) -> int:
            return 0

        def sys_ioctl(*_, **__) -> int:
            return 0

        def sys_open(*_, **__) -> int:
            return 0

        def sys_rmdir(*_, **__) -> int:
            return 0

        def sys_unlink(*_, **__) -> int:
            return 0

        def clock() -> int:
            return 0

        def time(*_, **__) -> int:
            return 0

        def emscripten_run_script(*_, **__):
            pass

        def fd_seek(*_, **__) -> int:
            return 0

        def emscripten_resize_heap(*_, **__) -> int:
            return 0

        def fd_read(*_, **__) -> int:
            return 0

        def emscripten_run_script_string(*_, **__) -> int:
            return 0

        def emscripten_run_script_int(*_, **__) -> int:
            return 1

        def emscripten_memcpy_big(dest: int, src: int, num: int) -> int:
            mem_data = self.memory.data_ptr(self.store)
            data_len = self.memory.data_len(self.store)

            if num is None:
                num = data_len - 1

            import ctypes

            mem_ptr = ctypes.cast(mem_data, ctypes.POINTER(ctypes.c_ubyte))

            # Copy memory
            for i in range(num):
                if dest + i < data_len and src + i < data_len:
                    mem_ptr[dest + i] = mem_ptr[src + i]

            return dest

        def environ_get(environ_ptr: int, environ_buf: int) -> int:
            buf_size = 0
            strings = get_env_strings()

            for index, string in enumerate(strings):
                ptr = environ_buf + buf_size
                self._write_i32(environ_ptr + index * 4, ptr)
                self._write_ascii_to_memory(string, ptr)
                buf_size += len(string) + 1
            return 0

        def environ_sizes_get(penviron_count: int, penviron_buf_size: int) -> int:
            strings = get_env_strings()
            self._write_i32(penviron_count, len(strings))
            buf_size = sum(len(string) + 1 for string in strings)
            self._write_i32(penviron_buf_size, buf_size)
            return 0

        # Create function types and instances
        imports = [
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                sys_fcntl64,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                fd_write,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                fd_close,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                sys_ioctl,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                sys_open,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                sys_rmdir,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                sys_unlink,
            ),
            wasmtime.Func(
                self.store, wasmtime.FuncType([], [wasmtime.ValType.i32()]), clock
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                time,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], []),
                emscripten_run_script,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                fd_seek,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                emscripten_memcpy_big,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                emscripten_resize_heap,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
                    [wasmtime.ValType.i32()],
                ),
                environ_get,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
                    [wasmtime.ValType.i32()],
                ),
                environ_sizes_get,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType(
                    [
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                        wasmtime.ValType.i32(),
                    ],
                    [wasmtime.ValType.i32()],
                ),
                fd_read,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                emscripten_run_script_string,
            ),
            wasmtime.Func(
                self.store,
                wasmtime.FuncType([wasmtime.ValType.i32()], [wasmtime.ValType.i32()]),
                emscripten_run_script_int,
            ),
            self.memory,
        ]

        return imports
