"""Headless setup of the parts of Wrye Bash that BashMon NG uses.

Wrye Bash normally boots through bash.py, which also loads wx, its settings
and its folders. BashMon NG only needs the Oblivion record definitions and
the save file code, so this sets up the game object directly:

- no wx, no BashSettings.dat, no Bash folders are touched;
- the game object is built with only the game path, which skips
  initialization.init_dirs (see GameInfo.__init__);
- game.init() registers the Oblivion record classes the save code needs.
"""
import os
import sys

_booted = False

def mopy_dir() -> str:
    """Return the submodule folder holding Wrye Bash's 'bash' package. In the
    frozen exe the package is bundled (see build.spec) instead."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), 'wrye-bash', 'Mopy')

def boot(game_dir: str):
    """Make Wrye Bash's 'bash' package importable and set the game.

    :param game_dir: the folder holding Oblivion.exe."""
    global _booted
    if _booted:
        return
    if not getattr(sys, 'frozen', False):
        mopy = mopy_dir()
        if not os.path.isdir(os.path.join(mopy, 'bash')):
            raise RuntimeError(f'Wrye Bash code not found in {mopy}. Run '
                               f'"git submodule update --init" first.')
        if mopy not in sys.path:
            sys.path.insert(0, mopy)
    # Installs a NullTranslations _() - English only, which is all we need
    from bash import localize  # noqa: F401
    from bash import bolt, bush
    from bash.game.oblivion import DiscOblivionGameInfo
    game = DiscOblivionGameInfo(bolt.GPath(game_dir))
    bush.game = game
    game.init()
    _booted = True
