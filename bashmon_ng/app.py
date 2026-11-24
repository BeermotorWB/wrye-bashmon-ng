"""Entry point: logging, single instance, game folder, tray + monitor."""
import logging
import os
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler

from . import config, instance
from ._version import VERSION

log = logging.getLogger('bashmon_ng')

# bashmon.log holds the current session; bashmon.log.1 (newest) to .5 the
# ones before. A session that outgrows LOG_MAX_BYTES also rolls over.
LOG_BACKUPS = 5
LOG_MAX_BYTES = 1_000_000

def _setup_logging(new_session: bool) -> str:
    """Log to bashmon.log in our data folder.

    :param new_session: True when we are the running instance: move the
        last session's log to bashmon.log.1 first. False when another
        instance owns the log: only append (renaming a log that another
        process writes to would fail on Windows)."""
    log_file = os.path.join(config.data_dir(), 'bashmon.log')
    if new_session:
        handler = RotatingFileHandler(log_file, maxBytes=LOG_MAX_BYTES,
                                      backupCount=LOG_BACKUPS,
                                      encoding='utf-8', delay=True)
        if os.path.isfile(log_file) and os.path.getsize(log_file):
            try:
                handler.doRollover()
            except OSError:
                pass # e.g. open in an editor - keep appending to it
    else:
        handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    return log_file

def _log_uncaught_errors():
    """Send errors nothing else catches to the log - the exe has no
    console, so they would otherwise vanish."""
    def main_hook(exc_type, exc, tb):
        log.critical('Unexpected error', exc_info=(exc_type, exc, tb))
    def thread_hook(args):
        if args.exc_type is SystemExit:
            return
        name = args.thread.name if args.thread else '?'
        log.critical('Unexpected error in thread %s', name, exc_info=(
            args.exc_type, args.exc_value, args.exc_traceback))
    sys.excepthook = main_hook
    threading.excepthook = thread_hook

def _ask_game_exe() -> str | None:
    """First run: let the user pick Oblivion.exe."""
    import tkinter
    from tkinter import filedialog
    root = tkinter.Tk()
    root.withdraw()
    try:
        return filedialog.askopenfilename(
            title=f'{config.APP_NAME}: select Oblivion.exe',
            filetypes=[('Oblivion', 'Oblivion.exe')]) or None
    finally:
        root.destroy()

def _game_dir() -> str | None:
    if game_dir := config.get_game_dir():
        return game_dir
    exe = _ask_game_exe()
    if not exe or os.path.basename(exe).lower() != 'oblivion.exe':
        return None
    config.set_game_exe(exe)
    return config.get_game_dir()

def selftest(game_dir: str) -> int:
    """Boot Wrye Bash's code headless and print the folders we would use."""
    from . import paths, wb_boot
    wb_boot.boot(game_dir)
    from . import saves  # noqa: F401 - import check
    lines = [f'Frozen:         {getattr(sys, "frozen", False)}',
             f'Saves folder:   {paths.saves_dir(game_dir)}',
             f'BashMon folder: {paths.signal_dir(game_dir)}',
             f'wx loaded:      {"wx" in sys.modules}']
    report = '\n'.join(lines)
    print(report)
    # The exe has no console - leave the result where it can be read
    with open(os.path.join(config.data_dir(), 'selftest.txt'), 'w',
              encoding='utf-8') as out:
        out.write(report + '\n')
    return 0

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ['--selftest']:
        return selftest(argv[1] if len(argv) > 1 else config.get_game_dir())
    if not instance.acquire():
        _setup_logging(new_session=False)
        log.info('Another instance is running (%s) - this copy (version '
                 '%s) exits', instance.read_info(), VERSION)
        return 0
    try:
        log_file = _setup_logging(new_session=True)
        _log_uncaught_errors()
        instance.write_info(VERSION)
        if not (game_dir := _game_dir()):
            log.info('No Oblivion.exe selected - exiting')
            return 1
        try:
            return _run(game_dir, log_file)
        except Exception:
            log.exception('Stopped by an error')
            return 1
    finally:
        instance.release()

def _run(game_dir: str, log_file: str) -> int:
    from . import paths, wb_boot
    from .monitor import Monitor
    from .tray import Tray
    log.info('Starting version %s, game folder %s', VERSION, game_dir)
    log.info('Exe %s, PID %d, %s, Python %s', sys.executable, os.getpid(),
             platform.platform(), platform.python_version())
    log.info('Data folder %s (config, logs, Backups)', config.data_dir())
    monitor = None
    exit_reason = 'tray stopped'
    def on_exit():
        nonlocal exit_reason
        exit_reason = 'Exit chosen in the tray menu'
        log.info(exit_reason)
        if monitor:
            monitor.stop()
        tray.stop()
    tray = Tray(log_file=log_file,
                get_saves_dir=lambda: paths.saves_dir(game_dir),
                get_signal_dir=lambda: paths.signal_dir(game_dir),
                on_exit=on_exit)
    def setup(icon):
        nonlocal monitor
        icon.visible = True
        try:
            wb_boot.boot(game_dir)
        except Exception as e:
            log.exception('Could not load the Wrye Bash save code')
            tray.set_status('error', f'Wrye Bash code failed to load: {e}')
            return
        monitor = Monitor(game_dir, os.path.join(config.data_dir(),
                                                 'Backups'), tray.set_status)
        monitor.start()
    tray.run(setup)
    if monitor:
        monitor.stop()
    log.info('Exited (%s)', exit_reason)
    return 0
