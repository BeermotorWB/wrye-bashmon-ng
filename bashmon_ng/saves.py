"""Save game operations Wrye Morph asks for: swapPlayer and moveSave.

Uses Wrye Bash's Oblivion save code (bosh._saves.SaveFile, bosh.faces). Call
wb_boot.boot() before importing this module.
"""
import logging
import os
import shutil

from bash import bush
from bash.bolt import FName, GPath
from bash.brec import FormId
from bash.brec.mod_io import ShortFidWriteContext
from bash.bosh._saves import SaveFile, SreNPC
from bash.bosh.faces import PCFaces

log = logging.getLogger(__name__)

# Default player swap flags, as in the original bashmon: name, race, gender,
# hair, eyes, class and stats
SWAP_FLAGS = 0x1 | 0x2 | 0x4 | 0x8 | 0x10 | 0x20 | 0x40
_IMPERIAL_RACE = 0x00907

class MorphError(Exception):
    """A request we cannot carry out."""

def parse_int(value: str) -> int:
    """'0x1A2B' or '6699' -> int (replaces bolt.intArg, which is gone)."""
    return int(value, 0)

class _SaveTarget:
    """The few parts of bosh.SaveInfo that SaveFile uses, without needing
    Wrye Bash's SaveInfos store, settings or Bash folders."""

    def __init__(self, save_path: str, backup_dir: str):
        self.abs_path = GPath(save_path)
        self.fn_key = FName(os.path.basename(save_path))
        self.fsize = os.path.getsize(save_path)
        self.ftime = os.path.getmtime(save_path)
        self._backup_dir = backup_dir

    def makeBackup(self, forceBackup=False):
        """Keep a copy of the save as it was before we changed it."""
        os.makedirs(self._backup_dir, exist_ok=True)
        shutil.copy2(self.abs_path.s,
                     os.path.join(self._backup_dir, f'{self.fn_key}.bak'))

    def setmtime(self, set_time=0.0, **kwargs):
        """Keep the original timestamp, like Wrye Bash does."""
        os.utime(self.abs_path.s, (set_time or self.ftime,) * 2)

    def __str__(self):
        return str(self.fn_key)

def load_save(save_path: str, backup_dir: str) -> SaveFile:
    if not os.path.isfile(save_path):
        raise MorphError(f'Save not found: {save_path}')
    save_file = SaveFile(_SaveTarget(save_path, backup_dir))
    save_file.load()
    return save_file

def _find_created_npc(save_file: SaveFile, npc_fid: int):
    """Return (key, record) of the created NPC with this FormID."""
    for rfid, record in save_file.created.items():
        if rfid == npc_fid:
            if record._rec_sig != b'NPC_':
                raise MorphError(f'Record {npc_fid:08X} in '
                                 f'{save_file.fileInfo} is not an NPC.')
            return rfid, record
    raise MorphError(f'Record {npc_fid:08X} not found in '
                     f'{save_file.fileInfo}.')

def _short(value):
    """FormId -> int; created NPCs keep the save's own short FormIDs."""
    return value.short_fid if isinstance(value, FormId) else value

def get_created_face(save_file: SaveFile, npc_fid: int):
    """Read the face/stats of a created NPC (one of Morph's stored shapes).

    Replaces PCFaces.save_getCreatedFace, removed from Wrye Bash. Follows
    PCFaces.mod_getFaces for the record attributes. Created NPCs do not use
    irefs - their FormIDs index the save's own master list."""
    rfid, record = _find_created_npc(save_file, npc_fid)
    npc = record.getTypeCopy()
    face = PCFaces.PCFace()
    face.face_masters = save_file._masters
    for att in PCFaces.PCFace.set_from_npc:
        setattr(face, att, _short(getattr(npc, att)))
    face.gender = int(npc.npc_flags.npc_female)
    face.pcName = npc.full or ''
    # Stats changed during play live in the NPC's change record
    PCFaces.save_getChangedNpc(save_file, rfid, face)
    return face

