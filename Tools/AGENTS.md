# GuessWho — shared brief for the parallel agents

Read `../PLAN.md` first (game design, in French). The user (Québec French speaker) knows nothing about Unreal and expects a finished, playable, multiplayer game. **All in-game text is in French.**

**Minimal QA (user's order, 2026-11-05: it burns too many tokens).** After a change, run at most one short check aimed at what changed and read only its summary or a filtered log. After a build, one `pkg_nettest.ps1` is enough. No `qa_suite`, render/screenshot sweeps, repeated test rounds or QA subagents unless the user asks. A failing check still gets fixed. Report what was not tested instead of testing more. This overrides any heavier test instruction in these docs.

**Last one standing (the user, 2026-11-06).** There are no detectives any more: every player is a guest, the last one alive wins. Older docs and scripts still mention seekers; `IsSeeker` and `GWRole 2` are never set. Rules: `gameplay/s46_last_standing.py`, whose docstring gives the order.

**Public repository (github.com/Tantris514/guess-who).** `.gitignore` is an allow-list; game content goes through Git LFS, without Epic's templates. Never publish builds (they carry the EOS keys), `GuessWho/Config/DefaultEngine.ini` or `Tools/online/eos_credentials.ini`. New keys go in `[GWEOS]` in that config, not in code. Scan before each push.

**Editor memory (2026-11-06).** Each recompile of `BP_GW_GameMode` in the same editor adds about 10 GB, and the editor dies of memory after a few ("paging file too small", then `ConnectionResetError` and "interactive editor not found"). Restart the editor between writes that compile it. A runner's exit code 0 proves nothing: read its output.

## Machine and constraints

- Windows 11, RTX 5070 12 GB, **32 GB RAM that is already under heavy pressure** (≈2 GB available). Never start a second Unreal Editor or a second ComfyUI. Keep big outputs out of your context (write to files, print summaries).
- Shells: PowerShell 5.1 (no `&&`; avoid inline Python with `<`/quotes; write `.py` files instead) and Git Bash. Run Python helpers with the system Python as `python -I -X utf8 <script>`. Python that needs numpy/PIL: `V:\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe -I <script>`.
- **C++ is limited to `GuessWho/Source/GuessWho` (EOS code games, `GWOnline.cpp`)**; gameplay stays Blueprint. VS 2022 Build Tools are installed. After changing Source/, run `Tools\online\build_code_targets.ps1 -Editor` with the editor closed. Do not enable other runtime plugins without need (no GameplayAbilities, no CommonUI, etc.). Editor-only plugins must have `"TargetAllowList": ["Editor"]` in the .uproject (already done for the MCP plugins).

## Paths

| What | Where |
|---|---|
| Engine (UE 5.8.4, launcher-style install) | `J:\Projets\Unreal_Projects\Guess Who\UE_5.8` |
| Project | `J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject` |
| Tools / scripts / logs | `J:\Projets\Unreal_Projects\Guess Who\Tools` (logs in `Tools\agent_logs\`) |
| ComfyUI asset pipeline | `J:\Projets\Unreal_Projects\Guess Who\AssetGen` |
| ComfyUI server | `http://127.0.0.1:8188` (already running, launched by Comfy Desktop — do not restart it) |

## The shared Unreal Editor

- One editor runs headless (`-nullrhi`): MCP at `http://127.0.0.1:8010/mcp`, Python remote execution on loopback.
- If it is not running: `powershell -NoProfile -ExecutionPolicy Bypass -File Tools\start_editor.ps1` (no-op if one is up). For screenshots you need rendering: only the coordinator restarts it with `-Render`.
- **Run Python in the editor**: `python -I -X utf8 Tools\ue_py.py path\to\script.py [args]` (args are in `UE_ARGS`), or `-c "code"` (`unreal` is imported). Print concise results. Always `unreal.EditorAssetLibrary.save_loaded_asset(...)` / `save_directory` after changes.
- **Unreal MCP over HTTP**: `python -I -X utf8 Tools\http_mcp_call.py http://127.0.0.1:8010/mcp steps.jsonl` (one JSON step per line: `{"method":"tools/call","params":{"name":"call_tool","arguments":{"toolset_name":"...","tool_name":"...","arguments":{...}}},"max":4000}`). `Tools\ue_describe.py <toolset> [-v]` lists a toolset's tools. Meta tools: `list_toolsets`, `describe_toolset(toolset_name)`, `call_tool(toolset_name, tool_name, arguments)`.
- The toolsets are Python you can read and import inside the editor: `UE_5.8\Engine\Plugins\Experimental\Toolsets\EditorToolset\Content\Python\editor_toolset\toolsets\*.py` (e.g. `from editor_toolset.toolsets.blueprint import BlueprintTools`). Examples of every feature in `...\editor_toolset\tests\test_blueprint_dsl.py`.
- **Blueprint graphs are written with the graph DSL**: `BlueprintTools.write_graph_dsl(graph, code)`; syntax in `Tools\ue_dsl_docs.txt`. Never guess node type ids or pin names: use `find_node_types` / `get_node_type_pins` first. Other useful tools: `create`, `add_variable`, `set_variable_replication` (NONE/REPLICATED/REP_NOTIFY), `add_function_graph`, `add_event`, `compile_blueprint`, `set_parent`, `get_default_object` + ObjectTools `set_properties`.
- Two agents share this editor. Only touch the assets you own (below). Retry a remote-exec call if it fails because the other agent is mid-command.

## Ownership (do not modify what you do not own)

| Agent | Owns |
|---|---|
| **assets** | Everything under `AssetGen\` and the ComfyUI GPU. Never touches Unreal. |
| **gameplay** | `/Game/GW/Blueprints`, `/Game/GW/UI`, `/Game/GW/Input`, `/Game/GW/Maps/L_MainMenu`, `/Game/GW/Audio`, `Config\DefaultEngine.ini` / `DefaultGame.ini` / `DefaultInput.ini` (project settings: maps, game modes, network). |
| **level** | `/Game/GW/Materials`, `/Game/GW/Textures`, `/Game/GW/Meshes`, `/Game/GW/Maps/L_Manor`, lighting, navmesh, post-process. |
| coordinator | Integration, `.uproject`, packaging, final QA. |

Template content already copied into the project (read-only, shared): `/Game/Characters/Mannequins` (SKM_Manny_Simple, SKM_Quinn_Simple, ABP_Unarmed, death/pistol/rifle anims, M_Mannequin + MIs), `/Game/Input` (IMC_Default, IMC_MouseLook, IA_Move/IA_Look/IA_MouseLook/IA_Jump), `/Game/ThirdPerson/Blueprints` (BP_ThirdPersonCharacter / GameMode / PlayerController — copy or subclass, don't edit).

## Contracts between agents

- **Map**: `/Game/GW/Maps/L_Manor` (level agent builds it). Its World Settings GameMode override = `/Game/GW/Blueprints/BP_GW_GameMode` (level agent sets it once gameplay has created the class; gameplay may also set the project default game mode).
- **Level provides** (for gameplay): a `NavMeshBoundsVolume` covering the whole walkable manor with the RecastNavMesh set to **dynamic runtime generation**; actors tagged `GW_SeekerSpawn` (≥4 TargetPoints in the closed "seeker waiting" spot); ≥8 `PlayerStart`s; actors tagged `GW_NPCSpawn` (≥40 TargetPoints spread on walkable floor in every room) — gameplay may also use random reachable navmesh points.
- **Assets provide** (for level and gameplay): `AssetGen\manifest.json`, updated after each approved asset:
  `{"assets": [{"name": "...", "kind": "prop|character_item|texture_tileable|wallpaper|rug|painting|window|keyart", "status": "approved", "files": {...absolute paths: glb, image, basecolor, normal, roughness...}, "size_cm": [w, d, h], "rooms": ["library", ...], "notes": "..."}]}`.
  Level imports props/textures from it; gameplay uses `character_item`s (masks, hats, revolver) and the keyart.
- **Character look**: every NPC and every hider uses the same character Blueprint, so they are indistinguishable. Outfits come from a shared list (material colour variants + hat/mask). Seekers ("détectives") get a distinct look (trench colour, fedora, revolver).

## Network design (gameplay; decided, don't redesign)

- Listen server; join by IP (`open <ip>`), host via `OpenLevel(L_Manor, "listen")`. Player name via URL option `?Name=`.
- Server→clients: replicated variables + RepNotify (round state and timer in GameState, role/alive in PlayerState, outfit/seeker/dead/health/shot counter on the character).
- **Client→server: there are no custom RPCs in this toolchain** (custom-event replication flags cannot be set by the tools). Use the engine's `ServerExec`: on the client call `ExecuteConsoleCommand("ServerExec GWFire")`; the server runs the console command for that player, which reaches **Exec functions** on the server-side PlayerController/Pawn (`UPlayer::Exec` → `ProcessConsoleExec`). Mark those Blueprint functions Exec (`BlueprintGraphEditor.set_is_exec_function`). Validate everything on the server (role, alive, round state, cooldown). This works in editor PIE and in **Development** packaged builds (not Shipping) — we ship Development.

## Reporting

Append short progress notes to `Tools\agent_logs\<agent>.md` (what is done, what is blocked, paths). End with a concise summary of what exists, how it was verified, and what is left.

## Added 2026-11-01 ~22:50: UI/UX + audio agent, and edit locks

- **ui agent** (new) owns: `/Game/GW/UI`, `/Game/GW/Audio`, `AssetGen/ui/`, `AssetGen/audio/`, `Tools/ui/`, the menu game mode/controller,
  sound classes/mixes, settings save. Its log: `Tools/agent_logs/ui.md`.
- ComfyUI is shared between the assets agent (3D) and the ui agent (UI art, music, SFX). Jobs queue FIFO and interleave.
  Nobody interrupts, clears the queue, frees models or restarts ComfyUI.
- Ambient sound actors the ui agent adds to L_Manor carry the tag `GW_Audio` only (never `GW_Gen`), so level rebuilds keep them.
- **Locks**: before modifying a Blueprint that more than one agent may touch (BP_GW_PlayerController, BP_GW_GameState,
  BP_GW_GameInstance, BP_GW_Character, WBP_HUD), append `LOCK <asset> <agent> <time>` to `Tools/agent_logs/locks.md`, and
  `UNLOCK <asset> <agent> <time>` once compiled and saved. Do not edit an asset someone else holds.
- **Rendered editor**: the coordinator may restart the shared editor with `-Render` for screenshot QA. If a remote-exec call fails
  because the editor is restarting, wait for port 8010 and retry; do not start a second editor.