# Wrye BashMon NG

A standalone Python 3 port of **bashmon**, the companion monitor that
[Wrye Morph](https://www.nexusmods.com/oblivion/mods/28563) needs for
shapeshifting the player. Wrye Bash dropped bashmon in 2017
(wrye-bash/wrye-bash#369); this project brings it back as a separate
executable that runs alongside a normal Wrye Bash install.

Status: **work in progress, use at your own risk.**

## Requirements (in game)

- Oblivion (classic, not Remastered)
- OBSE and Pluggy 0.89 or newer
- Cobl
- Wrye Morph 6.28
- Wrye Bash, for the Bashed Patch "Morph Factions" option

## How to use BashMon

### Build the Bashed Patch (once)

Wrye Morph needs Morph Factions to shift your factions, and its optional
plugins work only when merged. `Cobl Main.esm` must be active, or Morph
Factions does nothing.

1. In Wrye Bash's **Mods** tab, right-click `Bashed Patch, 0.esp` and choose
   **Rebuild Patch…**.
2. In the list on the left, tick **Merge Patches**. Click it to select it:
   the list on the right ("Mergeable Plugins") shows the plugins Wrye Bash
   can merge. Tick **every Cobl and Wrye Morph plugin** in it, e.g.
   `Wrye Morph Wearable.esp` and `Wrye Morph-See You Sleep.esp`.
3. In the list on the left, tick **Morph Factions**.
4. Click **Morph Factions** to select it. In the list on the right, tick
   **`Bash_MFact.csv`**. It is **not** ticked for you. (The file ships
   with Wrye Bash in `Mopy\Bash Patches\Oblivion\`. Tick any other
   `*_MFact.csv` files you have too.)
5. (Optional) Give guards their own names, so a doppelganged guard has a
   real name: tick **Import Names**, click it to select it, and tick
   **`Guard_Names.csv`** in the list on the right. (It ships with Wrye Bash
   in the same folder.)
6. Click **Build Patch**, and make sure the Bashed Patch is active.

Rebuild the patch the same way whenever your faction mods change.

### Install and run

1. Download `WryeBashMonNG-<version>.zip` from
   [Releases](https://github.com/BeermotorWB/wrye-bashmon-ng/releases) and
   unzip it into Wrye Bash's `Mopy\` folder. You get
   `Mopy\BashMonNG\bashmon.exe`.
2. Add a BashMon button to Wrye Bash's status bar:
   1. Open **Settings → Global Settings…** and go to **Status Bar**.
   2. Click **New**.
   3. **Name:** `BashMon`. **Application path:** use the file picker to
      choose `Mopy\BashMonNG\bashmon.exe`.
   4. Click **Save**. The button appears at the end of the status bar.
3. Click the **BashMon** button (or start `bashmon.exe`) **before** the
   game. The exe is not code signed, so
   Windows SmartScreen may warn on the first start: click **More info**,
   then **Run anyway**.
4. On the first start, pick your `Oblivion.exe`. BashMon remembers it.
5. BashMon runs in the system tray: **blue** = watching, **red** = error.
   Hover for its status. Right-click for Open Log, Open Save Folder, Open
   BashMon Folder and Exit; double-click opens the log.
6. Start the game through OBSE. When a save loads, Wrye Morph pings
   BashMon; the console shows "Wrye Morph: Bashmon is Alive".
7. Get the **Book of Souls** from Wrye Morph's quest: it starts at Fatback
   Cave, south of the Arcane University. Have BashMon running **before**
   you start the quest.
8. Use the Book of Souls to shift shapes. BashMon does its work between
   Morph's quicksave and quickload.

BashMon never shows pop-ups or notifications, so fullscreen games are not
interrupted. Its log and settings are in `%LOCALAPPDATA%\Wrye BashMon NG\`,
along with a backup of the last save it changed (`Backups\`). Only one
BashMon runs at a time.

Check a download against `SHA256SUMS.txt` from the same release:

```
certutil -hashfile WryeBashMonNG-<version>.zip SHA256
```

## How it works

Wrye Morph's scripts exchange text files with bashmon through Pluggy's
`My Games\Oblivion\Pluggy\User Files\BashMon\` folder (`Ping.txt`,
`Request.txt`, `Completed.txt`, `Failed.txt`). On a request, bashmon edits
the quicksave (`swapPlayer`) or renames it with its cosaves (`moveSave`);
Morph then quickloads.

## Repository layout

- `bashmon_ng/` - the port
- `legacy/` - original Python 2 bashmon versions, for reference

## License

GPL-3.0-or-later, same as Wrye Bash. See `LICENSE.md`.
