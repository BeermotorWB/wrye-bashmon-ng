# Wrye BashMon NG - code plan

## Goal

Run Wrye Morph v6.28 unchanged on a modern setup. BashMon NG is a tray app
that answers Morph's requests by editing the quicksave with Wrye Bash's own
save code (git submodule `wrye-bash/`).

## Protocol (verified against `Wrye Morph, X6.esp` scripts)

All files live in `Documents\My Games\Oblivion\Pluggy\User Files\BashMon\`.
Pluggy builds that path from the Documents folder alone and never reads
`Oblivion.ini`, so it stays there even when `bUseMyGamesDirectory=0` moves
the saves to the game folder. (The original bashmon used `saveBase` here,
which broke on such setups.)

| Step | Morph (in game) | BashMon NG |
|---|---|---|
| Ping | writes `Temp.txt`, renames to `Ping.txt` | renames `Ping.txt` to `Pong.txt` |
| Request | writes `Temp.txt`, renames to `Request.txt` | runs each line |
| Result | waits 20 s | touches `Completed.txt` or `Failed.txt` |
| Cleanup | deletes `Request`, `Completed`, `Failed` | waits until `Completed.txt` is gone |

Commands Morph sends:

- `moveSave quicksave.ess WryeMorphOldQS.ess` (and the reverse)
- `swapPlayer quicksave.ess 0x<oldBase> 0x<newBase>`

Saves are in `<saveBase>\<SLocalSavePath>` (default `Saves\`), read from the
main `Oblivion.ini`. BashMon NG never writes INIs.

## Modules (`bashmon_ng/`)

| Module | Job | Wrye Bash APIs used |
|---|---|---|
| `wb_boot.py` | headless Wrye Bash setup: `sys.path`, `localize`, Oblivion `GameInfo(game_path)` (no `init_dirs`), `game.init()` | `bush`, `localize`, `game.oblivion` |
| `config.py` | remembers `Oblivion.exe` in `%LOCALAPPDATA%\Wrye BashMon NG\config.json` | none |
| `paths.py` | `saveBase`, saves folder, Pluggy BashMon folder; reads INIs only | none (configparser) |
| `saves.py` | load/save a save file, created-NPC face get/set, `swap_player`, `move_save` | `bosh._saves.SaveFile`, `bosh.faces.PCFaces`, `brec.FormId` |
| `monitor.py` | polling loop (0.25 s) in a thread; reports status | none |
| `tray.py` | pystray icon, blue = watching, red = error; tooltip; menu | pystray, Pillow |
| `instance.py` | single instance via Windows mutex | ctypes |
| `app.py` | entry point; logging; first-run game picker | tkinter file dialog |

### Notes on the Wrye Bash save code

- `SaveFile` only needs `abs_path`, `fn_key`, `fsize`, `makeBackup()` and
  `setmtime()` from its file info. `saves.py` passes a small adapter, so no
  `SaveInfos`, settings or Bash folders are needed.
- `PCFaces.save_getCreatedFace` was removed upstream; `saves.py` rebuilds it
  from the record attributes (`PCFace.set_from_npc`), as `mod_getFaces` does.
- `PCFaces.save_setCreatedFace` (marked unused upstream) maps FormIDs through
  `MasterMap`, which returns tuple-based FormIds whose `short_fid` loses the
  master index when written in short format. `saves.py` uses its own setter
  that keeps the save's own short FormIDs (source and target are the same
  save, so no master remapping is needed).
- `moveSave` renames the `.ess` plus its `.obse` and `.pluggy` cosaves.
- `bolt.intArg` no longer exists; `int(x, 0)` replaces it.

## UI rules

- No toasts or any other notifications - they break fullscreen DirectX games.
- Errors: write `Failed.txt` (Morph shows its own message), icon turns red,
  keep watching.
- Log: `%LOCALAPPDATA%\Wrye BashMon NG\bashmon.log` (rotating).

## Install

Unzip the release (`WryeBashMonNG-<version>.zip`) into `Mopy\`: it holds
`BashMonNG\bashmon.exe` (the original's exe name, one self-contained file).
The user adds a custom launcher in
Wrye Bash's status bar.

## Test steps

1. Headless boot imports fine (`python -m bashmon_ng --selftest`).
2. Load + save a copy of a real quicksave; file is byte-identical.
3. `swap_player` on a save copy with Morph identities; load it in game.
4. In game: ping, shift, quickload, reverse `moveSave`.
5. Bashed Patch with Morph Factions (unchanged Wrye Bash feature).
