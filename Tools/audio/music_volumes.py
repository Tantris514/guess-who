"""Playback volume of the music SoundWaves in /Game/GW/Audio (editor script, re-runnable).
2026-11-03: MUS_Party / MUS_Gramophone were re-generated without brass (AssetGen/audio/music_soft_apply.py), so the volume cut
of the trumpet version (0.5 / 0.45) is lifted to 0.8 / 0.7. MUS_Hunt_Soft is a brass-free alternative for the hunt (not used
by the HUD unless someone swaps it in).   python -I -X utf8 Tools\\ui\\ue_run.py Tools\\audio\\music_volumes.py"""
import unreal

EAL = unreal.EditorAssetLibrary
for name, vol in (("MUS_Party", 0.8), ("MUS_Gramophone", 0.7), ("MUS_Hunt_Soft", 0.9)):
    p = f"/Game/GW/Audio/{name}"
    if not EAL.does_asset_exist(p):
        print("missing", p); continue
    w = unreal.load_asset(p)
    w.set_editor_property("volume", vol)
    w.set_editor_property("looping", True)
    EAL.save_loaded_asset(w, False)
    print("volume", name, vol, "duration", round(w.get_editor_property("duration"), 1))
