"""Only one BashMon may run - two would race for Morph's request files."""
import ctypes
import json
import os
import time

from . import config

_MUTEX_NAME = 'WryeBashMonNG_SingleInstance'
_ERROR_ALREADY_EXISTS = 183
_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_mutex = None

def _info_path() -> str:
    """Who holds the mutex, so a second start can log it."""
    return os.path.join(config.data_dir(), 'instance.json')

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

def write_info(version: str):
    """Record our PID and version for read_info. Call after acquire()."""
    try:
        with open(_info_path(), 'w', encoding='utf-8') as out:
            json.dump({'pid': os.getpid(), 'version': version,
                       'started': time.strftime('%Y-%m-%d %H:%M:%S')}, out)
    except OSError:
        pass

def read_info() -> str:
    """Describe the running instance, from what it wrote in write_info."""
    try:
        with open(_info_path(), encoding='utf-8') as ins:
            info = json.load(ins)
        return (f'PID {info["pid"]}, version {info["version"]}, started '
                f'{info["started"]}')
    except (OSError, ValueError, KeyError, TypeError):
        # Versions before 0.1.6 write no info
        return 'no details - probably a version before 0.1.6'

def release():
    global _mutex
    if _mutex:
        try:
            os.remove(_info_path())
        except OSError:
            pass
        _kernel32.CloseHandle(_mutex)
        _mutex = None
