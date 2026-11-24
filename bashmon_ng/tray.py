"""System tray icon. Silent by design: no toasts or other notifications,
which would pull a fullscreen DirectX game out of focus. State is shown by
the icon colour (blue = watching, red = error) and the tooltip."""
import logging
import os
import sys

import pystray
from PIL import Image

from .config import APP_NAME

log = logging.getLogger(__name__)

def _icon_file(name: str) -> str:
    base = sys._MEIPASS if getattr(sys, 'frozen', False) else \
        os.path.dirname(os.path.abspath(__file__))
    sub = ('bashmon_ng', 'icons') if getattr(sys, 'frozen', False) else (
        'icons',)
    return os.path.join(base, *sub, name)

def _open(get_path):
    """Open a file or folder from the menu. Errors are logged, not raised:
    an error in a menu action would stop the tray.

    :param get_path: returns the path (it reads INIs, which can fail)."""
    path = None
    try:
        path = get_path()
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            log.warning('Cannot open %s: it does not exist', path)
    except Exception:
        log.exception('Cannot open %s', path)

class Tray:
    def __init__(self, *, log_file, get_saves_dir, get_signal_dir,
                 on_exit):
        self._images = {
            'watching': Image.open(_icon_file('bash_icons_blue.ico')),
            'error': Image.open(_icon_file('bash_icons_red.ico')),
        }
        self._status_text = 'Starting…'
        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: self._status_text, None,
                             enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Open Log', lambda: _open(lambda: log_file),
                             default=True),
            pystray.MenuItem('Open Save Folder',
                             lambda: _open(get_saves_dir)),
            pystray.MenuItem('Open BashMon Folder',
                             lambda: _open(get_signal_dir)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit', lambda: on_exit()),
        )
        self.icon = pystray.Icon('WryeBashMonNG',
                                 icon=self._images['watching'],
                                 title=APP_NAME, menu=menu)

    def set_status(self, state: str, text: str):
        """Update icon colour, tooltip and the menu's status line."""
        prefix = 'Error' if state == 'error' else 'Watching'
        self._status_text = f'{prefix}: {text}'
        self.icon.icon = self._images.get(state, self._images['watching'])
        # Windows limits tooltips to 127 characters
        self.icon.title = f'{APP_NAME} - {self._status_text}'[:127]
        self.icon.update_menu()

    def run(self, setup):
        """Blocks until stop(); setup(icon) runs in a helper thread."""
        self.icon.run(setup=setup)

    def stop(self):
        self.icon.stop()
