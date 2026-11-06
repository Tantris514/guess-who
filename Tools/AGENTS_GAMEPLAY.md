# Gameplay scripting — conventions and traps (read before writing a gameplay script)

The game is Blueprint-only and every Blueprint graph is written by a Python script in `Tools\gameplay\` (gameplay,
`gw_lib`) or `Tools\ui\` (widgets, `uilib`). Never edit a Blueprint by hand or with a one-off command: the script is
the source of truth and must stay re-runnable (it is re-run after other changes). Also read `Tools\AGENTS.md`.

## Read first (in this order)
1. `Tools\ue_dsl_docs.txt`: the graph DSL.
2. `Tools\gameplay\gw_lib.py`: `load_bp`, `load_or_create_bp`, `ensure_var` (rep=, struct=, obj_class=, array=),
   `ensure_fn` (inputs/outputs, `exec_fn=True` for console-callable server commands), `ensure_component`,
   `write(bp, fn, code)`, `compile_bp`, `save`, `cdo`, `wire_input`, `find_types(bp, 'Name')`, `pins(bp, type_id)`.
3. `Tools\gameplay\s33_piano.py`: a complete small feature, from input action and mapping through the client →
   server command, game mode, game state and HUD feedback. Copy its structure.
4. `Tools\gameplay\s32_events.py`: replicated effect actors with components, AI controllers, game-mode helpers
   (`HurtCharacter`, `Explode`, `SpawnSpecial`).
5. `Tools\gameplay\s31_reactions.py`: the sound bank, `Say` / `QueueSay` / `WorldSound` / `NearestNPC` /
   `StartPanic` / `DeathCry`, and the CAT categories.
6. `Tools\ui\u15_dev_menu.py`: the dev menu (F2). Add an entry by adding one line in `PAGES`, its server command in
   `EXEC` and its body in the PC function dict. The widget is data-driven: `u15_dev_menu.py data` applies PAGES lines in
   seconds; `pc` writes Exec bodies; `widget` is only for new `ui()` / `checkui()` DSL. No Oui/Non options: use
   `check(label, 'GWDevX {}', flag)` with a bit of `GS.DevFlags` (set it in `DevFlagsPush`), which shows the real value.
   HUD rules: nothing at the top of the screen, no subtitles; life bottom-left, money bottom-right, item slots between them (u14_hud.py, s40_inventory.py ui). Personal messages go through
   `LocalNotice` (low on the screen); events show red mid-screen from `GS.EventName`; `GS.LastEvent` (Announce) is not
   displayed any more. HUD widget Tick logic does not run under `-nullrhi`: check it with a rendered run (`-GWUIQA`).
   A new input action appears in Options > Commandes after re-running `u11_screens.py options` (label in `KEY_LABELS`).
7. `Tools\ui\u16_curtain.py`: a small widget built with `uilib`.

## Running
- `python -I -X utf8 Tools\ui\ue_run.py "J:\...\Tools\gameplay\sXX.py"` runs a script in the shared headless editor.
  It waits by itself while `Tools\agent_logs\locks.md` shows `LOCK BUILD`.
- The machine is out of RAM: a stuck ComfyUI holds ~22 GB. The editor crashed once with "out of memory". If
  `ue_run` fails with ConnectionReset, check `tasklist | grep UnrealEditor`. If the editor is gone, run
  `powershell -File Tools\start_editor.ps1`, wait until `ue_run.py -c "print(1)"` answers, then re-run your script.
  A crash loses only that script's unsaved work.
- Headless game test (no GPU, works while the user plays):
  `"J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject" /Game/GW/Maps/L_Manor?listen?Name=Hote -game -nullrhi -nosound -unattended -nosplash -NoLiveCoding -GWDev -GWName=Hote -log -abslog=<your log>`
  Add `-GWDevTest` to run the automated dev-menu script (`DevTestTick` in u15, a command every 2 s). Log your own
  checkpoints with `(Development|PrintString :InString (cat "GW: ...") :bPrintToScreen false)`, then grep the log.
  Count `Accessed None`, `LogScript: Error|Blueprint Runtime Error`, `LogScript: Warning`: all must stay at 0.
- MEMORY (the editor crashed out of memory twice tonight): only ONE headless game test may run at a time on the whole
  machine. Before starting one, append `LOCK GAMETEST <agent> <time>` to locks.md. If another GAMETEST lock is open,
  wait. Append `UNLOCK GAMETEST ...` as soon as it ends, and keep tests short (≤ 5 min). Never leave a waiting python
  process per ComfyUI job: one collector process per agent.
- Compiles and game tests exclude each other: never start a game test while a Blueprint LOCK is open, and never
  start a compile while a GAMETEST lock is open (a -game process holding assets makes saves fail silently).
  After every compile, check that the saved .uasset timestamps moved.
- No rendered test (editor `-game` without `-nullrhi`) while the user is playing (`tasklist | grep UnrealGame`).
  Rendering competes with their game. Never make a packaged build: the coordinator does it.

## Item models
`Tools\gameplay\s41_item_models.py` puts the approved 3D models on the components of the item Blueprints. s34, s35, s37, s38, s40_inventory and
s40_events2 put the basic shapes back when re-run: run s41 after them (no args). `Tools\qa\py_harness.ps1 -Plan items -Render` shoots every item
with no test code to compile (Python steps inside the -game run).
`DestroyActor` on an AI controller does nothing in this game (measured, plan zomb4): end it with `UnPossess` + `SetLifeSpan`.

## DSL traps that already cost hours
- A `bind` of a pure node is re-evaluated at every use. Random picks, array reads and "get then change" values
  must go into a variable first: `(Variables|GW|SetX ...)`, then `(Variables|GW|GetX)`.
- A cast block `(bind x (Utilities|Casting|CastToY obj) (:then ...) (:CastFailed ...))` must be the last statement of
  its branch. Put anything that must follow inside `:then`.
- `(return)` followed by more statements in the same branch is an error ("Unreachable code after branch/return").
  `(if cond (return))` followed by more code is fine.
- No `bind` of a literal.
- `switch int` gets one exec pin per case, numbered from 0 by count. Cases 1..5 do NOT give a pin named "5". Use
  contiguous cases starting at 0, or `if` chains.
- Cross-Blueprint access: `(GW|Get|BP_X|Var :self obj)`, `(GW|Set|BP_X|Var :self obj :Var v)`,
  `(GW|Call|BP_X|Fn :self obj :Arg v)`. Own variables: `(Variables|<Category>|GetVar)` / `SetVar`. Components:
  `(Variables|Default|Get<Component>)`. Function-local variables: `BT.add_variable(bp, name, type, graph=g)`, then
  `Variables|Default|...`.
- Client → server: there are no custom RPCs. Use Exec functions on `BP_GW_PlayerController` (`ensure_fn(..., exec_fn=True)`).
  The host calls them directly; a client sends `(Development|ExecuteConsoleCommand :Command "ServerExec Name args" :SpecificPlayer self)`.
  Validate everything on the server (role, alive, distance, money).
- Server → clients: replicated variables. Use RepNotify for visuals; setting one on the server also runs the
  OnRep there.
- Never `unreal.EditorAssetLibrary.save_*` while `LOCK BUILD` is up. `ue_run` waits; your own direct calls do not.
- Git Bash collapses `\\` inside quoted heredocs. Write patch scripts with the file-writing tool and run them with
  `python -I -X utf8 file.py`.
- Check that a node exists before using it: `gw_lib.find_types(bp, 'SetAllBodiesBelow')` inside a small editor script.
- Blueprint `and` / `or` evaluate BOTH sides: `(and (IsValid m) (... m ...))` still reads a destroyed actor, and
  `(and (>= Idx 0) (== Arr[Idx] 0))` still reads index -1. Put the validity / range test in its own `if`.
- Inside a Blueprint, `GW|Get|<same class>|Var` gives a getter with no target pin, so one instance can't read another
  instance's variable that way (e.g. one NPC controller reading another's). Use a function on the other instance.
- s14's `GoTo` stops about 60 cm plus the capsule radius short of its target: use an arrival radius ≥ 2 m.
- Editor runs connect to ONE shared editor that runs one command at a time: a 10-min compile (e.g. WBP_DevMenu)
  blocks everyone. ue_run.py waits up to 15 min for it now; game tests use a port other than 7777 (the packaged smoke
  test joins 127.0.0.1:7777).

## Shared hooks (owned by the coordinator; call them, don't rewrite them)
- `BP_GW_GameMode.ReactionsTick` (s31) runs often on the server. It already calls `ShopTick`, `SocialTick` and
  `TurretTick`; you own the body of yours.
- `BP_GW_PlayerController.EventClientTick` (s32) runs every 0.1 s on each local player. It already calls
  `ShopClientTick`, `SocialClientTick`, `TurretClientTick` and `ViewClientTick`.
- `BP_GW_PlayerController.RequestInteract` (s33, the E key): the piano first, then `InteractOther` (coordinator).
  `InteractOther` tries `TryShop`, `TryTurret`, `TryDefuse` in order, each returning `Handled`. You own the body of
  yours.
- `BP_GW_GameMode.RewardNPCKill(Killer: Pawn, Victim: BP_GW_Character)`: call it whenever a guest player kills an NPC
  (gun, turret, bomb, trap). The shop agent owns its body: +100 $ and a loud, positional scream.
- `BP_GW_GameMode.DeathCry(Victim)` (s31): the victim's scream plus nearby guests shouting. Call it just before any
  death.
- In-game text is in French. The user speaks Québec French.

## NPC life (s44_npc_life.py, run LAST after s12, s14 npc, s23 CameraFadeTick, s31, s36, s39, s40_events2 npc)
It renders ThinkWith, AfterArrive, ChooseMove, GoTo, the NPC EventGraph, SitTry/SitDown/SitRelease/SeatThink, SocialFaceNow/SocialFidget/SocialMove, DanceWatch, SpawnNPC, SpawnPlayerPawn, CorpseTick, HoldNPC: their owners skip them.
Turning an NPC: `FaceAt(P)` on its controller, never SetActorRotation. Movement modes: `"MOVE_Walking"`, not `"Walking"` (that literal silently left seated guests in MOVE_None for ever).
OutfitIndex 32 stays "the detective's look on a guest": s29 keeps that slot, GM.NextOutfit never draws it. Tests: py_harness plans npc*, qa/npc_watch.py, qa/npc_net.ps1.

## Ownership
- Shop and economy agent: `s34_shop.py`, `u17_shop_ui.py`, `/Game/GW/Blueprints/Shop/`. It may extend `u14_hud.py`
  (money and item lines). Other agents do not edit `u14_hud.py`.
- Camera and combat agent: `s35_turret.py`, `s37_view.py`, `/Game/GW/Blueprints/Turret/`.
- Social agent: `s36_social.py`, `Tools\anim\` (procedural dance animations), `/Game/GW/Anims/Dance/`. It owns the
  NPC behaviour changes in `s14_npc_ghost_menu.py`: bar crowd, ballroom dancing.
- Dev menu entries go in `u15_dev_menu.py`. It is shared, so before editing it append `LOCK u15 <agent> <time>` to
  locks.md and `UNLOCK u15 ...` after re-running it. Make targeted insertions only.
- Every other script belongs to the coordinator. Ask the coordinator (SendMessage) if you need a change in one.
- Log progress in `Tools\agent_logs\<your agent>.md`. Update `BACKLOG.md` lines for your features (✅ when tested),
  and add a section to `GUIDE_JOUEUR.md` for anything a player uses (keys, prices).
