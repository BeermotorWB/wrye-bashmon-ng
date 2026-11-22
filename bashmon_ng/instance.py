"""Only one BashMon may run - two would race for Morph's request files."""
import ctypes

_MUTEX_NAME = 'WryeBashMonNG_SingleInstance'
_ERROR_ALREADY_EXISTS = 183
_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_mutex = None

def acquire() -> bool:
    """Return True if we are the only running instance."""
    global _mutex
    handle = _kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return True # cannot tell - better to run than to refuse
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        _kernel32.CloseHandle(handle)
        return False
    _mutex = handle
    return True

def release():
    global _mutex
    if _mutex:
        _kernel32.CloseHandle(_mutex)
        _mutex = None
