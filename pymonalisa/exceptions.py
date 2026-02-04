class MonalisaError(Exception):
    """Base exception for all MonaLisa operations"""
    pass


class MonalisaLicenseError(MonalisaError):
    """Exception raised for license-related errors"""
    pass


class MonalisaModuleError(MonalisaError):
    """Exception raised for module/WASM module errors"""
    pass


class MonalisaSessionError(MonalisaError):
    """Exception raised for session management errors"""
    pass