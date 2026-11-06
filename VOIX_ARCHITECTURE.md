# Voices of the ball — architecture (shared spec: engine ↔ voice production)

The user's brief (2026-11-02, night): it must feel like a real party, not a cheap video game. Nobody repeats the
same sentence. People hold conversations. Even in a panic the shouts never repeat. "Count it as each NPC being
allowed one sentence." Voices, dialogues, sound effects and music are coordinated, never a cacophony.

## 1. Principles
1. **A line is a one-time resource.** Every recorded line (one text in one voice) is said at most once per game
   session. When a category runs dry it goes silent, or falls back to non-verbal sounds (laughs, gasps, screams):
   silence beats repetition. Recency checks are not enough.
2. **Every character has its own voice (the user's rule, 2026-11-02 night).** A voice belongs to a cast
   character (char_comte, char_f_gown/Sandra, ... and every new character), not to an NPC instance: all NPCs
   wearing that character speak with its voice, and only with its lines. Each character has its own lines and its
   own dialogues, written for its personality. Staff (barman, junkie, waiters) and event characters (bandits,
   kamikaze, robot) have their own voices too.
   **Voices are a reusable asset**, kept forever: `AssetGen\voices\<char_id>\voice.json` holds the description,
   gender, age, personality and the exact TTS model, design prompt, seed and parameters. `ref.wav` is the reference
   clip used for cloning. `lines\` holds all generated lines. `AssetGen\voices\index.json` lists every voice.
   The manifest entry of the character gets `"voice": "<char_id>"`. A listening copy of each reference goes in
   `Voix (personnages)\<Nom> (<char_id>)\`, like `Personnages (images)\`.
   Every new character (the Character Creator session, the assets agent) gets its voice designed and saved at
   approval time, before its lines are generated.
3. **Conversations, not barks.** Most ambient talk is a scripted 2–4 turn dialogue between two NPCs standing
   together and facing each other. Turns are timed from the real clip durations, with natural 0.2–0.6 s gaps.
   Single remarks are rarer: someone alone, a reaction, a greeting to a guest.
4. **One voice director on the server** owns every NPC utterance and enforces the budget and priorities below.
   Nothing else plays voice lines directly.
5. **Only what a player can hear exists.** The director only makes NPCs talk within ~10 m of a player, in that
   player's room or the doorway. Elsewhere nobody talks, since nobody would hear. Walls occlude voices
   (ATT_GW_Voice: occlusion, 3.5 m full volume, 13 m falloff).

## 2. Budget and priorities (per listening area = around each player)
| Priority | What | Rule |
|---|---|---|
| P0 | death scream (the victim) | always, non-verbal screams may repeat in different voices |
| P1 | alarm: the first 2 s of a panic | at most 2 shouts per area per panic, matched to the cause |
| P2 | event lines (fire, blackout, attack, kamikaze, robot) | one every 6–9 s per area during the event |
| P3 | calm-down after a panic | 1–2 per area, often whispered |
| P4 | ambient: dialogue or remark | one conversation at a time per area; after it ends, 15–25 s of silence before the next |
| P5 | reactions (piano, fart, barman, greeting) | only if nothing above is playing nearby |
- A higher priority cancels everything lower that hasn't started yet (queued turns of a dialogue are dropped when a
  panic starts, and the two NPCs flee).
- Cause matching: every shout line has a cause tag (gun / fire / explosion / blackout / generic). A fire never gets
  "il a tiré". Gunshot lines need a real shot (GunContext).
- A guest pressing E on an NPC starts a short greeting exchange (P5, bypasses the ambient pause but not P0–P3).

## 3. Content to produce (ComfyUI, Qwen3-TTS voice clones; the audio agent)
- **Voices:** one per character (voice_id = char_id): the 6 current cast characters + the detective + the ~15 new
  characters in production + staff (barman, junkie, 2 waiters) + event characters (bandit ×2, kamikaze, robot).
  The voice is designed from the character's look and personality (manifest description, display name).
- **Per character:** 30+ remarks, 10+ greetings, cause-tagged shouts (8+), calm lines (6+, some whispered), event
  lines (a few per event), instrument reactions (3+), laughs/gasps (non-verbal).
- **Dialogues between characters:** written for a specific pair, using both personalities. Start with the most
  likely pairs: the current cast against each other and against the new characters. Expect 2+ dialogues per pair
  over time. Each turn is recorded in its speaker's voice.
- **Dialogues:** 150+ two-to-four-turn conversations, written for this ball: gossip about the hosts and the other
  guests, the masks, the food, the band, the storm outside on the island, little mysteries, light humour, a few
  absurd ones. Each has 2 speakers (voice ids) and its own text; no shared sentences between dialogues.
- **Remarks** (single lines said alone): 120+.
- **Greetings / answers to a guest:** 60+ ("Bonsoir…", "On se connaît ?", …).
- **Panic shouts** by cause: gun 30+, fire 25+, explosion 20+, blackout 20+, generic 30+. **Calm** 40+ (half
  whispered). **Event lines:** fire 20, blackout 20, attack 20, kamikaze 10 (the kamikaze himself: 8 different
  shouts, not "Alarme !" ×8), robot 10. **Piano / instrument reactions** 20.
- **Non-verbal:** screams 30+, gasps, laughs 30+, murmurs. These may repeat with variation.
- Every line in the report carries: file, category, voice_id, gender, text, duration_s, cause (for shouts),
  dialogue_id + turn (for dialogue lines), whispered, nonverbal, gun.

## 4. Engine (Tools/gameplay/s39_voice_director.py + s31 bank import)
- Bank arrays on the GameMode (server) and the GameState (clients: sounds, texts for subtitles): category, gender,
  voice, dialogue id, turn, duration, cause, used flag.
- NPC voice = its character: OutfitIndex → char_id (s29 puts the cast's manifest names in BP_GW_Character.GenIds) →
  lines tagged voice_id = char_id. Talking (until time), Partner for dialogues (s14 already pairs NPCs that face each
  other: the natural place for conversations). A conversation needs a dialogue written for the pair's two
  characters. With none left for that pair, they exchange single remarks, or stay silent.
- Director tick (0.5 s, server):
  - for each player area: purge queued lines that are below the active priority;
  - if the area is quiet and its ambient timer is due, choose a conversation (≈70 %) or a remark: speakers, voices,
    an unused dialogue that fits the speakers' genders and voices;
  - schedule the turns, mark the lines used, then set the timer to the end + 15–25 s.
- Panic, events and deaths ask the director for slots instead of queueing lines themselves.
- Subtitles: a line within 6 m of a player shows "Name : « text »" for its duration.

### 4b. As built (engine agent, 2026-11-02 night), with the adaptations and why
- **Import** (`Tools/gameplay/voice_bank.py`, pure Python): every report row, sorted by category so each category is
  one contiguous range (the director scans only that range). Texts de-duplicated across all reports; dialogues kept
  whole (turns 1..N, two different characters) or dropped; legacy voices mapped to their character, spoken lines of
  legacy voices no character owns dropped (a wrong voice is worse than silence). Missing duration → read from the
  WAV; missing cause → inferred from the text; missing speaker → from the turn's voice.
- **Who speaks.** `VoiceOf(NPC)` = GenIds[OutfitIndex] (bandits by Variant, kamikaze, robot, detective), cached on
  the character. A speaker must stand within 10 m of a player **and be in his sight** (a trace on the Camera
  channel: walls block it, people do not), and its voice must not already be speaking or queued in that area (two
  NPCs wearing the same character never talk at once). The line is chosen for the speaker; a speaker whose character
  has nothing fitting left is skipped (line-first selection among the speakers present).
- **Conversations.** First a guest within 2.6 m whose character shares an unused dialogue with the speaker's
  (either role). Otherwise a guest within 9 m whose character has one **walks over** (its brain's Partner + GoTo),
  and they talk once it has arrived (the area is held quiet meanwhile; 14 s timeout). Otherwise a remark, answered
  40 % of the time by the neighbour (a short reply or a laugh). Both face each other and hold still until the end.
- **Budget.** The alarm limit is "2 shouts + 1 bystander scream per area **per 12 s**" rather than "per panic":
  during an attack, StartPanic is called again every few seconds (each burst). Event lines: one per area, then the
  area waits 6–9 s after it ends. Calm: 2 lines per area, the second after the first ends. After a P1–P3 line the
  ambient waits too (8–12 s), after a conversation 15–25 s.
- **Cancellation.** A P0–P2 line drops the lower lines queued within 13 m (a dialogue's remaining turns go; if
  its first turn had not been heard yet, its lines stay unused) and fades out lower lines being spoken (Cue 9999).
  A queued P3–P5 line whose area got busier in the meantime is dropped at its turn.
- **Cause.** Explicit `StartPanicCause(Loc, Dur, Cause)` / `SetPanicCause(Cause)` (0 generic, 1 gun, 2 fire,
  3 explosion, 4 blackout), else inferred: GunContext or a gunshot / turret / laser sound in the last 0.6 s, an
  explosion sound in the last 0.8 s, the fire event or a fire sound, the blackout. A burning victim → fire. Players
  more than 18 m from the cause hear only generic shouts (they heard a noise, they saw nothing), except fire and
  blackout, which are everywhere.
- **Repeats.** Spoken lines: once per session. Non-verbal (screams, laughs): may repeat, never one of the last 12.
  Staff (barman, waiter, junkie): unused first, then reused (service phrases). The robot's feedback: may repeat,
  ≥10 s apart. The kamikaze: ≥14–22 s apart, its own lines only, then silence.
- **E on an NPC** (guests only, not detectives: no test to unmask players): greet → greet_again → a remark → a
  laugh; the NPC stops and turns to the guest; 35 % of the time its neighbour (another character) greets too. A
  disguised player answers nothing, like an NPC with nothing left to say.
- **One mouth.** Cue = sequence × 10000 + line (the bank may exceed 1000 lines); a new voice line fades the
  previous one; sound effects on a character (robot steps) never cut its voice.
- **Groups and gestures.** Lines and dialogues tagged `"context": "dance"` / `"bar"` are said only by guests in that
  s36 group (and preferred there). Speakers outside a group play s36's conversation loops through the replicated
  DanceId: 6 talking, 7 listening (the other person of the dialogue), 8 laughing; back to 0 when the talk ends.
- **Music ducking.** P0–P2 lines heard within 16 m push SM_GW_Duck on the listener's machine (music × 0.45, 0.35 s
  in, 3 s, 2.5 s out; every new such line restarts it), multiplied with the player's own volume settings.
- **Refinements from the headless tests (2026-11-03).** A walker counts as arrived within 2.6 m of its partner (it
  stops up to ~2.1 m away: acceptance radius + capsule). The rest of a conversation is dropped when no player is
  within 16 m any more (only what a player can hear exists). A blast that kills many: at most 2 death screams per area
  per second, the others die silently. E-talk and conversation partners never use a voice already speaking nearby.
  The robot's feedback may repeat 20 s after it was said.
- **Reaction categories for the feature scripts** (`voice_bank.CAT`; call `Say(Ch, id)` on a chosen NPC or
  `SayNearPlayers(id, 1, delay, spread)`, silent until lines exist): 65 fart_react, 66 safe_react, 67 alarm_react,
  69 ghost_react, 70 sword_react, 71 ball_react, 72 bomb_near (P3), 73 smoke_react (P3), 74 shrink_react,
  75 defuse_react (P3), 76 dance_end (context dance), 77 bar_toast (P4, context bar); staff 15 barman / 62 waiter /
  63 junkie.
- **Staff moments.** Staff lines carry a context (report "context"): 3 open, 4 sale, 5 no_money, 6 danger_sold,
  7 walk_away, 8 detective_near. `StaffSay(Cat, Ctx, Loc)` plays the moment's line at the vendor (unused first, falls
  back to a context-free line); a plain WorldSound(15/62/63) only takes sale or context-free lines; clients read
  `GameState.BankCtx` for their local "open" line. Context 9 smoke marks coughs.
- **Content updates** without a graph change: `s31_reactions.py tablesonly` (imports, then only the GameState /
  GameMode bank arrays, ~3 min); with a graph change: the full s31 (it runs s39).
- **Speed.** Lines are grouped per (category, voice) and dialogues per character pair, so a pick scans a dozen lines,
  not the whole bank (2,300+ clips expected).
- **Occlusion.** ATT_GW_Voice / ATT_GW_Far trace on the Camera channel instead of Visibility: UE ignores only the
  sound's owner in its occlusion trace, so on Visibility the listener's own body and any guest standing in between
  muffled every voice.
- **Test.** `-GWVoiceTest` plays a scripted 13 min round (rooms, E, fire, gunshot death, blackout, attack, burning
  guest, kamikaze, robot, piano, explosion) and logs every line (`GW: VOX ...`) and the players' positions;
  `Tools/qa/voice_log_check.py` checks repeats, causes, spacing, overlap per area, voices, distance, BP errors.

## 5. Coordination with the rest of the sound
- Music ducks under P0–P2 (the HUD's music volume follows a "tension" value replicated by the director).
- Room ambiences (AmbientSound beds per room) stay under the voices: −27 to −34 LUFS against −18 for speech.
- Loud one-shots (piano, explosions, gunshots, fart) are never stacked: a 1 s anti-overlap per category.
