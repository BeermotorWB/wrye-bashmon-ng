"""The request loop: watches Wrye Morph's Pluggy files and answers them.

Protocol (from Wrye Morph's wrMorZS / wrMorShiftIdQS scripts):
- Morph renames Temp.txt to Ping.txt; we rename it to Pong.txt. Morph only
  checks that Ping.txt is gone, within 5 seconds.
- Morph renames Temp.txt to Request.txt; we run each line, then create
  Completed.txt or Failed.txt. Morph deletes Request, Completed and Failed
  itself, so a request is only run while neither result file exists.
"""
import logging
import os
import threading
import time
import traceback

from . import paths

log = logging.getLogger(__name__)

POLL_SECONDS = 0.25
SAVES_DIR_REFRESH_SECONDS = 2.0
_SIGNALS = ('Ping', 'Pong', 'Request', 'Completed', 'Failed', 'Temp')

class Status:
    WATCHING = 'watching'
    ERROR = 'error'

class Monitor(threading.Thread):
    """Background thread. on_status(state, text) is called on changes."""

    def __init__(self, game_dir: str, backup_dir: str, on_status):
        super().__init__(name='BashMonNG-Monitor', daemon=True)
        self._game_dir = game_dir
        self._backup_dir = backup_dir
        self._on_status = on_status
        self._stop_event = threading.Event()
        self.signal_dir = paths.signal_dir(game_dir)
        self.saves_dir = paths.saves_dir(game_dir)
        self._saves_checked = time.monotonic()
        self.last_result = 'No requests yet'

    def _sig(self, name: str) -> str:
        return os.path.join(self.signal_dir, f'{name}.txt')

    def stop(self):
        self._stop_event.set()

    def _status(self, state: str):
        try:
            self._on_status(state, self.last_result)
        except Exception:
            log.exception('Status callback failed')

    def _clear_signals(self):
        """Stale files from a crashed session must not run again (the
        original bashmon cleared them on start too)."""
        for name in _SIGNALS:
            try:
                os.remove(self._sig(name))
            except FileNotFoundError:
                pass

    def _refresh_saves_dir(self):
        """The save folder can change while we run (e.g. Wrye Bash save
        profiles set SLocalSavePath)."""
        now = time.monotonic()
        if now - self._saves_checked < SAVES_DIR_REFRESH_SECONDS:
            return
        self._saves_checked = now
        try:
            saves_dir = paths.saves_dir(self._game_dir)
        except OSError:
            return # INI busy - try again later
        if saves_dir != self.saves_dir:
            log.info('Save folder is now %s', saves_dir)
            self.saves_dir = saves_dir
            self._status(Status.WATCHING)

    def _touch(self, name: str):
        with open(self._sig(name), 'w', encoding='cp1252'):
            pass

    def _handle_ping(self):
        if os.path.isfile(ping := self._sig('Ping')):
            os.replace(ping, self._sig('Pong'))
            log.info('Ping from Wrye Morph')
            self.last_result = 'Wrye Morph connected'
            self._status(Status.WATCHING)

    def _handle_request(self):
        request = self._sig('Request')
        if not os.path.isfile(request):
            return
        if os.path.exists(self._sig('Completed')) or os.path.exists(
                self._sig('Failed')):
            return # Morph has not picked up the last result yet
        from . import saves # needs wb_boot.boot() first
        with open(request, encoding='cp1252', errors='replace') as ins:
            lines = [ln.strip() for ln in ins if ln.strip()]
        log.info('Request: %s', ' | '.join(lines))
        try:
            results = [saves.run_command(ln, self.saves_dir,
                                         self._backup_dir) for ln in lines]
        except Exception as e:
            log.error('Request failed:\n%s', traceback.format_exc())
            self.last_result = f'Failed: {e}'
            self._touch('Failed')
            self._status(Status.ERROR)
            return
        self.last_result = '; '.join(results) or 'Empty request'
        log.info('Completed: %s', self.last_result)
        self._touch('Completed')
        self._status(Status.WATCHING)

    def run(self):
        os.makedirs(self.signal_dir, exist_ok=True)
        self._clear_signals()
        log.info('Watching %s (saves: %s)', self.signal_dir, self.saves_dir)
        self._status(Status.WATCHING)
        while not self._stop_event.wait(POLL_SECONDS):
            try:
                self._refresh_saves_dir()
                self._handle_ping()
                self._handle_request()
            except Exception as e:
                # Keep watching - Morph shows its own error on timeout
                log.error('Monitor error:\n%s', traceback.format_exc())
                self.last_result = f'Error: {e}'
                self._status(Status.ERROR)
        log.info('Stopped')
