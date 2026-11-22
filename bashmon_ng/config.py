"""BashMon NG settings: where Oblivion is, and where we keep our files."""
import json
import os

APP_NAME = 'Wrye BashMon NG'

def data_dir() -> str:
    """%LOCALAPPDATA%\\Wrye BashMon NG - log and config live here."""
    base = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path

def _config_path() -> str:
    return os.path.join(data_dir(), 'config.json')

def load() -> dict:
    try:
        with open(_config_path(), encoding='utf-8') as ins:
            return json.load(ins)
    except (OSError, ValueError):
        return {}

def save(cfg: dict):
    tmp = _config_path() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as out:
        json.dump(cfg, out, indent=2)
    os.replace(tmp, _config_path())

def get_game_dir() -> str | None:
    """Return the remembered Oblivion folder, if it still has Oblivion.exe."""
    game_dir = load().get('game_dir')
    if game_dir and os.path.isfile(os.path.join(game_dir, 'Oblivion.exe')):
        return game_dir
    return None

def set_game_exe(exe_path: str):
    cfg = load()
    cfg['game_dir'] = os.path.dirname(os.path.abspath(exe_path))
    save(cfg)
