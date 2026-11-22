"""Find the folders Wrye Morph and BashMon NG share.

Mirrors Wrye Bash's rules (initialization.init_dirs): the Oblivion.ini in the
game folder decides, through bUseMyGamesDirectory, whether the INI and saves
are under My Games or in the game folder. INIs are only ever read here.
"""
import configparser
import ctypes
import os
from ctypes import wintypes

def _documents_dir() -> str:
    """The user's Documents folder (SHGetKnownFolderPath)."""
    class _GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]
    # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
    guid = _GUID(0xFDD39AD0, 0x238F, 0x46AF,
                 (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85,
                                      0x48, 0x03, 0x69, 0xC7))
    out = ctypes.c_wchar_p()
    # Own handles - Wrye Bash sets argtypes on the shared ctypes.windll ones
    shell32 = ctypes.WinDLL('shell32')
    if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None,
                                    ctypes.byref(out)):
        return os.path.join(os.path.expanduser('~'), 'Documents')
    try:
        return out.value
    finally:
        ctypes.WinDLL('ole32').CoTaskMemFree(out)

def _read_ini(path: str) -> configparser.ConfigParser | None:
    if not os.path.isfile(path):
        return None
    ini = configparser.ConfigParser(allow_no_value=True, strict=False,
                                    interpolation=None)
    ini.optionxform = str.lower
    for enc in ('utf-8-sig', 'cp1252'):
        try:
            ini.read(path, encoding=enc)
            return ini
        except UnicodeDecodeError:
            continue
        except configparser.Error:
            return None
    return None

def _ini_value(ini, section: str, key: str) -> str | None:
    if ini is None:
        return None
    try:
        return ini.get(section, key.lower())
    except (configparser.Error, KeyError):
        return None

def save_base(game_dir: str) -> str:
    """Documents\\My Games\\Oblivion, or the game folder when the game
    folder's Oblivion.ini sets bUseMyGamesDirectory=0."""
    game_ini = _read_ini(os.path.join(game_dir, 'Oblivion.ini'))
    if _ini_value(game_ini, 'General', 'bUseMyGamesDirectory') == '0':
        return game_dir
    return os.path.join(_documents_dir(), 'My Games', 'Oblivion')

def saves_dir(game_dir: str) -> str:
    """The folder the game saves to: saveBase + SLocalSavePath."""
    base = save_base(game_dir)
    main_ini = _read_ini(os.path.join(base, 'Oblivion.ini'))
    local = _ini_value(main_ini, 'General', 'SLocalSavePath') or 'Saves\\'
    return os.path.normpath(os.path.join(base, local.strip()))

def signal_dir(game_dir: str) -> str:
    """Pluggy's user files folder that Wrye Morph uses to talk to us."""
    return os.path.join(save_base(game_dir), 'Pluggy', 'User Files',
                        'BashMon')
