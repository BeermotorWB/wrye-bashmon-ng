"""Entry point: logging, single instance, game folder, tray + monitor."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from . import config, instance
from ._version import VERSION

log = logging.getLogger('bashmon_ng')

def _setup_logging() -> str:
    log_file = os.path.join(config.data_dir(), 'bashmon.log')
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000,
                                  backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    return log_file

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
    log_file = _setup_logging()
    if not instance.acquire():
        log.info('Another instance is running - exiting')
        return 0
    try:
        if not (game_dir := _game_dir()):
            log.info('No Oblivion.exe selected - exiting')
            return 1
        return _run(game_dir, log_file)
    finally:
        instance.release()

def _run(game_dir: str, log_file: str) -> int:
    from . import paths, wb_boot
    from .monitor import Monitor
    from .tray import Tray
    log.info('Starting version %s, game folder %s', VERSION, game_dir)
    monitor = None
    def on_exit():
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
    log.info('Exited')
    return 0