def set_created_face(save_file: SaveFile, npc_fid: int, face):
    """Store a face/stats into a created NPC (one of Morph's stored shapes).

    Based on PCFaces.save_setCreatedFace, which maps FormIDs through
    MasterMap. That yields tuple-based FormIds whose short_fid drops the
    master index when written in the save's short format, so this writes the
    save's own short FormIDs instead. The face comes from the same save, so
    no master remapping is needed."""
    rfid, record = _find_created_npc(save_file, npc_fid)
    npc = record.getTypeCopy()
    save_file.created[rfid] = npc
    def fid(value):
        return FormId(value) if value else None
    npc.npc_flags.npc_female = bool(face.gender & 0x1)
    npc.full = face.pcName
    npc.setRace(FormId(face.race or _IMPERIAL_RACE))
    npc.eye = fid(face.eye)
    npc.hair = fid(face.hair)
    for att in ('hairLength', 'hairRed', 'hairBlue', 'hairGreen', 'unused3',
                'fggs_p', 'fgga_p', 'fgts_p'):
        setattr(npc, att, getattr(face, att))
    # Level, base spell, fatigue and factions go in the change record below
    if face.skills: npc.skills = face.skills
    if face.health:
        npc.health = face.health
        npc.unused2 = face.unused2
    if face.attributes: npc.attributes = face.attributes
    if face.npc_class: npc.npc_class = fid(face.npc_class)
    npc.setChanged()
    with ShortFidWriteContext():
        npc.getSize()
    #--Change record?
    change_record = save_file.get_npc(rfid)
    if change_record is None:
        return
    sre_npc, version = change_record
    if not sre_npc.acbs:
        sre_npc.acbs = SreNPC.ACBS()
    sre_npc.acbs.npc_flags.npc_female = face.gender
    sre_npc.acbs.level_offset = face.level_offset
    sre_npc.acbs.base_spell = face.base_spell
    sre_npc.acbs.fatigue = face.fatigue
    sre_npc.modifiers = face.modifiers[:]
    get_iref = save_file.getIref
    sre_npc.spells = [get_iref(x) for x in face.spells]
    sre_npc.factions = [(get_iref(x), y) for x, y in face.factions]
    save_file.fid_recNum[rfid] = sre_npc.getTuple(version)

def write_save(save_file: SaveFile):
    save_file.safeSave()

# Commands --------------------------------------------------------------------
def swap_player(saves_dir: str, backup_dir: str, save_name: str,
                old_form: str, new_form: str, flags: str = None):
    """Store the player's current shape in old_form, then turn the player
    into new_form. Returns 'OldName >> NewName'."""
    old_fid, new_fid = parse_int(old_form), parse_int(new_form)
    swap_flags = SWAP_FLAGS if flags is None else parse_int(flags)
    save_path = os.path.join(saves_dir, os.path.basename(save_name))
    save_file = load_save(save_path, backup_dir)
    #--player >> old form
    old_face = PCFaces.save_getPlayerFace(save_file)
    set_created_face(save_file, old_fid, old_face)
    #--new form >> player
    new_face = get_created_face(save_file, new_fid)
    PCFaces.save_setPlayerFace(save_file, new_face, swap_flags)
    write_save(save_file)
    return f'{old_face.pcName} >> {new_face.pcName}'

def _cosave_paths(save_path: str) -> list[str]:
    root = os.path.splitext(save_path)[0]
    return [root + bush.game.Se.cosave_ext, root + '.pluggy']

def move_save(saves_dir: str, old_save: str, new_save: str):
    """Rename a save and its .obse/.pluggy cosaves, replacing the target.

    Only file names are used, so nothing outside the saves folder is
    touched."""
    old_path = os.path.join(saves_dir, os.path.basename(old_save))
    new_path = os.path.join(saves_dir, os.path.basename(new_save))
    if os.path.exists(new_path) and not os.path.isfile(new_path):
        raise MorphError(f'{new_path} exists and is not a save file.')
    if not os.path.exists(old_path):
        return f'{old_save} not found, nothing to move'
    if not os.path.isfile(old_path):
        raise MorphError(f'{old_path} is not a save file.')
    pairs = [(old_path, new_path),
             *zip(_cosave_paths(old_path), _cosave_paths(new_path))]
    for src, dst in pairs:
        if os.path.isfile(src):
            os.replace(src, dst)
        elif os.path.isfile(dst):
            # A stale cosave would belong to the wrong save - drop it
            os.remove(dst)
    return f'{old_save} -> {new_save}'

def run_command(line: str, saves_dir: str, backup_dir: str) -> str:
    """Run one request line from Wrye Morph."""
    command, *args = line.split()
    if command == 'swapPlayer':
        return swap_player(saves_dir, backup_dir, *args)
    if command == 'moveSave':
        return move_save(saves_dir, *args)
    raise MorphError(f'Unknown command: {command}')
